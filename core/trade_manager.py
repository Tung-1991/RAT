# -*- coding: utf-8 -*-
# FILE: core/trade_manager.py
# V5.3: FINAL REFACTOR - PERFECT ISOLATION FOR BOT & MANUAL TRADES

import logging
import config
from core.storage_manager import load_state, save_state, append_trade_log
import MetaTrader5 as mt5
from datetime import datetime
import math

class TradeManager:
    def __init__(self, connector, checklist_manager, log_callback=None):
        self.connector = connector
        self.checklist = checklist_manager
        self.log_callback = log_callback 
        self.state = load_state()
        
        if "daily_loss_count" not in self.state: self.state["daily_loss_count"] = 0
        if "trade_tactics" not in self.state: self.state["trade_tactics"] = {} 
        if "initial_r_dist" not in self.state: self.state["initial_r_dist"] = {}
        
        if self.state.get("trades_today_count", 0) == 0: self.state["daily_loss_count"] = 0

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
    # 1. HÀM THỰC THI LỆNH CHO BOT (CHỈ DAEMON GỌI)
    # ====================================================================================
    def execute_bot_trade(self, direction, symbol, sl_price, tp_price, bot_risk_percent, tactic_str):
        """Hàm chuyên dụng bóp cò cho Bot. Nhận tham số trực tiếp từ Daemon."""
        config.SYMBOL = symbol 
        acc_info = self.connector.get_account_info()
        
        # Vẫn phải qua vòng kiểm tra an toàn (Max lệnh, Max Loss ngày...)
        res = self.checklist.run_pre_trade_checks(acc_info, self.state, symbol, strict_mode=True)
        if not res["passed"]:
            fail_reasons = [c['msg'] for c in res['checks'] if c['status'] == 'FAIL']
            self.log(f"⚠️ [BOT BLOCKED] Bị chặn bởi hệ thống an toàn: {fail_reasons}", error=True)
            return "CHECKLIST_FAIL"

        tick = mt5.symbol_info_tick(symbol)
        sym_info = mt5.symbol_info(symbol)
        if not tick or not sym_info: 
            self.log("❌ [BOT] Thiếu dữ liệu Tick từ sàn.", error=True)
            return "ERR_NO_TICK"
        
        current_price = tick.ask if direction == "BUY" else tick.bid
        equity = acc_info['equity']
        contract_size = sym_info.trade_contract_size

        # 1. Tính toán Lot size dựa trên Rủi ro Bot và Math SL
        sl_distance = abs(current_price - sl_price)
        if sl_distance <= 0: 
            self.log("❌ [BOT] Lỗi Math SL: Khoảng cách SL = 0", error=True)
            return "ERR_CALC_SL_ZERO"

        risk_usd = equity * (bot_risk_percent / 100.0)
        raw_lot = risk_usd / (sl_distance * contract_size)
        lot_size = round(raw_lot / config.LOT_STEP) * config.LOT_STEP
        lot_size = max(config.MIN_LOT_SIZE, min(lot_size, config.MAX_LOT_SIZE))

        # 2. Đảm bảo tuyệt đối Bot đánh không có TP
        enforced_tp = 0.0

        # 3. Gửi lệnh
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        comment = "[BOT]_AUTO_ENTRY"
        
        result = self.connector.place_order(symbol, order_type, lot_size, sl_price, enforced_tp, config.MAGIC_NUMBER, comment)
        
        if result and result.retcode == 10009:
            ticket_id = result.order
            self.state["trades_today_count"] += 1
            if ticket_id not in self.state["active_trades"]:
                self.state["active_trades"].append(ticket_id)
            
            self.update_trade_tactic(ticket_id, tactic_str)
            
            # Lưu 1R để dùng cho TSL
            actual_1r_dist = abs(current_price - sl_price)
            if "initial_r_dist" not in self.state: self.state["initial_r_dist"] = {}
            self.state["initial_r_dist"][str(ticket_id)] = actual_1r_dist
            save_state(self.state)

            self.log(f"🚀 [BOT EXEC] {direction} {symbol} #{ticket_id} | Lot: {lot_size:.2f} | Risk: {bot_risk_percent}% | TSL: {tactic_str}")
            return "SUCCESS"
        
        err_msg = result.comment if result else 'Unknown Connection Error'
        self.log(f"❌ [BOT ERR] Sàn từ chối lệnh: {err_msg}", error=True)
        return "MT5_ERROR"

    # ====================================================================================
    # 2. HÀM THỰC THI LỆNH TAY (CHỈ UI GỌI KHI BẤM NÚT)
    # ====================================================================================
    def execute_manual_trade(self, direction, preset_name, symbol, strict_mode, 
                             manual_lot=0.0, manual_tp=0.0, manual_sl=0.0, bypass_checklist=False, 
                             tsl_mode="BE+STEP_R"):
        """Hàm dành riêng cho User thao tác trên bảng điều khiển Master UI."""
        config.SYMBOL = symbol 
        acc_info = self.connector.get_account_info()
        res = self.checklist.run_pre_trade_checks(acc_info, self.state, symbol, strict_mode)
        
        if not res["passed"]:
            if bypass_checklist:
                fail_reasons = [c['msg'] for c in res['checks'] if c['status'] == 'FAIL']
                self.log(f"⚠️ [FORCE] Bỏ qua cảnh báo an toàn: {fail_reasons}")
            else:
                return "CHECKLIST_FAIL"

        params = config.PRESETS.get(preset_name, config.PRESETS["SCALPING"])
        tick = mt5.symbol_info_tick(symbol)
        if not tick: return "ERR_NO_TICK"
        
        price = tick.ask if direction == "BUY" else tick.bid
        equity = acc_info['equity']
        sym_info = mt5.symbol_info(symbol)
        contract_size = sym_info.trade_contract_size if sym_info else 1.0

        lot_size = 0.0
        sl_distance = 0.0
        
        if manual_sl > 0: 
            sl_distance = abs(price - manual_sl)
        else:
            sl_percent = params["SL_PERCENT"] / 100.0
            sl_distance = price * sl_percent

        if sl_distance <= 0: return "ERR_CALC_SL_ZERO"

        if manual_lot > 0: 
            lot_size = manual_lot
        else:
            current_risk_pct = params.get("RISK_PERCENT", config.RISK_PER_TRADE_PERCENT)
            risk_usd = equity * (current_risk_pct / 100.0)
            raw_lot = risk_usd / (sl_distance * contract_size)
            
            if raw_lot < config.MIN_LOT_SIZE: 
                return f"ERR_LOT_TOO_SMALL|Risk:${risk_usd:.2f}|Min:{config.MIN_LOT_SIZE}"
            
            lot_size = round(raw_lot / config.LOT_STEP) * config.LOT_STEP

        lot_size = max(config.MIN_LOT_SIZE, min(lot_size, config.MAX_LOT_SIZE))
        sl_price = manual_sl if manual_sl > 0 else (price - sl_distance if direction == "BUY" else price + sl_distance)

        tp_price = 0.0
        if manual_tp > 0: 
            tp_price = manual_tp
        else:
            rr_ratio = params["TP_RR_RATIO"]
            real_sl_dist = abs(price - sl_price)
            tp_price = price + (real_sl_dist * rr_ratio) if direction == "BUY" else price - (real_sl_dist * rr_ratio)

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        comment = f"[USER]_{preset_name}"
        
        result = self.connector.place_order(symbol, order_type, lot_size, sl_price, tp_price, config.MAGIC_NUMBER, comment)
        
        if result and result.retcode == 10009:
            ticket_id = result.order
            self.state["trades_today_count"] += 1
            if ticket_id not in self.state["active_trades"]:
                self.state["active_trades"].append(ticket_id)
            
            self.update_trade_tactic(ticket_id, tsl_mode)
            
            actual_1r_dist = abs(price - sl_price)
            if "initial_r_dist" not in self.state: self.state["initial_r_dist"] = {}
            self.state["initial_r_dist"][str(ticket_id)] = actual_1r_dist
            save_state(self.state)

            final_risk_p = params.get("RISK_PERCENT", config.RISK_PER_TRADE_PERCENT)
            self.log(f"🚀 [USER EXEC] {direction} {symbol} #{ticket_id} | Vol: {lot_size:.2f} | Risk: {final_risk_p}% | TSL: {tsl_mode}")
            return f"SUCCESS|{ticket_id}"
        
        err_msg = result.comment if result else 'Unknown Connection Error'
        return f"ERR_MT5: {err_msg}"

    # ====================================================================================
    # 3. LOGIC CẬP NHẬT TRẠNG THÁI VÀ DỜI TSL (BASKET LOGIC TỪ BÁC - GIỮ NGUYÊN)
    # ====================================================================================
    def update_running_trades(self, account_type="STANDARD", market_context=None):
        tsl_status_map = {} 
        try:
            current_positions = self.connector.get_all_open_positions()
            current_tickets = [p.ticket for p in current_positions]
            tracked_tickets = list(self.state["active_trades"])
            
            # 1. XỬ LÝ LỆNH ĐÃ ĐÓNG
            closed_tickets = [t for t in tracked_tickets if t not in current_tickets]
            if closed_tickets:
                for ticket in closed_tickets:
                    s_ticket = str(ticket)
                    if s_ticket in self.state.get("trade_tactics", {}): 
                        del self.state["trade_tactics"][s_ticket]
                         
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
                                "time": datetime.now().strftime("%H:%M"),
                                "symbol": exit_deal.symbol,
                                "type": "BUY" if exit_deal.type==1 else "SELL",
                                "profit": profit,
                                "reason": reason
                            })
                            append_trade_log(ticket, exit_deal.symbol, "BUY" if exit_deal.type==1 else "SELL", exit_deal.volume, profit, reason)
                            
                    if ticket in self.state["active_trades"]:
                        self.state["active_trades"].remove(ticket)
                save_state(self.state)

            # 2. GOM CỤM LỆNH (Basket Logic)
            bot_positions = [p for p in current_positions if p.magic == config.MAGIC_NUMBER]
            baskets = {}
            for pos in bot_positions:
                key = (pos.symbol, pos.type)
                if key not in baskets: baskets[key] = []
                baskets[key].append(pos)

            # 3. THỰC THI TSL CHO TỪNG CỤM
            for key, basket_positions in baskets.items():
                basket_status = self._apply_basket_trailing_logic(basket_positions, market_context)
                for pos in basket_positions:
                    tsl_status_map[pos.ticket] = basket_status

        except Exception as e:
            self.log(f"❌ Lỗi TSL update loop: {e}", error=True)
        
        return tsl_status_map

    def _apply_basket_trailing_logic(self, basket_positions, market_context):
        if not basket_positions: return "Monitoring..."

        basket_positions.sort(key=lambda x: x.time)
        master_pos = basket_positions[0] 
        
        tactic_str = self.get_trade_tactic(master_pos.ticket)
        if tactic_str == "OFF": return "TSL OFF"

        active_modes = tactic_str.split("+")
        symbol = master_pos.symbol
        is_buy = (master_pos.type == mt5.ORDER_TYPE_BUY)
        current_price = master_pos.price_current 
        current_sl = master_pos.sl 
        
        sym_info = mt5.symbol_info(symbol)
        point = sym_info.point if sym_info else 0.00001
        
        total_volume = sum(p.volume for p in basket_positions)
        avg_entry = sum(p.price_open * p.volume for p in basket_positions) / total_volume
        total_profit_usd = sum(p.profit + getattr(p, 'swap', 0.0) + getattr(p, 'commission', 0.0) for p in basket_positions)
        
        s_ticket = str(master_pos.ticket)
        one_r_dist = self.state.get("initial_r_dist", {}).get(s_ticket, 0.0)

        if one_r_dist == 0:
            preset_name = master_pos.comment.split("_")[1] if (master_pos.comment and "_" in master_pos.comment) else "SCALPING"
            params = config.PRESETS.get(preset_name, config.PRESETS["SCALPING"])
            one_r_dist = avg_entry * (params["SL_PERCENT"] / 100.0)
            if "initial_r_dist" not in self.state: self.state["initial_r_dist"] = {}
            self.state["initial_r_dist"][s_ticket] = one_r_dist 

        if one_r_dist <= 0: return "Err R Dist"

        curr_dist = current_price - avg_entry if is_buy else avg_entry - current_price
        curr_r = curr_dist / one_r_dist
        
        candidates = []
        milestones = [] 
        tsl_cfg = config.TSL_CONFIG

        # 1. BREAK-EVEN
        if "BE" in active_modes:
            total_fee_usd = abs(sum(getattr(p, 'commission', 0.0) + getattr(p, 'swap', 0.0) for p in basket_positions))
            fee_dist = total_fee_usd / (total_volume * sym_info.trade_contract_size) if sym_info.trade_contract_size > 0 else 0
            
            mode = tsl_cfg.get("BE_MODE", "SOFT")
            base = avg_entry - fee_dist if (is_buy and mode=="SOFT") else (avg_entry + fee_dist if (is_buy and mode=="SMART") else avg_entry)
            if not is_buy: base = avg_entry + fee_dist if mode=="SOFT" else (avg_entry - fee_dist if mode=="SMART" else avg_entry)

            be_sl = base + (tsl_cfg.get("BE_OFFSET_POINTS", 0) * point) if is_buy else base - (tsl_cfg.get("BE_OFFSET_POINTS", 0) * point)
            trig_r = tsl_cfg.get("BE_OFFSET_RR", 0.8)
            trig_p = avg_entry + (one_r_dist * trig_r) if is_buy else avg_entry - (one_r_dist * trig_r)
            
            if curr_r >= trig_r: candidates.append((be_sl, "BE (Basket)"))
            else: milestones.append((abs(current_price - trig_p), f"BE | {trig_p:.2f} -> {be_sl:.2f}"))

        # 2. STEP R
        if "STEP_R" in active_modes:
            sz, rt = tsl_cfg.get("STEP_R_SIZE", 1.0), tsl_cfg.get("STEP_R_RATIO", 0.8)
            steps = max(0, math.floor(curr_r / sz))
            if steps >= 1:
                step_sl = avg_entry + (steps * one_r_dist * rt) if is_buy else avg_entry - (steps * one_r_dist * rt)
                candidates.append((step_sl, f"STEP {steps} (Basket)"))
            
            next_step = int(steps + 1)
            n_trig = avg_entry + (next_step * sz * one_r_dist) if is_buy else avg_entry - (next_step * sz * one_r_dist)
            n_sl = avg_entry + (next_step * one_r_dist * rt) if is_buy else avg_entry - (next_step * one_r_dist * rt)
            milestones.append((abs(current_price - n_trig), f"Step {next_step} | {n_trig:.2f} -> {n_sl:.2f}"))

        # 3. PNL LOCK
        if "PNL" in active_modes:
            acc = self.connector.get_account_info()
            if acc:
                pnl_pct = (total_profit_usd / acc['balance']) * 100
                levels = sorted(tsl_cfg["PNL_LEVELS"], key=lambda x: x[0])
                best_pnl_sl = None
                for lvl in levels:
                    if pnl_pct >= lvl[0]:
                        lock_dist = (acc['balance'] * (lvl[1]/100.0)) / (total_volume * sym_info.trade_contract_size)
                        best_pnl_sl = avg_entry + lock_dist if is_buy else avg_entry - lock_dist
                    else:
                        req_profit_usd = acc['balance'] * (lvl[0]/100.0)
                        trig_p = avg_entry + (req_profit_usd / (total_volume * sym_info.trade_contract_size)) if is_buy else \
                                 avg_entry - (req_profit_usd / (total_volume * sym_info.trade_contract_size))
                        milestones.append((abs(current_price - trig_p), f"PnL {lvl[0]}% | {trig_p:.2f}"))
                        break
                if best_pnl_sl: candidates.append((best_pnl_sl, "PNL (Basket)"))

        # 4. TSL SWING
        if "SWING" in active_modes and market_context:
            sh, sl, atr = market_context.get("swing_high"), market_context.get("swing_low"), market_context.get("atr")
            trend_adx = market_context.get("trend", "UP")
            
            if sh and sl and atr and str(sh) != "--" and str(sl) != "--":
                tsl_mode = getattr(config, "TSL_LOGIC_MODE", "STATIC")
                trail_buf = getattr(config, "trail_atr_buffer", 0.2)
                sh, sl, atr = float(sh), float(sl), float(atr)
                swing_sl = None
                
                if is_buy:
                    if tsl_mode == "AGGRESSIVE": swing_sl = sh - (trail_buf * atr)
                    elif tsl_mode == "DYNAMIC" and trend_adx != "UP": swing_sl = sh - (trail_buf * atr)
                    else: swing_sl = sl - (trail_buf * atr)
                else:
                    if tsl_mode == "AGGRESSIVE": swing_sl = sl + (trail_buf * atr)
                    elif tsl_mode == "DYNAMIC" and trend_adx != "DOWN": swing_sl = sl + (trail_buf * atr)
                    else: swing_sl = sh + (trail_buf * atr)
                
                if swing_sl:
                    candidates.append((swing_sl, f"SWING ({tsl_mode})"))
                    milestones.append((0.0, f"SWING | {swing_sl:.2f}"))

        valid_moves = []
        for price, rule in candidates:
            price = round(price / point) * point
            if is_buy and price > current_sl + (point / 2): valid_moves.append((price, rule))
            elif not is_buy and (current_sl == 0 or price < current_sl - (point / 2)): valid_moves.append((price, rule))

        if valid_moves:
            best_move = max(valid_moves, key=lambda x: x[0]) if is_buy else min(valid_moves, key=lambda x: x[0])
            target_sl, action_rule = best_move
            
            if abs(target_sl - current_sl) > (point / 2):
                self.log(f"⚡ [TSL] {symbol} dời SL theo {action_rule} ➔ {target_sl:.5f}")
                for pos in basket_positions:
                     self.connector.modify_position(pos.ticket, target_sl, pos.tp)
                return f"MOVED {action_rule}"
            else:
                return action_rule

        if milestones:
            closest_milestone = sorted(milestones, key=lambda x: x[0])[0][1]
            return closest_milestone

        return "Monitoring..."