# -*- coding: utf-8 -*-
# FILE: core/trade_manager.py
# V3.0: UNIFIED TRADE MANAGER - FAST STATELESS TSL (KAISER EDITION FINAL)

import logging
import json
import os
import time
import MetaTrader5 as mt5
import config
from core.data_engine import data_engine
from core.storage_manager import load_state, save_state  # THÊM save_state

class TradeManager:
    def __init__(self, connector, checklist_manager, log_callback=None):
        self.connector = connector
        self.checklist = checklist_manager
        self.log_callback = log_callback 
        self.brain_path = "data/brain_settings.json"
        self.last_brain_read = 0
        self.brain_settings = {}
        self.state = load_state() 
        
        # Đảm bảo state luôn có biến này để không bị lỗi
        if "active_trades" not in self.state: 
            self.state["active_trades"] = []
        if "trade_tactics" not in self.state:
            self.state["trade_tactics"] = {}

    def log(self, msg, error=False):
        if self.log_callback: 
            self.log_callback(msg, error=error)
        else: 
            logger = logging.getLogger("TradeManager")
            if error: logger.error(msg)
            else: logger.info(msg)

    def _get_brain_settings(self):
        now = time.time()
        if now - self.last_brain_read > 5:
            try:
                if os.path.exists(self.brain_path):
                    with open(self.brain_path, "r", encoding="utf-8") as f:
                        self.brain_settings = json.load(f)
                self.last_brain_read = now
            except Exception as e:
                self.log(f"Lỗi đọc Brain Settings: {e}", error=True)
        return self.brain_settings

    # ====================================================================================
    # 1. HÀM THỰC THI LỆNH CHO BOT 
    # ====================================================================================
    def execute_bot_trade(self, direction, symbol, context, market_mode="ANY"):
        config.SYMBOL = symbol 
        
        acc_info = self.connector.get_account_info()
        bot_bypass = getattr(config, "BOT_BYPASS_CHECKLIST", True) 

        res = self.checklist.run_pre_trade_checks(acc_info, self.state, symbol, strict_mode=not bot_bypass)
        if not res["passed"]:
            if bot_bypass:
                self.log(f"⚠️ [BOT FORCE] Bỏ qua cảnh báo an toàn Checklist để test")
            else:
                fail_reasons = [c['msg'] for c in res['checks'] if c['status'] == 'FAIL']
                self.log(f"⚠️ [BOT BLOCKED] Bị chặn bởi an toàn: {fail_reasons}", error=True)
                return "CHECKLIST_FAIL"

        tick = mt5.symbol_info_tick(symbol)
        sym_info = mt5.symbol_info(symbol)
        if not tick or not sym_info: 
            self.log("❌ [BOT] Thiếu dữ liệu Tick từ sàn.", error=True)
            return "ERR_NO_TICK"
        
        current_price = tick.ask if direction == "BUY" else tick.bid

        # --- SMART SL ---
        sl_mode = getattr(config, "ENTRY_SL_MODE", "Swing M15 + ATR")
        buffer_atr = context.get("atr_entry", 0.0005)
        
        if sl_mode == "Swing M15 + ATR":
            sl_price = context.get("swing_low_entry", current_price) - buffer_atr if direction == "BUY" else context.get("swing_high_entry", current_price) + buffer_atr
        elif sl_mode == "Swing H1 + ATR":
            sl_price = context.get("swing_low_trend", current_price) - (buffer_atr * 1.5) if direction == "BUY" else context.get("swing_high_trend", current_price) + (buffer_atr * 1.5)
        elif sl_mode == "Fibo 61.8%":
            sl_price = context.get("fibo_618_support", current_price - buffer_atr*2) if direction == "BUY" else context.get("fibo_618_resistance", current_price + buffer_atr*2)
        else:
            sl_price = current_price - (buffer_atr * 2) if direction == "BUY" else current_price + (buffer_atr * 2)

        sl_distance = abs(current_price - sl_price)
        if sl_distance <= 0: return "ERR_CALC_SL_ZERO"

        reward_ratio = getattr(config, "REWARD_RATIO", 1.5)
        tp_price = current_price + (sl_distance * reward_ratio) if direction == "BUY" else current_price - (sl_distance * reward_ratio)

        # --- TÍNH VOLUME ---
        brain = self._get_brain_settings()
        risk_tsl = brain.get("risk_tsl", {})
        base_risk = risk_tsl.get("base_risk", getattr(config, "BOT_RISK_PERCENT", 0.3))
        mode_multiplier = risk_tsl.get("mode_multipliers", {}).get(market_mode, 1.0)
        final_risk_percent = base_risk * mode_multiplier

        equity = acc_info['equity']
        contract_size = sym_info.trade_contract_size
        risk_usd = equity * (final_risk_percent / 100.0)
        raw_lot = risk_usd / (sl_distance * contract_size)
        lot_size = round(raw_lot / config.LOT_STEP) * config.LOT_STEP
        lot_size = max(config.MIN_LOT_SIZE, min(lot_size, config.MAX_LOT_SIZE))

        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL
        comment = f"[BOT]_AUTO_{market_mode}"
        bot_magic = getattr(config, "BOT_MAGIC_NUMBER", 9999)
        
        result = self.connector.place_order(symbol, order_type, lot_size, sl_price, tp_price, bot_magic, comment)
        
        if result and result.retcode == 10009:
            ticket_id = result.order
            self.log(f"🚀 [BOT EXEC] {direction} {symbol} #{ticket_id} | Lot: {lot_size:.2f} | Risk: {final_risk_percent}%")
            return "SUCCESS"
        
        err_msg = result.comment if result else 'Unknown Connection Error'
        self.log(f"❌ [BOT ERR] Sàn từ chối lệnh: {err_msg}", error=True)
        return "MT5_ERROR"

    # ====================================================================================
    # 2. HÀM THỰC THI LỆNH TAY
    # ====================================================================================
    def execute_manual_trade(self, direction, preset_name, symbol, strict_mode, 
                             manual_lot=0.0, manual_tp=0.0, manual_sl=0.0, bypass_checklist=False, tactic_str=""):
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
        manual_magic = getattr(config, "MANUAL_MAGIC_NUMBER", 8888)
        
        result = self.connector.place_order(symbol, order_type, lot_size, sl_price, tp_price, manual_magic, comment)
        
        if result and result.retcode == 10009:
            ticket_id = result.order
            self.update_trade_tactic(ticket_id, tactic_str) 
            self.log(f"🚀 [USER EXEC] {direction} {symbol} #{ticket_id} | Vol: {lot_size:.2f}")
            return f"SUCCESS|{ticket_id}"
        
        return f"ERR_MT5: {result.comment if result else 'Unknown Connection Error'}"

    def update_trade_tactic(self, ticket, tactic_str):
        self.state["trade_tactics"][str(ticket)] = tactic_str
        save_state(self.state) # ĐÃ FIX: Lưu vĩnh viễn xuống ổ cứng

    def get_trade_tactic(self, ticket):
        return self.state.get("trade_tactics", {}).get(str(ticket), "OFF")

    # ====================================================================================
    # 3. QUẢN LÝ LỆNH CHẠY (TSL & DỌN RÁC)
    # ====================================================================================
    def update_running_trades(self, account_type="STANDARD", all_market_contexts=None):
        tsl_status_map = {} 
        try:
            current_positions = self.connector.get_all_open_positions()
            current_tickets = [p.ticket for p in current_positions]
            
            # --- ĐÃ FIX: DỌN DẸP LỆNH ĐÓNG ĐỂ UI HIỂN THỊ ĐÚNG ---
            tracked_tickets = list(self.state.get("active_trades", []))
            closed_tickets = [t for t in tracked_tickets if t not in current_tickets]
            
            if closed_tickets:
                for ticket in closed_tickets:
                    self.log(f"📉 Phát hiện lệnh #{ticket} đã đóng.")
                    if ticket in self.state["active_trades"]:
                        self.state["active_trades"].remove(ticket)
                    if str(ticket) in self.state.get("trade_tactics", {}): 
                        del self.state["trade_tactics"][str(ticket)]
                save_state(self.state)
            # -----------------------------------------------------

            bot_magic = getattr(config, "BOT_MAGIC_NUMBER", 9999)
            manual_magic = getattr(config, "MANUAL_MAGIC_NUMBER", 8888)
            tracked_positions = [p for p in current_positions if p.magic in (bot_magic, manual_magic)]
            
            needs_save = False
            for pos in tracked_positions:
                if pos.ticket not in self.state["active_trades"]:
                    self.state["active_trades"].append(pos.ticket)
                    needs_save = True
                
                self._apply_advanced_tsl(pos)
                tsl_status_map[pos.ticket] = "Running"
                
            if needs_save: save_state(self.state)

        except Exception as e:
            self.log(f"❌ Lỗi TSL update loop: {e}", error=True)
        
        return tsl_status_map

    def _apply_advanced_tsl(self, pos):
        symbol = pos.symbol
        tick = mt5.symbol_info_tick(symbol)
        sym_info = mt5.symbol_info(symbol)
        if not tick or not sym_info: return

        current_price = tick.bid if pos.type == mt5.ORDER_TYPE_BUY else tick.ask
        is_buy = pos.type == mt5.ORDER_TYPE_BUY
        
        net_profit = pos.profit + pos.swap + getattr(pos, 'commission', 0.0)
        if net_profit <= 0 or pos.sl <= 0: return 

        sl_distance_points = abs(pos.price_open - pos.sl)
        if sl_distance_points == 0 or sym_info.trade_tick_size == 0: return

        initial_risk_money = (sl_distance_points / sym_info.trade_tick_size) * sym_info.trade_tick_value * pos.volume
        if initial_risk_money <= 0: return 

        r_multiple = net_profit / initial_risk_money
        candidates = []
        brain = self._get_brain_settings()
        tsl_cfg = brain.get("tsl_config", getattr(config, "TSL_CONFIG", {}))
        
        breakeven_buffer = getattr(config, "BREAKEVEN_BUFFER_POINTS", 10) * sym_info.point

        if r_multiple >= 1.0 and r_multiple < 2.0:
            be_sl = pos.price_open + breakeven_buffer if is_buy else pos.price_open - breakeven_buffer
            candidates.append(be_sl)
        elif r_multiple >= 2.0:
            lock_distance = sl_distance_points * int(r_multiple - 1)
            step_sl = pos.price_open + lock_distance if is_buy else pos.price_open - lock_distance
            candidates.append(step_sl)

        acc = self.connector.get_account_info()
        pnl_levels = tsl_cfg.get("PNL_LEVELS", []) 
        if acc and pnl_levels:
            pnl_pct = (net_profit / acc['balance']) * 100
            for lvl in sorted(pnl_levels, key=lambda x: x[0]):
                if pnl_pct >= lvl[0]:
                    lock_dist_money = acc['balance'] * (lvl[1] / 100.0)
                    lock_points = (lock_dist_money / (sym_info.trade_tick_value * pos.volume)) * sym_info.trade_tick_size
                    pnl_sl = pos.price_open + lock_points if is_buy else pos.price_open - lock_points
                    candidates.append(pnl_sl)

        if r_multiple >= 3.0: 
            _, _, context = data_engine.fetch_and_prepare(symbol)
            if context:
                trail_buf = getattr(config, "trail_atr_buffer", 0.2)
                atr = context.get("atr_entry", 0.0005)
                sh = context.get("swing_high_entry", 0)
                sl = context.get("swing_low_entry", 0)
                if sh > 0 and sl > 0:
                    swing_sl = sl - (trail_buf * atr) if is_buy else sh + (trail_buf * atr)
                    candidates.append(swing_sl)

        if not candidates: return

        best_sl = max(candidates) if is_buy else min(candidates)
        min_stop_level = sym_info.trade_stops_level * sym_info.point
        
        if is_buy:
            if best_sl > pos.sl and best_sl <= (current_price - min_stop_level):
                self.connector.modify_position(pos.ticket, best_sl, pos.tp)
                self.log(f"⚡ [TSL] Dời SL #{pos.ticket} ➔ {best_sl:.5f}")
        else:
            if best_sl < pos.sl and best_sl >= (current_price + min_stop_level):
                self.connector.modify_position(pos.ticket, best_sl, pos.tp)
                self.log(f"⚡ [TSL] Dời SL #{pos.ticket} ➔ {best_sl:.5f}")