# -*- coding: utf-8 -*-
# FILE: core/trade_manager.py
# V4.4 (FINAL): UNIFIED TRADE MANAGER - DYNAMIC MACRO, REVERSE CLOSE & CASH TSL (KAISER EDITION)

import logging
import json
import os
import time
import math
import threading
from datetime import datetime, timedelta
import MetaTrader5 as mt5
import config
from core.data_engine import data_engine
from core.storage_manager import load_state, save_state, append_trade_log


class TradeManager:
    def __init__(self, connector, checklist_manager, log_callback=None):
        self.connector = connector
        self.checklist = checklist_manager
        self.log_callback = log_callback
        self.brain_path = "data/brain_settings.json"
        self.last_brain_read = 0
        self.brain_settings = {}
        self.state = load_state()

        if "active_trades" not in self.state:
            self.state["active_trades"] = []
        if "trade_tactics" not in self.state:
            self.state["trade_tactics"] = {}
        if "parent_baskets" not in self.state:
            self.state["parent_baskets"] = {}
        if "child_to_parent" not in self.state:
            self.state["child_to_parent"] = {}
        if "initial_r_dist" not in self.state:
            self.state["initial_r_dist"] = {}

        # [NEW V4.4] Tracking chuyên sâu cho Cooldown và Log
        if "exit_reasons" not in self.state:
            self.state["exit_reasons"] = {}
        if "last_close_times" not in self.state:
            self.state["last_close_times"] = {}

    def log(self, msg, error=False, target=None):
        if self.log_callback:
            try:
                self.log_callback(msg, error=error, target=target)
            except TypeError:
                self.log_callback(msg, error=error)
        else:
            logger = logging.getLogger("TradeManager")
            if error:
                logger.error(msg)
            else:
                logger.info(msg)

    def _get_brain_settings(self):
        now = time.time()
        if now - self.last_brain_read > 5:
            try:
                if os.path.exists(self.brain_path):
                    with open(self.brain_path, "r", encoding="utf-8") as f:
                        self.brain_settings = json.load(f)
                self.last_brain_read = now
            except Exception:
                pass
        return self.brain_settings

    def check_and_trigger_cooldown(self):
        brain = self._get_brain_settings()
        safeguard_cfg = brain.get("bot_safeguard", {})
        
        max_loss_pct = float(safeguard_cfg.get("MAX_DAILY_LOSS_PERCENT", 2.5))
        max_trades = int(safeguard_cfg.get("MAX_TRADES_PER_DAY", 30))
        max_streak = int(safeguard_cfg.get("MAX_LOSING_STREAK", 3))
        cooldown_hours = float(safeguard_cfg.get("GLOBAL_COOLDOWN_HOURS", 4.0))
        
        start_bal = self.state.get("starting_balance", 0)
        pnl = self.state.get("bot_pnl_today", 0.0)
        loss_pct = (pnl / start_bal * 100) if start_bal > 0 else 0
        
        trades = self.state.get("bot_trades_today", 0)
        losses = self.state.get("bot_daily_loss_count", 0)
        
        triggered = False
        reason = ""
        
        if loss_pct <= -max_loss_pct:
            triggered = True
            reason = f"Chạm Max Loss ({loss_pct:.2f}% / {max_loss_pct}%)"
        elif trades >= max_trades:
            triggered = True
            reason = f"Chạm Max Trades ({trades}/{max_trades})"
        elif losses >= max_streak:
            triggered = True
            reason = f"Chạm Max Streak ({losses}/{max_streak})"
            
        if triggered:
            from core.storage_manager import reset_bot_session
            cooldown_until = time.time() + (cooldown_hours * 3600)
            
            # Đóng tất cả các lệnh bot đang chạy nếu có cấu hình CLOSE_ALL_ON_COOLDOWN (tùy chọn)
            # Ở đây ta chỉ reset cache và chặn mở lệnh mới. Lệnh cũ vẫn chạy.
            
            reset_bot_session(f"Hit Limit: {reason}")
            
            # Cập nhật lại state sau khi reset
            self.state = load_state()
            self.state["cooldown_until"] = cooldown_until
            save_state(self.state)
            
            self.log(f"🛑 [SAFEGUARD] {reason}. Bot bước vào Global Cooldown trong {cooldown_hours} giờ.", target="bot")

    # ====================================================================================
    # [NEW V4.4] HÀM CẮT LỆNH KHI CÓ TÍN HIỆU ĐẢO CHIỀU (REVERSE SIGNAL)
    # ====================================================================================
    def close_opposite_positions(self, symbol, new_direction, min_hold_time=180):
        bot_magic = getattr(config, "BOT_MAGIC_NUMBER", 9999)
        positions = [
            p
            for p in self.connector.get_all_open_positions()
            if p.symbol == symbol and p.magic == bot_magic
        ]
        opposite_type = (
            mt5.ORDER_TYPE_SELL if new_direction == "BUY" else mt5.ORDER_TYPE_BUY
        )

        closed_count = 0
        now = time.time()

        for p in positions:
            if p.type == opposite_type:
                hold_time = now - p.time
                if hold_time >= min_hold_time:
                    self.log(
                        f"🔄 [REVERSE] Tín hiệu đảo chiều ({new_direction})! Cắt lệnh #{p.ticket} (Hold: {hold_time:.0f}s)",
                        target="bot",
                    )
                    self.state["exit_reasons"][str(p.ticket)] = (
                        f"Reverse_to_{new_direction}"
                    )

                    # Chạy luồng ẩn để cắt lệnh không làm kẹt
                    threading.Thread(
                        target=self.connector.close_position,
                        args=(p,),
                        daemon=True,
                    ).start()
                    closed_count += 1
                else:
                    self.log(
                        f"⏳ [REVERSE] Bỏ qua cắt đảo chiều lệnh #{p.ticket} do chưa đủ Min Hold Time ({hold_time:.0f}s < {min_hold_time}s)",
                        target="bot",
                    )

        return closed_count

    # ====================================================================================
    # 1. HÀM THỰC THI LỆNH CHO BOT (HỖ TRỢ ENTRY, DCA, PCA, DYNAMIC SL & STRICT RISK)
    # ====================================================================================
    def execute_bot_trade(
        self, direction, symbol, context, market_mode="ANY", signal_class="ENTRY"
    ):
        config.SYMBOL = symbol
        acc_info = self.connector.get_account_info()
        brain = self._get_brain_settings()
        safeguard_cfg = brain.get("bot_safeguard", {})

        # [NEW V4.4] KIỂM TRA ĐẢO CHIỀU TRƯỚC KHI VÀO LỆNH (Cắt lệnh ngược chiều giải phóng Margin)
        close_on_reverse = safeguard_cfg.get("CLOSE_ON_REVERSE", False)
        if close_on_reverse and signal_class == "ENTRY":
            min_hold = safeguard_cfg.get("CLOSE_ON_REVERSE_MIN_TIME", 180)
            self.close_opposite_positions(symbol, direction, min_hold)

        # Gọi Checklist độc lập của Bot
        res = self.checklist.run_bot_safeguard_checks(
            acc_info, self.state, symbol, safeguard_cfg, signal_class
        )

        if not res["passed"]:
            fail_names = [c["name"] for c in res["checks"] if c["status"] == "FAIL"]
            fail_reasons = [c["msg"] for c in res["checks"] if c["status"] == "FAIL"]
            name_str = ",".join(fail_names) if fail_names else "UNK"
            reason_str = (
                " | ".join(fail_reasons)
                if fail_reasons
                else "Lỗi Safeguard không xác định"
            )
            return f"SAFEGUARD_FAIL|{name_str}|{reason_str}"

        tick = mt5.symbol_info_tick(symbol)
        sym_info = mt5.symbol_info(symbol)
        if not tick or not sym_info:
            return "ERR_NO_TICK"

        current_price = tick.ask if direction == "BUY" else tick.bid
        risk_tsl = brain.get("risk_tsl", {})
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

        # TÍNH TOÁN SMART SL TỪ CẤU HÌNH BRAIN
        sl_group = risk_tsl.get("base_sl", "G2")
        if "DYNAMIC" in sl_group:
            sl_group = "G1" if market_mode in ["TREND", "BREAKOUT"] else "G2"

        atr_key = f"atr_{sl_group}"
        swing_l_key = f"swing_low_{sl_group}"
        swing_h_key = f"swing_high_{sl_group}"

        # CHỐT CHẶN 1: Bẫy lỗi mất Data
        if atr_key not in context or swing_l_key not in context or swing_h_key not in context:
            return f"SAFEGUARD_FAIL|No_Data|Mất dữ liệu Swing/ATR của {sl_group}. Từ chối vào lệnh."

        buffer_atr = context.get(atr_key)
        swing_l = context.get(swing_l_key)
        swing_h = context.get(swing_h_key)

        sl_price = swing_l - buffer_atr if direction == "BUY" else swing_h + buffer_atr
        sl_distance = abs(current_price - sl_price)

        # CHỐT CHẶN 2: Bẫy lỗi SL cực hẹp (Nhỏ hơn 0.05% giá trị tài sản)
        min_safe_dist = current_price * 0.0005 
        if sl_distance < min_safe_dist:
            return f"SAFEGUARD_FAIL|SL_Too_Tight|Khoảng cách SL quá hẹp ({sl_distance:.5f}). Từ chối để chống nổ Lot."

        parent_pos = None
        bot_magic = getattr(config, "BOT_MAGIC_NUMBER", 9999)
        if signal_class in ["DCA", "PCA"]:
            positions = [
                p
                for p in self.connector.get_all_open_positions()
                if p.symbol == symbol and p.magic == bot_magic
            ]
            if positions:
                parent_pos = sorted(positions, key=lambda x: x.time)[0]

        strict_fee_per_lot = 0.0
        if risk_tsl.get("strict_risk", False):
            acc_type = getattr(config, "DEFAULT_ACCOUNT_TYPE", "STANDARD")
            if acc_type in ["PRO", "STANDARD"]:
                comm_rate = 0.0
            else:
                comm_rate = getattr(config, "COMMISSION_RATES", {}).get(
                    symbol,
                    getattr(config, "ACCOUNT_TYPES_CONFIG", {})
                    .get(acc_type, {})
                    .get("COMMISSION_PER_LOT", 7.0),
                )
            spread_cost = (
                sym_info.spread * sym_info.point * sym_info.trade_contract_size
                if sym_info
                else 0.0
            )
            strict_fee_per_lot = comm_rate + spread_cost

        # [NEW V4.4] TÍNH VOLUME - TÍCH HỢP FIXED LOT & STRICT MIN LOT
        sym_cfgs = brain.get("symbol_configs", {}).get(symbol, {})
        fixed_lot = float(sym_cfgs.get("fixed_lot", 0.0))
        strict_min_lot = safeguard_cfg.get("STRICT_MIN_LOT", False)

        if parent_pos and signal_class in ["DCA", "PCA"]:
            cfg_key = "dca_config" if signal_class == "DCA" else "pca_config"
            mult = brain.get(
                cfg_key, getattr(config, f"{signal_class}_CONFIG", {})
            ).get("STEP_MULTIPLIER", 1.5)
            raw_lot = parent_pos.volume * mult
            lot_size = round(raw_lot / getattr(config, "LOT_STEP", 0.01)) * getattr(
                config, "LOT_STEP", 0.01
            )
            lot_size = max(config.MIN_LOT_SIZE, min(lot_size, config.MAX_LOT_SIZE))

        elif fixed_lot > 0:
            lot_size = fixed_lot
            # Vẫn gọi qua connector để lấy safe_sl chống lỗi sàn
            _, safe_sl = self.connector.calculate_lot_size(
                symbol, 10.0, sl_price, order_type, 0
            )
            sl_price = safe_sl if safe_sl else sl_price

        else:
            base_risk = risk_tsl.get(
                "base_risk", getattr(config, "BOT_RISK_PERCENT", 0.3)
            )
            mode_multiplier = risk_tsl.get("mode_multipliers", {}).get(market_mode, 1.0)
            final_risk_percent = base_risk * mode_multiplier
            risk_usd = acc_info["equity"] * (final_risk_percent / 100.0)

            calc_lot, safe_sl = self.connector.calculate_lot_size(
                symbol, risk_usd, sl_price, order_type, strict_fee_per_lot
            )

            # Xử lý Strict Min Lot Rejection
            if calc_lot is None or calc_lot == 0:
                if strict_min_lot:
                    return "SAFEGUARD_FAIL|Strict Min Lot|Từ chối do Vol tính toán < Min Lot (Rủi ro cao)"
                else:
                    return "ERR_LOT_CALC_FAILED"

            lot_size = calc_lot
            sl_price = safe_sl

        # [NEW V4.4] Áp dụng Max Lot Cap (Tính cho từng lệnh riêng lẻ)
        max_lot_cap = float(sym_cfgs.get("max_lot_cap", 0.0))
        if max_lot_cap > 0:
            lot_size = min(lot_size, max_lot_cap)

        # TÍNH TP
        if parent_pos and signal_class in ["DCA", "PCA"]:
            tp_price = parent_pos.tp
            sl_price = parent_pos.sl
        else:
            if safeguard_cfg.get("BOT_USE_TP", False):
                # Lấy đúng tên biến BOT_TP_RR_RATIO
                reward_ratio = getattr(config, "BOT_TP_RR_RATIO", 1.5)
                tp_price = (
                    current_price + (sl_distance * reward_ratio)
                    if direction == "BUY"
                    else current_price - (sl_distance * reward_ratio)
                )
            else:
                tp_price = 0.0

        comment = f"[BOT]_AUTO_{signal_class}"
        result = self.connector.place_order(
            symbol, order_type, lot_size, sl_price, tp_price, bot_magic, comment
        )

        if result and result.retcode == 10009:
            ticket_id = result.order
            bot_tactic = risk_tsl.get(
                "bot_tsl", getattr(config, "BOT_DEFAULT_TSL", "BE+STEP_R+SWING")
            )
            dca_cfg = brain.get("dca_config", getattr(config, "DCA_CONFIG", {}))
            pca_cfg = brain.get("pca_config", getattr(config, "PCA_CONFIG", {}))

            if dca_cfg.get("ENABLED", False) and "AUTO_DCA" not in bot_tactic:
                bot_tactic += "+AUTO_DCA"
            if pca_cfg.get("ENABLED", False) and "AUTO_PCA" not in bot_tactic:
                bot_tactic += "+AUTO_PCA"

            # [FIX V4.4]: Tự động gán Reverse Close (REV_C) cho lệnh Bot nếu được bật
            if (
                safeguard_cfg.get("CLOSE_ON_REVERSE", False)
                and "REV_C" not in bot_tactic
            ):
                bot_tactic += "+REV_C"

            self.update_trade_tactic(ticket_id, bot_tactic)
            self.state["initial_r_dist"][str(ticket_id)] = sl_distance

            if parent_pos and signal_class in ["DCA", "PCA"]:
                s_parent = str(parent_pos.ticket)
                s_child = str(ticket_id)
                if s_parent not in self.state["parent_baskets"]:
                    self.state["parent_baskets"][s_parent] = []
                self.state["parent_baskets"][s_parent].append(s_child)
                self.state["child_to_parent"][s_child] = s_parent
                self.state["initial_r_dist"][s_child] = self.state[
                    "initial_r_dist"
                ].get(s_parent, sl_distance)
                save_state(self.state)

                self.log(
                    f"🔥 [{signal_class}] Mẹ #{s_parent} đẻ Con #{s_child} | Vol: {lot_size:.2f}",
                    target="bot",
                )
                if signal_class == "DCA":
                    threading.Thread(
                        target=self._adjust_basket_tp,
                        args=(parent_pos.ticket,),
                        daemon=True,
                    ).start()
            else:
                self.log(
                    f"🚀 [BOT EXEC] {direction} {symbol} #{ticket_id} | Lot: {lot_size:.2f} | TSL: {bot_tactic}",
                    target="bot",
                )
                if signal_class == "ENTRY":
                    self.state["bot_last_entry_times"][symbol] = time.time()

                self.state["bot_trades_today"] = (
                    self.state.get("bot_trades_today", 0) + 1
                )
                self.state["trades_today_count"] = (
                    self.state.get("trades_today_count", 0) + 1
                )
                save_state(self.state)
                self.check_and_trigger_cooldown()

            return "SUCCESS"

        return "MT5_ERROR"

    def _adjust_basket_tp(self, parent_ticket):
        time.sleep(2)
        s_parent = str(parent_ticket)
        children = self.state.get("parent_baskets", {}).get(s_parent, [])
        if not children:
            return

        tickets = [parent_ticket] + [int(t) for t in children]
        positions = [
            p for p in self.connector.get_all_open_positions() if p.ticket in tickets
        ]
        if not positions:
            return

        total_lot = sum(p.volume for p in positions)
        total_value = sum(p.volume * p.price_open for p in positions)
        avg_price = total_value / total_lot

        sym_info = mt5.symbol_info(positions[0].symbol)
        is_buy = positions[0].type == mt5.ORDER_TYPE_BUY

        tp_offset = 50 * sym_info.point
        new_tp = avg_price + tp_offset if is_buy else avg_price - tp_offset
        new_tp = round(new_tp / sym_info.point) * sym_info.point

        for p in positions:
            if abs(p.tp - new_tp) > sym_info.point * 2:
                self.connector.modify_position(p.ticket, p.sl, new_tp)

        self.log(
            f"🔄 [BASKET RESCUE] Kéo TP Rổ #{parent_ticket} về: {new_tp:.5f}",
            target="bot",
        )

    # ====================================================================================
    # 2. HÀM THỰC THI LỆNH TAY (MANUAL)
    # ====================================================================================
    def execute_manual_trade(
        self,
        direction,
        preset_name,
        symbol,
        strict_mode,
        manual_lot=0.0,
        manual_tp=0.0,
        manual_sl=0.0,
        bypass_checklist=False,
        tactic_str="OFF",
    ):
        config.SYMBOL = symbol
        acc_info = self.connector.get_account_info()
        res = self.checklist.run_pre_trade_checks(
            acc_info, self.state, symbol, strict_mode
        )

        if not res["passed"] and not bypass_checklist:
            return "CHECKLIST_FAIL"

        params = getattr(config, "PRESETS", {}).get(
            preset_name, {"SL_PERCENT": 0.4, "TP_RR_RATIO": 1.5, "RISK_PERCENT": 0.3}
        )
        tick = mt5.symbol_info_tick(symbol)
        sym_info = mt5.symbol_info(symbol)
        if not tick or not sym_info:
            return "ERR_NO_TICK"

        price = tick.ask if direction == "BUY" else tick.bid
        equity = acc_info["equity"]
        order_type = mt5.ORDER_TYPE_BUY if direction == "BUY" else mt5.ORDER_TYPE_SELL

        if manual_sl > 0:
            sl_distance = abs(price - manual_sl)
        else:
            sl_distance = price * (params.get("SL_PERCENT", 0.5) / 100.0)

        if sl_distance <= 0:
            return "ERR_CALC_SL_ZERO"

        risk_pct = params.get("RISK_PERCENT", 0.3)
        sl_price = (
            manual_sl
            if manual_sl > 0
            else (price - sl_distance if direction == "BUY" else price + sl_distance)
        )

        if manual_lot > 0:
            lot_size = manual_lot
        else:
            strict_fee_per_lot = 0.0
            if params.get("STRICT_RISK", False):
                acc_type = getattr(config, "DEFAULT_ACCOUNT_TYPE", "STANDARD")
                if acc_type in ["PRO", "STANDARD"]:
                    comm_rate = 0.0
                else:
                    comm_rate = getattr(config, "COMMISSION_RATES", {}).get(
                        symbol,
                        getattr(config, "ACCOUNT_TYPES_CONFIG", {})
                        .get(acc_type, {})
                        .get("COMMISSION_PER_LOT", 7.0),
                    )

                spread_cost = (
                    sym_info.spread * sym_info.point * sym_info.trade_contract_size
                    if sym_info
                    else 0.0
                )
                strict_fee_per_lot = comm_rate + spread_cost

            risk_usd = equity * (risk_pct / 100.0)

            calc_lot, safe_sl = self.connector.calculate_lot_size(
                symbol, risk_usd, sl_price, order_type, strict_fee_per_lot
            )
            if calc_lot is None:
                return "ERR_LOT_CALC_FAILED"
            lot_size = calc_lot
            sl_price = safe_sl

        # [NEW V4.4] Áp dụng Max Lot Cap (Tính cho từng lệnh riêng lẻ)
        brain = self._get_brain_settings()
        sym_cfgs = brain.get("symbol_configs", {}).get(symbol, {})
        max_lot_cap = float(sym_cfgs.get("max_lot_cap", 0.0))
        if max_lot_cap > 0:
            lot_size = min(lot_size, max_lot_cap)

        if manual_tp > 0:
            tp_price = manual_tp
        else:
            tp_price = (
                price + (abs(price - sl_price) * params.get("TP_RR_RATIO", 1.5))
                if direction == "BUY"
                else price - (abs(price - sl_price) * params.get("TP_RR_RATIO", 1.5))
            )

        result = self.connector.place_order(
            symbol,
            order_type,
            lot_size,
            sl_price,
            tp_price,
            getattr(config, "MANUAL_MAGIC_NUMBER", 8888),
            f"[USER]_{preset_name}",
        )

        if result and result.retcode == 10009:
            self.update_trade_tactic(result.order, tactic_str)
            self.state["initial_r_dist"][str(result.order)] = abs(price - sl_price)

            self.state["manual_trades_today"] = (
                self.state.get("manual_trades_today", 0) + 1
            )
            self.state["trades_today_count"] = (
                self.state.get("trades_today_count", 0) + 1
            )

            save_state(self.state)
            self.log(
                f"🚀 [USER EXEC] {direction} {symbol} #{result.order} | Vol: {lot_size:.2f} | TSL: {tactic_str}"
            )
            return f"SUCCESS|{result.order}"

        return "MT5_ERROR"

    def update_trade_tactic(self, ticket, tactic_str):
        self.state["trade_tactics"][str(ticket)] = tactic_str
        save_state(self.state)

    def get_trade_tactic(self, ticket):
        return self.state.get("trade_tactics", {}).get(str(ticket), "OFF")

    # ====================================================================================
    # 3. QUẢN LÝ LỆNH CHẠY (TSL ĐỘC LẬP & DỌN RÁC RỔ LỆNH)
    # ====================================================================================
    def update_running_trades(self, account_type="STANDARD", all_market_contexts=None):
        tsl_status_map = {}
        try:
            current_positions = self.connector.get_all_open_positions()
            current_tickets = [p.ticket for p in current_positions]
            tracked_tickets = list(self.state.get("active_trades", []))

            # XỬ LÝ ĐÓNG LỆNH & CHỐT RỔ BẢO VỆ MẸ-CON
            closed_tickets = [t for t in tracked_tickets if t not in current_tickets]
            if closed_tickets:
                for ticket in closed_tickets:
                    s_ticket = str(ticket)

                    deals = mt5.history_deals_get(position=ticket)
                    if deals:
                        deal_out = [d for d in deals if d.entry == mt5.DEAL_ENTRY_OUT]
                        if deal_out:
                            d_out = deal_out[0]
                            real_pnl = d_out.profit + d_out.commission + d_out.swap

                            bot_magic = getattr(config, "BOT_MAGIC_NUMBER", 9999)
                            is_bot = d_out.magic == bot_magic

                            self.state["pnl_today"] += real_pnl

                            if real_pnl < 0:
                                self.state["daily_loss_count"] += 1

                            if is_bot:
                                self.state["bot_pnl_today"] = (
                                    self.state.get("bot_pnl_today", 0) + real_pnl
                                )
                                if real_pnl < 0:
                                    self.state["bot_daily_loss_count"] = (
                                        self.state.get("bot_daily_loss_count", 0) + 1
                                    )
                            else:
                                self.state["manual_pnl_today"] = (
                                    self.state.get("manual_pnl_today", 0) + real_pnl
                                )
                                if real_pnl < 0:
                                    self.state["manual_daily_loss_count"] = (
                                        self.state.get("manual_daily_loss_count", 0) + 1
                                    )

                            pos_type_str = (
                                "BUY" if d_out.type == mt5.DEAL_TYPE_SELL else "SELL"
                            )
                            pnl_sign = "+" if real_pnl >= 0 else ""

                            # [NEW V4.4] Lấy lý do thoát lệnh từ Tracker và lưu Cooldown
                            exit_reason = self.state.get("exit_reasons", {}).get(
                                s_ticket, "Closed"
                            )
                            self.state["last_close_times"][d_out.symbol] = time.time()

                            current_session = self.state.get("current_session_id", "LEGACY")
                            
                            entry_price = 0.0
                            deal_in = [d for d in deals if d.entry == mt5.DEAL_ENTRY_IN]
                            if deal_in:
                                entry_price = deal_in[0].price
                                
                            last_sl, last_tp = 0.0, 0.0
                            orders = mt5.history_orders_get(position=ticket)
                            if orders:
                                for ord in reversed(orders):
                                    if ord.sl > 0: last_sl = ord.sl
                                    if ord.tp > 0: last_tp = ord.tp
                                    if last_sl > 0 and last_tp > 0: break
                                    
                            fee = d_out.commission + d_out.swap

                            append_trade_log(
                                ticket,
                                d_out.symbol,
                                pos_type_str,
                                d_out.volume,
                                entry_price,
                                last_sl,
                                last_tp,
                                fee,
                                real_pnl,
                                exit_reason,
                                session_id=current_session
                            )
                            log_target = "bot" if is_bot else "manual"
                            self.log(
                                f"[DỌN DẸP] Đóng lệnh {pos_type_str} {d_out.symbol} #{ticket} ({exit_reason}) | PnL: {pnl_sign}${real_pnl:.2f}",
                                target=log_target,
                            )

                            # Cập nhật last_dca_pca_close_time nếu lệnh này là con (DCA/PCA)
                            from core.storage_manager import (
                                update_last_dca_pca_close_time,
                            )

                            bot_tactic = self.get_trade_tactic(ticket)
                            if "AUTO_DCA" in bot_tactic or "AUTO_PCA" in bot_tactic:
                                update_last_dca_pca_close_time(
                                    d_out.symbol, time.time()
                                )

                            if is_bot:
                                self.check_and_trigger_cooldown()

                    if ticket in self.state["active_trades"]:
                        self.state["active_trades"].remove(ticket)
                    for key in [
                        "trade_tactics",
                        "initial_r_dist",
                        "exit_reasons",
                        "initial_costs",
                    ]:
                        if s_ticket in self.state.get(key, {}):
                            del self.state[key][s_ticket]

                    # Basket Logic
                    if s_ticket in self.state.get("parent_baskets", {}):
                        child_tickets = self.state["parent_baskets"][s_ticket]
                        for child_t in child_tickets:
                            child_pos = next(
                                (
                                    p
                                    for p in current_positions
                                    if str(p.ticket) == str(child_t)
                                ),
                                None,
                            )
                            if child_pos:
                                self.log(
                                    f"⚠️ [BASKET CLOSE] Đóng lệnh Con #{child_t} do Mẹ #{ticket} đã chốt!",
                                    target="bot",
                                )
                                self.state["exit_reasons"][str(child_t)] = (
                                    "Parent_Closed"
                                )
                                threading.Thread(
                                    target=self.connector.close_position,
                                    args=(child_pos,),
                                    daemon=True,
                                ).start()
                        del self.state["parent_baskets"][s_ticket]

                    if s_ticket in self.state.get("child_to_parent", {}):
                        parent_t = self.state["child_to_parent"][s_ticket]
                        if (
                            parent_t in self.state.get("parent_baskets", {})
                            and s_ticket in self.state["parent_baskets"][parent_t]
                        ):
                            self.state["parent_baskets"][parent_t].remove(s_ticket)
                        del self.state["child_to_parent"][s_ticket]

                save_state(self.state)

            bot_magic = getattr(config, "BOT_MAGIC_NUMBER", 9999)
            manual_magic = getattr(config, "MANUAL_MAGIC_NUMBER", 8888)
            tracked_positions = [
                p for p in current_positions if p.magic in (bot_magic, manual_magic)
            ]

            needs_save = False
            for pos in tracked_positions:
                if pos.ticket not in self.state["active_trades"]:
                    self.state["active_trades"].append(pos.ticket)
                    needs_save = True

                sym_ctx = (
                    all_market_contexts.get(pos.symbol, {})
                    if all_market_contexts
                    else {}
                )
                tsl_status_map[pos.ticket] = self._apply_independent_tsl(pos, sym_ctx)

                if "ANTI_CASH" in self.get_trade_tactic(pos.ticket):
                    self._check_anti_cash(pos)

                if "REV_C" in self.get_trade_tactic(pos.ticket):
                    self._check_recovery(pos, sym_ctx)

            if needs_save:
                save_state(self.state)

        except Exception as e:
            self.log(f"❌ Lỗi update loop: {e}", error=True)
        return tsl_status_map

    def _check_anti_cash(self, pos):
        tsl_cfg = self._get_brain_settings().get(
            "tsl_config", getattr(config, "TSL_CONFIG", {})
        )
        hard_stop_usd = float(tsl_cfg.get("ANTI_CASH_USD", 10.0))
        time_cut_s = int(tsl_cfg.get("ANTI_CASH_TIME", 60))

        profit_usd = pos.profit + pos.swap + getattr(pos, "commission", 0.0)

        # [NEW V4.4] Tự động cộng phí sàn ban đầu vào ngưỡng cắt lỗ
        s_ticket = str(pos.ticket)
        if "initial_costs" not in self.state:
            self.state["initial_costs"] = {}
        if s_ticket not in self.state["initial_costs"]:
            # Phí ban đầu = |Profit âm lúc mới mở + Commission + Swap|
            init_cost = abs(
                min(0, pos.profit) + pos.swap + getattr(pos, "commission", 0.0)
            )
            self.state["initial_costs"][s_ticket] = init_cost
            save_state(self.state)

        initial_cost = self.state["initial_costs"].get(s_ticket, 0.0)
        dynamic_threshold = hard_stop_usd + initial_cost

        # Option 1: Hard Cash Stop (Dynamic Threshold)
        if profit_usd <= -dynamic_threshold:
            self.log(
                f"🔥 [ANTI CASH] Đạt ngưỡng Hard Stop (-${hard_stop_usd} + Phí ${initial_cost:.2f})! Cắt lỗ lệnh #{pos.ticket}",
                target="bot",
            )
            self.state["exit_reasons"][str(pos.ticket)] = "Anti_Cash_Hard_Stop"
            threading.Thread(
                target=self.connector.close_position, args=(pos,), daemon=True
            ).start()
            return

        # Option 2: Time & Drawdown Cut
        hold_time = time.time() - pos.time
        if hold_time > time_cut_s and profit_usd < 0:
            self.log(
                f"⏳ [ANTI CASH] Quá Min Hold Time ({time_cut_s}s) và đang âm! Cắt lỗ lệnh #{pos.ticket}",
                target="bot",
            )
            self.state["exit_reasons"][str(pos.ticket)] = "Anti_Cash_Time_Cut"
            threading.Thread(
                target=self.connector.close_position, args=(pos,), daemon=True
            ).start()

    def _check_recovery(self, pos, context):
        """[NEW V4.4] Close on Reverse (REV_C) logic"""
        # 1. Lấy signal hiện tại từ context (đã được Daemon ghi vào latest_signal)
        current_signal = context.get("latest_signal", 0)

        is_buy = pos.type == mt5.ORDER_TYPE_BUY
        is_reversed = False

        # Logic: Nếu đang BUY mà signal là -1 (SELL) hoặc ngược lại
        if is_buy and current_signal == -1:
            is_reversed = True
        elif not is_buy and current_signal == 1:
            is_reversed = True

        if is_reversed:
            # Check Min Hold Time từ config bot_safeguard
            safe_cfg = self._get_brain_settings().get("bot_safeguard", {})
            min_hold = float(safe_cfg.get("CLOSE_ON_REVERSE_MIN_TIME", 180))
            hold_time = time.time() - pos.time

            if hold_time >= min_hold:
                self.log(
                    f"🔄 [RECOVERY] Đảo chiều Signal ({'SELL' if is_buy else 'BUY'})! Đóng lệnh #{pos.ticket}",
                    target="bot",
                )
                self.state["exit_reasons"][str(pos.ticket)] = "Recovery_Close"
                threading.Thread(
                    target=self.connector.close_position, args=(pos,), daemon=True
                ).start()

    def _apply_independent_tsl(self, pos, context):
        tactic_str = self.get_trade_tactic(pos.ticket)
        if tactic_str == "OFF" or not tactic_str:
            return "TSL OFF"

        active_modes = tactic_str.split("+")
        is_buy = pos.type == mt5.ORDER_TYPE_BUY
        current_price = pos.price_current
        current_sl = pos.sl

        sym_info = mt5.symbol_info(pos.symbol)
        point = sym_info.point if sym_info else 0.00001

        one_r_dist = self.state.get("initial_r_dist", {}).get(str(pos.ticket), 0.0)
        if one_r_dist <= 0:
            if pos.sl > 0:
                one_r_dist = abs(pos.price_open - pos.sl)
            else:
                return "Thiếu R-Dist"

        curr_dist = (
            current_price - pos.price_open if is_buy else pos.price_open - current_price
        )
        curr_r = curr_dist / one_r_dist

        candidates = []
        milestones = []

        brain = self._get_brain_settings()
        tsl_cfg = brain.get("tsl_config", getattr(config, "TSL_CONFIG", {}))

        # [NEW V4.4] ONE-TIME BE: Bỏ qua BE/BE_CASH nếu SL đã được khoá an toàn
        one_time_be = tsl_cfg.get("ONE_TIME_BE", False)
        sl_better_than_entry = (is_buy and pos.sl >= pos.price_open) or (
            not is_buy and pos.sl > 0 and pos.sl <= pos.price_open
        )
        if one_time_be and sl_better_than_entry:
            if "BE" in active_modes:
                active_modes.remove("BE")
            if "BE_CASH" in active_modes:
                active_modes.remove("BE_CASH")

        # [NEW V4.4] 1. BE_HARD_CASH (Nâng cấp thành Thang cuốn cuốn chiếu Lãi Thực Tế)
        if "BE_CASH" in active_modes:
            be_type = tsl_cfg.get("BE_CASH_TYPE", "USD")  # USD, PERCENT, POINT
            be_val = float(
                tsl_cfg.get("BE_VALUE", 5.0)
            )  # Sử dụng BE_VALUE làm Bước nhảy (Step)

            profit_usd = pos.profit + pos.swap + getattr(pos, "commission", 0.0)
            acc = self.connector.get_account_info()
            bal = acc["balance"] if acc else 1000

            # Tính toán Bước nhảy (Step Value) quy đổi ra USD
            step_usd = 0
            if be_type == "USD":
                step_usd = be_val
            elif be_type == "PERCENT":
                step_usd = bal * (be_val / 100.0)
            elif be_type == "POINT":
                step_usd = be_val * point * pos.volume * sym_info.trade_contract_size

            if step_usd > 0:
                # Tính tổng phí hao hụt (Commission + Spread) để cắt hòa vốn không bị âm
                total_fee = abs(getattr(pos, "commission", 0.0)) + (
                    sym_info.spread * point * pos.volume * sym_info.trade_contract_size
                )

                # Tính xem lợi nhuận gộp (Profit) hiện tại đã đạt được bao nhiêu "Bậc thang"
                steps_achieved = math.floor(profit_usd / step_usd)

                if steps_achieved >= 1:
                    # Bậc 1: Khóa $0. Bậc 2: Khóa $5. Bậc n: Khóa (n-1)*Step
                    locked_profit_usd = (steps_achieved - 1) * step_usd

                    # Quy đổi lợi nhuận USD muốn khóa ra khoảng cách giá (Price Distance)
                    lock_dist_price = locked_profit_usd / (
                        pos.volume * sym_info.trade_contract_size
                    )

                    # Mốc hòa vốn cơ sở (Đã cộng phí)
                    breakeven_dist = total_fee / (
                        pos.volume * sym_info.trade_contract_size
                    )

                    if is_buy:
                        base_be_price = pos.price_open + breakeven_dist
                        lock_price = base_be_price + lock_dist_price
                    else:
                        base_be_price = pos.price_open - breakeven_dist
                        lock_price = base_be_price - lock_dist_price

                    candidates.append((lock_price, f"CASH Bậc {steps_achieved}"))

                # Tính Milestone hiển thị lên UI để chờ bậc tiếp theo
                next_step = steps_achieved + 1
                next_target_usd = next_step * step_usd
                milestones.append(
                    (
                        next_target_usd - profit_usd,
                        f"BE_CASH Đợi Bậc {next_step} (${next_target_usd:.2f})",
                    )
                )

        # [NEW V4.4] 2. PSAR TRAILING
        if "PSAR_TRAIL" in active_modes and context:
            trail_group = tsl_cfg.get("PSAR_GROUP", "G2")
            if "DYNAMIC" in trail_group:
                market_mode = context.get("market_mode", "ANY")
                trail_group = "G1" if market_mode in ["TREND", "BREAKOUT"] else "G2"

            psar_val = context.get(f"psar_{trail_group}", context.get("psar"))
            if psar_val:
                candidates.append((psar_val, f"PSAR ➔ {psar_val:.2f}"))
                milestones.append((0, f"PSAR Đợi ➔ {psar_val:.2f}"))

        if "BE" in active_modes:
            trig_r = tsl_cfg.get("BE_OFFSET_RR", 0.8)
            base = pos.price_open
            be_sl = (
                base + (tsl_cfg.get("BE_OFFSET_POINTS", 0) * point)
                if is_buy
                else base - (tsl_cfg.get("BE_OFFSET_POINTS", 0) * point)
            )
            trig_p = (
                base + (trig_r * one_r_dist) if is_buy else base - (trig_r * one_r_dist)
            )

            if curr_r >= trig_r:
                candidates.append((be_sl, "BE"))
            else:
                milestones.append(
                    (abs(curr_r - trig_r), f"BE Đợi {trig_p:.2f} ➔ {be_sl:.2f}")
                )

        if "STEP_R" in active_modes:
            sz, rt = tsl_cfg.get("STEP_R_SIZE", 1.0), tsl_cfg.get("STEP_R_RATIO", 0.8)
            steps = math.floor(curr_r / sz)

            if steps >= 1:
                step_sl = (
                    pos.price_open + (steps * one_r_dist * rt)
                    if is_buy
                    else pos.price_open - (steps * one_r_dist * rt)
                )
                candidates.append((step_sl, f"STEP {steps}"))

            next_step = steps + 1
            next_trig_p = (
                pos.price_open + (next_step * sz * one_r_dist)
                if is_buy
                else pos.price_open - (next_step * sz * one_r_dist)
            )
            next_sl = (
                pos.price_open + (next_step * sz * one_r_dist * rt)
                if is_buy
                else pos.price_open - (next_step * sz * one_r_dist * rt)
            )
            milestones.append(
                (
                    abs(curr_r - next_step * sz),
                    f"Step {next_step} Đợi {next_trig_p:.2f} ➔ {next_sl:.2f}",
                )
            )

        if "PNL" in active_modes:
            acc = self.connector.get_account_info()
            if acc:
                profit_usd = pos.profit + pos.swap + getattr(pos, "commission", 0.0)
                pnl_pct = (profit_usd / acc["balance"]) * 100
                levels = sorted(tsl_cfg.get("PNL_LEVELS", []), key=lambda x: x[0])

                for lvl in levels:
                    req_profit_usd = acc["balance"] * (lvl[0] / 100.0)
                    lock_dist = (acc["balance"] * (lvl[1] / 100.0)) / (
                        pos.volume * sym_info.trade_contract_size
                    )
                    pnl_sl = (
                        pos.price_open + lock_dist
                        if is_buy
                        else pos.price_open - lock_dist
                    )
                    trig_p = (
                        pos.price_open
                        + (req_profit_usd / (pos.volume * sym_info.trade_contract_size))
                        if is_buy
                        else pos.price_open
                        - (req_profit_usd / (pos.volume * sym_info.trade_contract_size))
                    )

                    if pnl_pct >= lvl[0]:
                        candidates.append((pnl_sl, f"PNL {lvl[1]}%"))
                    else:
                        milestones.append(
                            (
                                abs(pnl_pct - lvl[0]),
                                f"PnL {lvl[0]}% Đợi {trig_p:.2f} ➔ {pnl_sl:.2f}",
                            )
                        )
                        break

        if "SWING" in active_modes and context:
            trail_group = tsl_cfg.get("SWING_GROUP", "G2")
            market_mode = context.get("market_mode", "ANY")
            is_trending = market_mode in ["TREND", "BREAKOUT"]
            if "DYNAMIC" in trail_group:
                trail_group = "G1" if is_trending else "G2"

            sh = context.get(f"swing_high_{trail_group}")
            sl = context.get(f"swing_low_{trail_group}")
            atr = context.get(f"atr_{trail_group}", 0)

            if sh is not None and sl is not None and atr:
                trail_buf = getattr(config, "trail_atr_buffer", 0.2)
                tsl_mode = tsl_cfg.get("TSL_LOGIC_MODE", "STATIC")
                is_trending = context.get("market_mode", "TREND") in [
                    "TREND",
                    "BREAKOUT",
                ]

                swing_sl = 0.0
                if is_buy:
                    if tsl_mode == "STATIC":
                        swing_sl = sl - (trail_buf * atr)
                    elif tsl_mode == "AGGRESSIVE":
                        swing_sl = sh - (trail_buf * atr)
                    elif tsl_mode == "DYNAMIC":
                        swing_sl = (
                            sl - (trail_buf * atr)
                            if is_trending
                            else sh - (trail_buf * atr)
                        )
                else:
                    if tsl_mode == "STATIC":
                        swing_sl = sh + (trail_buf * atr)
                    elif tsl_mode == "AGGRESSIVE":
                        swing_sl = sl + (trail_buf * atr)
                    elif tsl_mode == "DYNAMIC":
                        swing_sl = (
                            sh + (trail_buf * atr)
                            if is_trending
                            else sl + (trail_buf * atr)
                        )

                candidates.append((swing_sl, f"SWING ➔ {swing_sl:.2f}"))
                milestones.append((0, f"SWING Đợi ➔ {swing_sl:.2f}"))

        valid_moves = []
        min_stop_dist = getattr(sym_info, "trade_stops_level", 0) * point
        for price, rule in candidates:
            if not price:
                continue
            price = round(price / point) * point
            if is_buy:
                if (
                    price > current_sl + (point / 2)
                    and price <= current_price - min_stop_dist
                ):
                    valid_moves.append((price, rule))
            else:
                if (
                    current_sl == 0 or price < current_sl - (point / 2)
                ) and price >= current_price + min_stop_dist:
                    valid_moves.append((price, rule))

        if valid_moves:
            target_sl, action_rule = (
                max(valid_moves, key=lambda x: x[0])
                if is_buy
                else min(valid_moves, key=lambda x: x[0])
            )
            if abs(target_sl - current_sl) > (point / 2):
                self.connector.modify_position(pos.ticket, target_sl, pos.tp)
                self.state["exit_reasons"][str(pos.ticket)] = (
                    f"Hit_TSL_{action_rule}"  # Track TSL hit
                )
                return f"{action_rule} Đã kéo ➔ {target_sl:.2f}"

        if milestones:
            return sorted(milestones, key=lambda x: x[0])[0][1]

        return "Tracking..."
