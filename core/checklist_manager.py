# -*- coding: utf-8 -*-
# FILE: core/checklist_manager.py
# Checklist Manager V4.4: Auto-detect Loss Mode & Smart UI Display

import config
import MetaTrader5 as mt5

class ChecklistManager:
    def __init__(self, connector):
        self.connector = connector

    def run_pre_trade_checks(self, account_info, state, symbol, strict_mode=True) -> dict:
        checks = []
        all_passed = True
        
        # 1. Connection & Ping & Spread Check
        if self.connector._is_connected:
            # --- A. CHECK PING ---
            try:
                ping_ms = mt5.terminal_info().ping_last / 1000
            except:
                ping_ms = 0
                
            ping_status = "OK"
            
            try:
                max_ping = config.MAX_PING_MS
            except AttributeError:
                max_ping = 150 

            if ping_ms > max_ping: 
                ping_status = "WARN"
                if strict_mode: 
                    all_passed = False 
                    ping_status = "FAIL"

            # --- B. CHECK SPREAD ---
            tick = mt5.symbol_info_tick(symbol)
            spread_points = 0
            if tick:
                point = mt5.symbol_info(symbol).point
                if point > 0:
                    spread_points = (tick.ask - tick.bid) / point
            
            try:
                max_spread = config.MAX_SPREAD_POINTS
            except AttributeError:
                max_spread = 50 

            # Format tin nhắn hiển thị chi tiết
            spread_msg = f"Ping {ping_ms:.0f}ms (Max {max_ping}) | Spr {spread_points:.0f} (Max {max_spread})"
            
            if spread_points > max_spread:
                if strict_mode:
                    checks.append({"name": "Mạng/Spread", "status": "FAIL", "msg": spread_msg})
                    all_passed = False
                else:
                    checks.append({"name": "Mạng/Spread", "status": "WARN", "msg": spread_msg})
            elif ping_status == "FAIL":
                 checks.append({"name": "Mạng/Spread", "status": "FAIL", "msg": spread_msg})
            else:
                 checks.append({"name": "Mạng/Spread", "status": "OK", "msg": spread_msg})

        else:
            checks.append({"name": "Kết nối MT5", "status": "FAIL", "msg": "Mất kết nối Server"})
            all_passed = False

        # 2. Account Check
        if not account_info:
             checks.append({"name": "Dữ liệu TK", "status": "FAIL", "msg": "Không lấy được dữ liệu"})
             return {"passed": False, "checks": checks}

        if state["starting_balance"] == 0:
            state["starting_balance"] = account_info.get('balance', 0)

        # 3. Daily Loss Check ($/%)
        start_bal = state["starting_balance"]
        pnl_today = state["pnl_today"]
        loss_pct = (pnl_today / start_bal * 100) if start_bal > 0 else 0
        max_loss_limit = -config.MAX_DAILY_LOSS_PERCENT
        
        loss_msg = f"{loss_pct:.2f}% (Limit {max_loss_limit}%)"
        
        if loss_pct <= max_loss_limit:
            checks.append({"name": "Daily Loss", "status": "FAIL", "msg": loss_msg})
            all_passed = False
        else:
            # Cảnh báo vàng nếu sắp chạm trần (còn cách 0.5%)
            if loss_pct <= (max_loss_limit + 0.5):
                checks.append({"name": "Daily Loss", "status": "WARN", "msg": loss_msg})
            else:
                checks.append({"name": "Daily Loss", "status": "OK", "msg": loss_msg})

        # 4. [UPDATED] Losing Trades Check (Hiển thị Mode Streak hay Total)
        current_losses = state.get("manual_daily_loss_count", 0) 
        max_allowed_losses = config.MAX_LOSING_STREAK
        
        # Tự động lấy tên Mode để hiển thị cho Boss biết
        mode_name = getattr(config, "LOSS_COUNT_MODE", "TOTAL")
        
        # Ví dụ hiển thị: "[Total] 1 (Max 3)" hoặc "[Streak] 2 (Max 3)"
        loss_count_msg = f"[{mode_name}] {current_losses} (Max {max_allowed_losses})"
        
        if current_losses >= max_allowed_losses:
            checks.append({"name": "Số Lệnh Thua", "status": "FAIL", "msg": loss_count_msg})
            all_passed = False
        else:
            checks.append({"name": "Số Lệnh Thua", "status": "OK", "msg": loss_count_msg})

        # 5. Trades Today Check (Hiển thị Max)
        count = state["trades_today_count"]
        max_trades = config.MAX_TRADES_PER_DAY
        trade_msg = f"{count} (Max {max_trades})"
        
        if count >= max_trades:
            checks.append({"name": "Số Lệnh", "status": "FAIL", "msg": trade_msg})
            all_passed = False
        else:
             checks.append({"name": "Số Lệnh", "status": "OK", "msg": trade_msg})

        # 6. Open Position Check
        positions = self.connector.get_all_open_positions()
        bot_magic = getattr(config, "BOT_MAGIC_NUMBER", 9999)
        manual_magic = getattr(config, "MANUAL_MAGIC_NUMBER", 8888)
        my_pos = [p for p in positions if p.magic in (bot_magic, manual_magic)]
        
        try:
            max_open_pos = config.MAX_OPEN_POSITIONS
        except AttributeError:
            max_open_pos = 1

        pos_msg = f"Đang chạy: {len(my_pos)} (Max {max_open_pos})"

        if len(my_pos) >= max_open_pos:
            checks.append({"name": "Trạng thái", "status": "FAIL", "msg": pos_msg})
            all_passed = False
        else:
            checks.append({"name": "Trạng thái", "status": "OK", "msg": pos_msg})

        return {"passed": all_passed, "checks": checks}

    def run_bot_safeguard_checks(self, account_info, state, symbol, safeguard_cfg) -> dict:
        checks = []
        all_passed = True
        
        max_loss_pct = float(safeguard_cfg.get("MAX_DAILY_LOSS_PERCENT", 2.5))
        max_open = int(safeguard_cfg.get("MAX_OPEN_POSITIONS", 3))
        max_trades = int(safeguard_cfg.get("MAX_TRADES_PER_DAY", 30))
        max_streak = int(safeguard_cfg.get("MAX_LOSING_STREAK", 3))
        loss_mode = safeguard_cfg.get("LOSS_COUNT_MODE", "TOTAL")
        
        check_ping = safeguard_cfg.get("CHECK_PING", True)
        max_ping = int(safeguard_cfg.get("MAX_PING_MS", 150))
        check_spread = safeguard_cfg.get("CHECK_SPREAD", True)
        max_spread = int(safeguard_cfg.get("MAX_SPREAD_POINTS", 50))

        if not self.connector._is_connected:
            return {"passed": False, "checks": [{"name": "Kết nối", "status": "FAIL", "msg": "Mất kết nối MT5"}]}

        if not account_info:
            return {"passed": False, "checks": [{"name": "Dữ liệu", "status": "FAIL", "msg": "Không có Account Info"}]}

        if check_ping:
            try: ping_ms = mt5.terminal_info().ping_last / 1000
            except: ping_ms = 0
            if ping_ms > max_ping:
                checks.append({"name": "Ping", "status": "FAIL", "msg": f"Ping {ping_ms:.0f}ms vượt mức {max_ping}ms"})
                all_passed = False

        if check_spread:
            tick = mt5.symbol_info_tick(symbol)
            spread_points = 0
            if tick:
                point = mt5.symbol_info(symbol).point
                if point > 0: spread_points = (tick.ask - tick.bid) / point
            if spread_points > max_spread:
                checks.append({"name": "Spread", "status": "FAIL", "msg": f"Spread {spread_points:.0f} vượt mức {max_spread}"})
                all_passed = False

        if state["starting_balance"] == 0:
            state["starting_balance"] = account_info.get('balance', 0)
        start_bal = state["starting_balance"]
        pnl_today = state["pnl_today"]
        loss_pct = (pnl_today / start_bal * 100) if start_bal > 0 else 0
        if loss_pct <= -max_loss_pct:
            checks.append({"name": "Daily Loss", "status": "FAIL", "msg": f"Lỗ {loss_pct:.2f}% chạm trần {max_loss_pct}%"})
            all_passed = False

        count = state["trades_today_count"]
        if count >= max_trades:
            checks.append({"name": "Số Lệnh", "status": "FAIL", "msg": f"Đã đánh {count} lệnh (Max {max_trades})"})
            all_passed = False

        current_losses = state.get("bot_daily_loss_count", 0) 
        if current_losses >= max_streak:
            checks.append({"name": "Lệnh Thua", "status": "FAIL", "msg": f"[{loss_mode}] {current_losses} lệnh thua (Max {max_streak})"})
            all_passed = False

        positions = self.connector.get_all_open_positions()
        bot_magic = getattr(config, "BOT_MAGIC_NUMBER", 9999)
        my_pos = [p for p in positions if p.magic == bot_magic]
        if len(my_pos) >= max_open:
            checks.append({"name": "Trạng thái", "status": "FAIL", "msg": f"Đang chạy {len(my_pos)} lệnh (Max {max_open})"})
            all_passed = False

        return {"passed": all_passed, "checks": checks}