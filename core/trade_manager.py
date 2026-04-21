# -*- coding: utf-8 -*-
# FILE: core/trade_manager.py
# V3.0: UNIFIED TRADE MANAGER - DYNAMIC SL & MAGIC SPLIT (KAISER EDITION)

import logging
import config
from core.storage_manager import load_state, save_state, append_trade_log
from signals.multi_candle import get_pullback_confirmation
import MetaTrader5 as mt5
from datetime import datetime
import math
import threading
import time
import pandas as pd
import pandas_ta as ta

class TradeManager:
    def __init__(self, connector, checklist_manager, log_callback=None):
        self.connector = connector
        self.checklist = checklist_manager
        self.log_callback = log_callback 
        self.state = load_state()
        self.dca_pca_cache = {} # Bộ nhớ đệm giảm tải MT5
        
        # Đảm bảo các biến State luôn tồn tại để tránh lỗi sập Bot
        if "daily_loss_count" not in self.state: self.state["daily_loss_count"] = 0
        if "trade_tactics" not in self.state: self.state["trade_tactics"] = {} 
        if "initial_r_dist" not in self.state: self.state["initial_r_dist"] = {}
        if "parent_baskets" not in self.state: self.state["parent_baskets"] = {}
        if "child_to_parent" not in self.state: self.state["child_to_parent"] = {}
        if "active_trades" not in self.state: self.state["active_trades"] = []
        if "last_child_bar_time" not in self.state: self.state["last_child_bar_time"] = {}
        
        if self.state.get("trades_today_count", 0) == 0: 
            self.state["daily_loss_count"] = 0

    def log(self, msg, error=False):
        if self.log_callback: 
            self.log_callback(msg, error=error)
        else: 
            print(f"{'❌' if error else '✅'} {msg}")

    def get_trade_tactic(self, ticket):
        return self.state.get("trade_tactics", {}).get(str(ticket), "OFF")

    def update_trade_tactic(self, ticket, new_tactic_str):
        if "trade_tactics" not in self.state: self.state["trade_tactics"] = {}
        self.state["trade_tactics"][str(ticket)] = new_tactic_str
        save_state(self.state)

    # ====================================================================================
    # 1. HÀM THỰC THI LỆNH CHO BOT (V3.0 - Dynamic SL & Bot Magic Number)
    # ====================================================================================
    def execute_bot_trade(self, direction, symbol, sl_price, tp_price, bot_risk_percent, tactic_str, details=None):
        config.SYMBOL = symbol 
        acc_info = self.connector.get_account_info()
        
        bot_bypass = getattr(config, "BOT_BYPASS_CHECKLIST", True) 

        res = self.checklist.run_pre_trade_checks(acc_info, self.state, symbol, strict_mode=not bot_bypass)
        if not res["passed"]:
            if bot_bypass:
                self.log(f"⚠️ [BOT FORCE] Bỏ qua cảnh báo an toàn Checklist để test")
            else:
                fail_reasons = [c['msg'] for c in res['checks'] if c['status'] == 'FAIL']
                self.log(f"⚠️ [BOT BLOCKED] Bị chặn bởi hệ thống an toàn: {fail_reasons}", error=True)
                return "CHECKLIST_FAIL"

        tick = mt5.symbol_info_tick(symbol)
        sym_info = mt5.symbol_info(symbol)
        if not tick or not sym_info: 
            self.log("❌ [BOT] Thiếu dữ liệu Tick từ sàn.", error=True)
            return "ERR_NO_TICK"
        
        current_price = tick.ask if direction == "BUY" else tick.bid

        # --- [V3.0] TÍNH TOÁN SL ĐỘNG DỰA TRÊN DETAILS (SWING H/L & ATR) ---
        if details:
            swing_high = details.get("swing_high", 0.0)
            swing_low = details.get("swing_low", 0.0)
            atr = details.get("atr", 0.0)
            sl_mult = getattr(config, "sl_atr_multiplier", 0.2)

            if atr > 0:
                if direction == "BUY" and swing_low > 0:
                    sl_price = swing_low - (atr * sl_mult)
                elif direction == "SELL" and swing_high > 0:
                    sl_price = swing_high + (atr * sl_mult)
        # -------------------------------------------------------------------

        sl_distance = abs(current_price - sl_price)
        if sl_distance <= 0 or sl_price <= 0: 
            self.log("❌ [BOT] Lỗi Math SL: Không có dữ liệu Swing/ATR hợp lệ hoặc SL = 0", error=True)
            return "ERR_CALC_SL_ZERO"

        equity = acc_info['equity']
        contract_size = sym_info.trade_contract_size

        risk_usd = equity * (bot_risk_percent / 100.0)
        raw_lot = risk_usd / (sl_distance * contract_size)
        lot_size = round(raw_lot / config.LOT_STEP) * config.LOT_STEP
        lot_size = max(config.MIN_LOT_SIZE, min(lot_size, config.MAX_LOT_SIZE))

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        comment = "[BOT]_AUTO_ENTRY"
        
        # [V3.0] Sử dụng Magic Number riêng của Bot
        bot_magic = getattr(config, "BOT_MAGIC_NUMBER", 9999)
        
        result = self.connector.place_order(symbol, order_type, lot_size, sl_price, tp_price, bot_magic, comment)
        
        if result and result.retcode == 10009:
            ticket_id = result.order
            self.state["trades_today_count"] += 1
            if ticket_id not in self.state["active_trades"]:
                self.state["active_trades"].append(ticket_id)
            
            self.update_trade_tactic(ticket_id, tactic_str)
            self.state["initial_r_dist"][str(ticket_id)] = sl_distance
            save_state(self.state)

            self.log(f"🚀 [BOT EXEC] {direction} {symbol} #{ticket_id} | Lot: {lot_size:.2f} | Risk: {bot_risk_percent}% | TSL: {tactic_str}")
            return "SUCCESS"
        
        err_msg = result.comment if result else 'Unknown Connection Error'
        self.log(f"❌ [BOT ERR] Sàn từ chối lệnh: {err_msg}", error=True)
        return "MT5_ERROR"

    # ====================================================================================
    # 2. HÀM THỰC THI LỆNH TAY (V3.0 - Manual Magic Number)
    # ====================================================================================
    def execute_manual_trade(self, direction, preset_name, symbol, strict_mode, 
                             manual_lot=0.0, manual_tp=0.0, manual_sl=0.0, bypass_checklist=False, 
                             tsl_mode="BE+STEP_R"):
        config.SYMBOL = symbol 
        acc_info = self.connector.get_account_info()
        res = self.checklist.run_pre_trade_checks(acc_info, self.state, symbol, strict_mode)
        
        if not res["passed"]:
            if bypass_checklist:
                fail_reasons = [c['msg'] for c in res['checks'] if c['status'] == 'FAIL']
                self.log(f"⚠️ [FORCE] Bỏ qua cảnh báo an toàn: {fail_reasons}")
            else:
                return "CHECKLIST_FAIL"

        params = getattr(config, "PRESETS", {}).get(preset_name, {})
        if not params:
            # Fallback nếu UI gửi preset không tồn tại
            params = {"SL_PERCENT": 0.4, "TP_RR_RATIO": 1.5, "RISK_PERCENT": 0.3}

        tick = mt5.symbol_info_tick(symbol)
        sym_info = mt5.symbol_info(symbol)
        if not tick or not sym_info: return "ERR_NO_TICK"
        
        price = tick.ask if direction == "BUY" else tick.bid
        equity = acc_info['equity']
        contract_size = sym_info.trade_contract_size

        if manual_sl > 0: 
            sl_distance = abs(price - manual_sl)
        else:
            sl_percent = params.get("SL_PERCENT", 0.5) / 100.0
            sl_distance = price * sl_percent

        if sl_distance <= 0: return "ERR_CALC_SL_ZERO"

        if manual_lot > 0: 
            lot_size = manual_lot
        else:
            current_risk_pct = params.get("RISK_PERCENT", getattr(config, "RISK_PER_TRADE_PERCENT", 0.3))
            risk_usd = equity * (current_risk_pct / 100.0)
            raw_lot = risk_usd / (sl_distance * contract_size)
            lot_size = round(raw_lot / config.LOT_STEP) * config.LOT_STEP

        lot_size = max(config.MIN_LOT_SIZE, min(lot_size, config.MAX_LOT_SIZE))
        sl_price = manual_sl if manual_sl > 0 else (price - sl_distance if direction == "BUY" else price + sl_distance)

        if manual_tp > 0: 
            tp_price = manual_tp
        else:
            rr_ratio = params.get("TP_RR_RATIO", 1.5)
            real_sl_dist = abs(price - sl_price)
            tp_price = price + (real_sl_dist * rr_ratio) if direction == "BUY" else price - (real_sl_dist * rr_ratio)

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        comment = f"[USER]_{preset_name}"
        
        # [V3.0] Sử dụng Magic Number riêng của lệnh Tay
        manual_magic = getattr(config, "MANUAL_MAGIC_NUMBER", 8888)
        
        result = self.connector.place_order(symbol, order_type, lot_size, sl_price, tp_price, manual_magic, comment)
        
        if result and result.retcode == 10009:
            ticket_id = result.order
            self.state["trades_today_count"] += 1
            if ticket_id not in self.state["active_trades"]:
                self.state["active_trades"].append(ticket_id)
            
            self.update_trade_tactic(ticket_id, tsl_mode)
            self.state["initial_r_dist"][str(ticket_id)] = abs(price - sl_price)
            save_state(self.state)

            self.log(f"🚀 [USER EXEC] {direction} {symbol} #{ticket_id} | Vol: {lot_size:.2f} | TSL: {tsl_mode}")
            return f"SUCCESS|{ticket_id}"
        
        return f"ERR_MT5: {result.comment if result else 'Unknown Connection Error'}"

    # ====================================================================================
    # 3. QUẢN LÝ LỆNH CHẠY (BASKET CLOSE & TSL)
    # ====================================================================================
    def update_running_trades(self, account_type="STANDARD", all_market_contexts=None):
        tsl_status_map = {} 
        try:
            current_positions = self.connector.get_all_open_positions()
            current_tickets = [p.ticket for p in current_positions]
            tracked_tickets = list(self.state.get("active_trades", []))
            
            # 1. XỬ LÝ LỆNH ĐÃ ĐÓNG & BASKET CLOSE (CHỐT CHẶN SINH TỬ)
            closed_tickets = [t for t in tracked_tickets if t not in current_tickets]
            if closed_tickets:
                for ticket in closed_tickets:
                    s_ticket = str(ticket)
                         
                    deals = mt5.history_deals_get(position=ticket)
                    if deals:
                        exit_deal = deals[-1]
                        if exit_deal.entry == mt5.DEAL_ENTRY_OUT:
                            profit = exit_deal.profit + exit_deal.swap + getattr(exit_deal, 'commission', 0.0)
                            self.state["pnl_today"] += profit
                            if profit < 0: self.state["daily_loss_count"] += 1
                            
                            reason = "Cắt Tay" if "User_Close" in (exit_deal.comment or "") else \
                                     ("Dính SL" if exit_deal.reason == mt5.DEAL_REASON_SL else \
                                      ("Húp TP" if exit_deal.reason == mt5.DEAL_REASON_TP else "Client Close"))
                            
                            self.log(f"📉 Đóng lệnh #{ticket} | {exit_deal.symbol} | PnL: {profit:+.2f}$ | {reason}")
                            
                            if "daily_history" not in self.state: self.state["daily_history"] = []
                            self.state["daily_history"].append({
                                "time": datetime.now().strftime("%H:%M"), "symbol": exit_deal.symbol,
                                "type": "BUY" if exit_deal.type==1 else "SELL", "profit": profit, "reason": reason
                            })
                            append_trade_log(ticket, exit_deal.symbol, "BUY" if exit_deal.type==1 else "SELL", exit_deal.volume, profit, reason)
                            
                    # DỌN DẸP STATE
                    if ticket in self.state["active_trades"]: self.state["active_trades"].remove(ticket)
                    if s_ticket in self.state.get("trade_tactics", {}): del self.state["trade_tactics"][s_ticket]
                    if s_ticket in self.state.get("initial_r_dist", {}): del self.state["initial_r_dist"][s_ticket]

                    # BASKET CLOSE LOGIC
                    if s_ticket in self.state.get("parent_baskets", {}):
                        child_tickets = self.state["parent_baskets"][s_ticket]
                        for child_t in child_tickets:
                            child_pos = next((p for p in current_positions if str(p.ticket) == str(child_t)), None)
                            if child_pos:
                                self.log(f"⚠️ [BASKET CLOSE] Đóng lệnh Con #{child_t} do Mẹ #{ticket} đã chết!", error=True)
                                threading.Thread(target=self.connector.close_position, args=(child_pos,), daemon=True).start()
                        del self.state["parent_baskets"][s_ticket]
                    
                    if s_ticket in self.state.get("child_to_parent", {}):
                        parent_t = self.state["child_to_parent"][s_ticket]
                        if parent_t in self.state.get("parent_baskets", {}) and s_ticket in self.state["parent_baskets"][parent_t]:
                            self.state["parent_baskets"][parent_t].remove(s_ticket)
                        del self.state["child_to_parent"][s_ticket]

                save_state(self.state)

            # 2. XỬ LÝ TSL & DCA/PCA CHO TỪNG LỆNH ĐỘC LẬP
            bot_magic = getattr(config, "BOT_MAGIC_NUMBER", 9999)
            manual_magic = getattr(config, "MANUAL_MAGIC_NUMBER", 8888)
            
            # Quét tất cả lệnh thuộc về Bot hoặc Manual
            tracked_positions = [p for p in current_positions if p.magic in (bot_magic, manual_magic)]
            
            for pos in tracked_positions:
                symbol_context = all_market_contexts.get(pos.symbol, {}) if all_market_contexts else {}
                tsl_status_map[pos.ticket] = self._apply_individual_trailing_logic(pos, symbol_context)

        except Exception as e:
            self.log(f"❌ Lỗi TSL/Basket update loop: {e}", error=True)
        
        return tsl_status_map

    def _apply_individual_trailing_logic(self, pos, symbol_context):
        tactic_str = self.get_trade_tactic(pos.ticket)
        if tactic_str == "OFF": return "TSL OFF"

        active_modes = tactic_str.split("+")
        is_buy = (pos.type == mt5.ORDER_TYPE_BUY)
        current_price = pos.price_current 
        current_sl = pos.sl 
        
        sym_info = mt5.symbol_info(pos.symbol)
        point = sym_info.point if sym_info else 0.00001
        contract_size = sym_info.trade_contract_size if sym_info else 1.0
        
        s_ticket = str(pos.ticket)
        one_r_dist = self.state.get("initial_r_dist", {}).get(s_ticket, 0.0)

        # QUÉT DCA & PCA
        if "AUTO_DCA" in active_modes or "AUTO_PCA" in active_modes:
            self._check_dca_pca(pos, symbol_context, tactic_str)

        if one_r_dist <= 0: return "Err R Dist"

        curr_dist = current_price - pos.price_open if is_buy else pos.price_open - current_price
        curr_r = curr_dist / one_r_dist
        
        candidates, milestones = [], []
        tsl_cfg = getattr(config, "TSL_CONFIG", {})

        # 1. BREAK-EVEN
        if "BE" in active_modes:
            total_fee_usd = abs(getattr(pos, 'commission', 0.0) + getattr(pos, 'swap', 0.0))
            fee_dist = total_fee_usd / (pos.volume * contract_size) if contract_size > 0 else 0
            
            mode = tsl_cfg.get("BE_MODE", "SOFT")
            base = pos.price_open - fee_dist if (is_buy and mode=="SOFT") else (pos.price_open + fee_dist if (is_buy and mode=="SMART") else pos.price_open)
            if not is_buy: base = pos.price_open + fee_dist if mode=="SOFT" else (pos.price_open - fee_dist if mode=="SMART" else pos.price_open)

            be_sl = base + (tsl_cfg.get("BE_OFFSET_POINTS", 0) * point) if is_buy else base - (tsl_cfg.get("BE_OFFSET_POINTS", 0) * point)
            trig_r = tsl_cfg.get("BE_OFFSET_RR", 0.8)
            
            if curr_r >= trig_r: candidates.append((be_sl, "BE"))
            else: 
                trig_p = pos.price_open + (one_r_dist * trig_r) if is_buy else pos.price_open - (one_r_dist * trig_r)
                milestones.append((abs(curr_r - trig_r), f"BE | {trig_p:.2f} -> {be_sl:.2f}"))

        # 2. STEP R
        if "STEP_R" in active_modes:
            sz, rt = tsl_cfg.get("STEP_R_SIZE", 1.0), tsl_cfg.get("STEP_R_RATIO", 0.8)
            steps = max(0, math.floor(curr_r / sz))
            if steps >= 1:
                step_sl = pos.price_open + (steps * one_r_dist * rt) if is_buy else pos.price_open - (steps * one_r_dist * rt)
                candidates.append((step_sl, f"STEP {steps}"))
            
            n_trig = pos.price_open + ((steps + 1) * sz * one_r_dist) if is_buy else pos.price_open - ((steps + 1) * sz * one_r_dist)
            n_sl = pos.price_open + ((steps + 1) * sz * one_r_dist * rt) if is_buy else pos.price_open - ((steps + 1) * sz * one_r_dist * rt)
            milestones.append((abs(curr_r - (steps+1)*sz), f"Step {steps+1} | {n_trig:.2f} -> {n_sl:.2f}"))

        # 3. PNL LOCK
        if "PNL" in active_modes:
            acc = self.connector.get_account_info()
            if acc:
                profit_usd = pos.profit + getattr(pos, 'swap', 0.0) + getattr(pos, 'commission', 0.0)
                pnl_pct = (profit_usd / acc['balance']) * 100
                levels = sorted(tsl_cfg.get("PNL_LEVELS", []), key=lambda x: x[0])
                for lvl in levels:
                    if pnl_pct >= lvl[0]:
                        lock_dist = (acc['balance'] * (lvl[1]/100.0)) / (pos.volume * contract_size)
                        pnl_sl = pos.price_open + lock_dist if is_buy else pos.price_open - lock_dist
                        candidates.append((pnl_sl, "PNL"))
                        milestones.append((abs(pnl_pct - lvl[0]), f"PnL {lvl[0]}% | -> {pnl_sl:.2f}"))

        # 4. TSL SWING
        if "SWING" in active_modes and symbol_context:
            sh, sl, atr = symbol_context.get("swing_high"), symbol_context.get("swing_low"), symbol_context.get("atr")
            trend_adx = symbol_context.get("trend", "UP")
            
            if sh and sl and atr and str(sh) != "--":
                tsl_mode = getattr(config, "TSL_LOGIC_MODE", "STATIC")
                trail_buf = getattr(config, "trail_atr_buffer", 0.2)
                sh, sl, atr = float(sh), float(sl), float(atr)
                swing_sl = None
                
                if is_buy: 
                    if tsl_mode == "AGGRESSIVE" or (tsl_mode == "DYNAMIC" and trend_adx != "UP"): swing_sl = sh - (trail_buf * atr)
                    else: swing_sl = sl - (trail_buf * atr) 
                else: 
                    if tsl_mode == "AGGRESSIVE" or (tsl_mode == "DYNAMIC" and trend_adx != "DOWN"): swing_sl = sl + (trail_buf * atr)
                    else: swing_sl = sh + (trail_buf * atr)
                
                candidates.append((swing_sl, "SWING"))
                milestones.append((0, f"SWING | -> {swing_sl:.2f}"))

        # Xử lý cập nhật SL an toàn
        valid_moves = []
        min_stop_dist = getattr(sym_info, 'trade_stops_level', 0) * point

        for price, rule in candidates:
            if price is None: continue
            price = round(price / point) * point
            if is_buy:
                if price > current_sl + (point / 2) and price <= current_price - min_stop_dist:
                    valid_moves.append((price, rule))
            else:
                if (current_sl == 0 or price < current_sl - (point / 2)) and price >= current_price + min_stop_dist:
                    valid_moves.append((price, rule))

        if valid_moves:
            best_move = max(valid_moves, key=lambda x: x[0]) if is_buy else min(valid_moves, key=lambda x: x[0])
            target_sl, action_rule = best_move
            
            if abs(target_sl - current_sl) > (point / 2):
                self.log(f"⚡ [TSL] Dời SL #{pos.ticket} ({action_rule}) ➔ {target_sl:.5f}")
                self.connector.modify_position(pos.ticket, target_sl, pos.tp)
                return f"{action_rule} ➔ {target_sl:.2f}"

        if milestones:
            closest_ms = sorted(milestones, key=lambda x: x[0])[0][1]
            return f"Track: {closest_ms}"

        return "Tracking..."

    # ====================================================================================
    # 4. CHỨC NĂNG NHỒI LỆNH (MẸ - CON) - V8.4 BỘ NHỚ ĐỆM 15 PHÚT
    # ====================================================================================
    def _check_dca_pca(self, pos, symbol_context, tactic_str):
        s_ticket = str(pos.ticket)
        if s_ticket in self.state.get("child_to_parent", {}): return # Chặn đệ quy

        is_buy = pos.type == mt5.ORDER_TYPE_BUY
        current_children = self.state.get("parent_baskets", {}).get(s_ticket, [])
        
        # --- 1. TÌM GIÁ CỦA LỆNH CUỐI CÙNG TRONG RỔ ---
        last_order_price = pos.price_open
        if current_children:
            current_positions = self.connector.get_all_open_positions()
            for child_t in reversed(current_children):
                child_pos = next((p for p in current_positions if str(p.ticket) == child_t), None)
                if child_pos:
                    last_order_price = child_pos.price_open
                    break

        # --- 2. THUẬT TOÁN CACHE 15 PHÚT (GIẢM TẢI 99% CHO EXNESS) ---
        now = datetime.now()
        cache_key = f"{pos.symbol}_{now.day}_{now.hour}_{now.minute // 15}"
        
        if cache_key != self.dca_pca_cache.get(f"{pos.symbol}_key"):
            rates_m15 = mt5.copy_rates_from_pos(pos.symbol, mt5.TIMEFRAME_M15, 0, 30)
            if rates_m15 is None or len(rates_m15) < 30: return
            
            df_m15 = pd.DataFrame(rates_m15)
            ema_series = df_m15['close'].ewm(span=getattr(config, "ENTRY_EMA_PERIOD", 21), adjust=False).mean()
            
            df_closed = df_m15.iloc[:-1]
            ema_closed = ema_series.iloc[:-1]
            
            mc_config = {"PULLBACK_CANDLE_PATTERN": getattr(config, "PULLBACK_CANDLE_PATTERN", "ENGULFING")}
            pullback_signal = get_pullback_confirmation(df_closed, ema_closed, mc_config)

            adx_value = 0.0
            if "AUTO_PCA" in tactic_str:
                h1_rates = mt5.copy_rates_from_pos(pos.symbol, mt5.TIMEFRAME_H1, 0, 20)
                if h1_rates is not None:
                    df_h1 = pd.DataFrame(h1_rates)
                    adx_res = df_h1.ta.adx(length=getattr(config, "ADX_PERIOD", 14))
                    if adx_res is not None and not adx_res.empty:
                        adx_value = adx_res.iloc[-1, 0]

            self.dca_pca_cache[f"{pos.symbol}_key"] = cache_key
            self.dca_pca_cache[pos.symbol] = {
                "pullback_signal": pullback_signal,
                "adx_value": adx_value,
                "current_bar_time": int(rates_m15[-1]['time'])
            }

        cached_data = self.dca_pca_cache.get(pos.symbol, {})
        pullback_signal = cached_data.get("pullback_signal")
        adx_value = cached_data.get("adx_value", 0.0)
        current_bar_time = cached_data.get("current_bar_time", 0)
        
        last_time_db = self.state.get("last_child_bar_time", {})
        if last_time_db.get(s_ticket) == current_bar_time: return 

        # --- 3. LOGIC DCA (GỒNG LỖ - BẮT NHỊP HỒI) ---
        if "AUTO_DCA" in tactic_str:
            dca_cfg = getattr(config, "DCA_CONFIG", {})
            if len(current_children) < dca_cfg.get("MAX_STEPS", 3):
                atr = symbol_context.get("atr", 0)
                if atr and atr > 0:
                    dist = last_order_price - pos.price_current if is_buy else pos.price_current - last_order_price
                    if dist >= (atr * dca_cfg.get("DISTANCE_ATR_R", 1.0)):
                        if (is_buy and pullback_signal == "BUY") or (not is_buy and pullback_signal == "SELL"):
                            self._execute_child_order(pos, "DCA", dca_cfg.get("STEP_MULTIPLIER", 1.5))
                            if "last_child_bar_time" not in self.state: self.state["last_child_bar_time"] = {}
                            self.state["last_child_bar_time"][s_ticket] = current_bar_time
                            save_state(self.state)
                            return 

        # --- 4. LOGIC PCA (NHỒI THUẬN - BÁM TREND) ---
        if "AUTO_PCA" in tactic_str:
            pca_cfg = getattr(config, "PCA_CONFIG", {})
            if len(current_children) < pca_cfg.get("MAX_STEPS", 2):
                is_risk_free = (is_buy and pos.sl >= pos.price_open) or (not is_buy and pos.sl > 0 and pos.sl <= pos.price_open)
                min_pca_dist = symbol_context.get("atr", 0.001) * 0.5 
                dist_from_last = pos.price_current - last_order_price if is_buy else last_order_price - pos.price_current
                
                if is_risk_free and dist_from_last >= min_pca_dist:
                    if adx_value >= getattr(config, "ADX_STRONG", 23):
                        if (is_buy and pullback_signal == "BUY") or (not is_buy and pullback_signal == "SELL"):
                            self._execute_child_order(pos, "PCA", pca_cfg.get("STEP_MULTIPLIER", 0.5))
                            if "last_child_bar_time" not in self.state: self.state["last_child_bar_time"] = {}
                            self.state["last_child_bar_time"][s_ticket] = current_bar_time
                            save_state(self.state)

    def _execute_child_order(self, parent_pos, mode, multiplier):
        new_lot = round((parent_pos.volume * multiplier) / getattr(config, "LOT_STEP", 0.01)) * getattr(config, "LOT_STEP", 0.01)
        new_lot = max(getattr(config, "MIN_LOT_SIZE", 0.01), min(new_lot, getattr(config, "MAX_LOT_SIZE", 100.0)))
        
        parent_tactic = self.get_trade_tactic(parent_pos.ticket)
        child_tactic = parent_tactic.replace("+AUTO_DCA", "").replace("+AUTO_PCA", "")
        if child_tactic.startswith("+"): child_tactic = child_tactic[1:]
        if not child_tactic: child_tactic = "OFF"
        
        # [V3.0] Lệnh con kế thừa Magic Number của lệnh Mẹ
        child_magic = parent_pos.magic
        result = self.connector.place_order(parent_pos.symbol, parent_pos.type, new_lot, parent_pos.sl, parent_pos.tp, child_magic, f"[{mode}]_Child")
        
        if result and result.retcode == 10009:
            child_ticket = result.order
            s_parent = str(parent_pos.ticket)
            s_child = str(child_ticket)
            
            if s_parent not in self.state["parent_baskets"]: self.state["parent_baskets"][s_parent] = []
            self.state["parent_baskets"][s_parent].append(s_child)
            self.state["child_to_parent"][s_child] = s_parent
            
            self.update_trade_tactic(child_ticket, child_tactic)
            
            if "initial_r_dist" in self.state and s_parent in self.state["initial_r_dist"]:
                self.state["initial_r_dist"][s_child] = self.state["initial_r_dist"][s_parent]
                
            self.state["active_trades"].append(child_ticket)
            save_state(self.state)
            
            self.log(f"🔥 [{mode} XÁC NHẬN NẾN] Mẹ #{s_parent} đẻ Con #{s_child} | Vol: {new_lot:.2f}")

            if mode == "DCA":
                threading.Thread(target=self._adjust_basket_tp, args=(parent_pos.ticket,), daemon=True).start()

    def _adjust_basket_tp(self, parent_ticket):
        time.sleep(1.5) 
        s_parent = str(parent_ticket)
        children = self.state.get("parent_baskets", {}).get(s_parent, [])
        if not children: return

        tickets = [parent_ticket] + [int(t) for t in children]
        positions = self.connector.get_all_open_positions()
        basket_pos = [p for p in positions if p.ticket in tickets]
        
        if not basket_pos: return

        total_lot = sum(p.volume for p in basket_pos)
        total_value = sum(p.volume * p.price_open for p in basket_pos)
        avg_price = total_value / total_lot
        
        is_buy = basket_pos[0].type == mt5.ORDER_TYPE_BUY
        sym_info = mt5.symbol_info(basket_pos[0].symbol)
        
        has_manual_tp = basket_pos[0].tp > 0
        
        if has_manual_tp:
            tp_offset = 30 * sym_info.point
        else:
            tp_offset = 50 * sym_info.point
            
        new_tp = avg_price + tp_offset if is_buy else avg_price - tp_offset
        new_tp = round(new_tp / sym_info.point) * sym_info.point
        
        for p in basket_pos:
            if abs(p.tp - new_tp) > sym_info.point * 2:
                self.connector.modify_position(p.ticket, p.sl, new_tp)
                
        self.log(f"🔄 [BASKET RESCUE] Kéo TP của Rổ DCA #{parent_ticket} về điểm hòa vốn: {new_tp:.5f}")