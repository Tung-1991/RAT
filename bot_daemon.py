# -*- coding: utf-8 -*-
# FILE: bot_daemon.py
# V3.0 PATCH: TÍCH HỢP DATA ENGINE & VOTING ENGINE THEO KIẾN TRÚC MỚI
# CẬP NHẬT: THÊM CƠ CHẾ HOT-RELOAD CHO STRATEGY SANDBOX (FILE WATCHER)

import os
import time
import threading
import traceback
import pandas as pd
from datetime import datetime
import config
import MetaTrader5 as mt5  # Thêm import mt5 nếu ngài đang gọi mt5.TIMEFRAME_H1 ở dưới
from core.storage_manager import load_state, save_state
from core.checklist_manager import ChecklistManager
# [V3.0] Import Module Mới
from core.data_engine import DataEngine
from signals.signal_generator import SignalGenerator

class BotDaemon:
    def __init__(self, connector, trade_manager, log_callback=None):
        self.connector = connector
        self.trade_manager = trade_manager
        self.log_callback = log_callback
        self.running = False
        self.thread = None
        
        self.checklist = ChecklistManager(connector, None)
        # [V3.0] Khởi tạo Data Engine & Signal Generator (Wrapper)
        self.data_engine = DataEngine(connector)
        self.signal_generator = SignalGenerator()

        self.last_signal_time = {}
        
        # [V3.0] Biến phục vụ Hot-Reload Sandbox
        self.last_sandbox_mtime = 0 
        self.sandbox_file_path = "data/sandbox_rules.json" # Đảm bảo tên file này khớp với file UI Sandbox lưu

    def log(self, msg, error=False):
        if self.log_callback:
            self.log_callback(msg, error=error)
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] {'❌' if error else '✅'} {msg}")

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            self.log("▶️ Khởi động Bot Daemon V3.0...", error=False)

    def stop(self):
        if self.running:
            self.running = False
            if self.thread:
                self.thread.join(timeout=2.0)
            self.log("⏹️ Đã dừng Bot Daemon.", error=False)

    def _run_loop(self):
        while self.running:
            try:
                # =========================================================
                # [V3.0] CƠ CHẾ HOT-RELOAD CHIẾN THUẬT THEO THỜI GIAN THỰC
                # =========================================================
                if os.path.exists(self.sandbox_file_path):
                    current_mtime = os.path.getmtime(self.sandbox_file_path)
                    if current_mtime > self.last_sandbox_mtime:
                        if self.last_sandbox_mtime != 0: # Bỏ qua lần nạp đầu tiên lúc mới bật bot
                            self.log("🔄 Phát hiện cấu hình Sandbox mới. Đang nạp lại (Hot-Reload)...")
                            if hasattr(self.signal_generator, 'reload_config'):
                                self.signal_generator.reload_config()
                                self.log("✅ Nạp chiến thuật mới thành công. Không cần khởi động lại Bot!")
                        self.last_sandbox_mtime = current_mtime
                # =========================================================

                state = load_state()
                now = datetime.now()
                
                if getattr(config, "RESET_DAILY_LOSS", True) and state.get("last_reset_day") != now.day:
                    state["daily_loss_count"] = 0
                    state["trades_today_count"] = 0
                    state["pnl_today"] = 0.0
                    state["daily_history"] = []
                    state["last_reset_day"] = now.day
                    save_state(state)

                if getattr(config, "CHECK_NEWS_IMPACT", True):
                    self.checklist.update_forex_factory_news()

                # --- 1. UPDATE QUẢN LÝ LỆNH ĐANG CHẠY (GIỮ NGUYÊN LOGIC CŨ) ---
                symbol = getattr(config, "UI_ACTIVE_SYMBOL", getattr(config, "SYMBOL", "XAUUSDm"))
                acc_info = self.connector.get_account_info()
                
                # Để hỗ trợ Trailing Stop SWING, cần context của Symbol hiện tại
                market_context = {}
                df_h1_tsl = self.connector.get_historical_data(symbol, mt5.TIMEFRAME_H1, getattr(config, "NUM_H1_BARS", 70))
                if df_h1_tsl is not None and not df_h1_tsl.empty:
                    # Tận dụng DataEngine để lấy context (swing_h, swing_l, atr, trend)
                    market_context[symbol] = self.data_engine._build_context(df_h1_tsl, config.__dict__)
                
                tsl_status = self.trade_manager.update_running_trades(
                    account_type="STANDARD", 
                    all_market_contexts=market_context
                )
                
                if tsl_status:
                    self.log(f"🔄 TSL Update: {tsl_status}")

                # --- 2. LOGIC QUÉT TÍN HIỆU VÀO LỆNH (V3.0) ---
                if not getattr(config, "AUTO_TRADE_ENABLED", False):
                    time.sleep(getattr(config, "DAEMON_LOOP_DELAY", 15))
                    continue

                if acc_info is None:
                    time.sleep(getattr(config, "DAEMON_LOOP_DELAY", 15))
                    continue

                check_res = self.checklist.run_pre_trade_checks(acc_info, state, symbol, strict_mode=True)
                if not check_res["passed"]:
                    time.sleep(getattr(config, "DAEMON_LOOP_DELAY", 15))
                    continue

                # LẤY DATA & TẠO PAYLOAD QUA DATA ENGINE (V3.0)
                # Dùng config.__dict__ để lấy fallback params nếu cần
                data_package = self.data_engine.fetch_and_prepare(symbol, config.__dict__)
                
                if not data_package:
                    time.sleep(getattr(config, "DAEMON_LOOP_DELAY", 15))
                    continue

                # ĐẨY VÀO SIGNAL GENERATOR (WRAPPER V3.0)
                signal_val, details = self.signal_generator.generate_signal(data_package)

                # KIỂM TRA ĐIỀU KIỆN VÀO LỆNH
                current_bar_time = data_package["raw_trigger"].iloc[-1].name if 'raw_trigger' in data_package and not data_package["raw_trigger"].empty else 0
                
                # Tránh nhồi lệnh trên cùng 1 nến
                if self.last_signal_time.get(symbol) != current_bar_time:
                    if signal_val == 1:
                        self.log(f"🎯 [V3.0] Tín hiệu MUA từ Sandbox (Mode: {details.get('mode')})")
                        self._place_trade("BUY", symbol, details)
                        self.last_signal_time[symbol] = current_bar_time
                        
                    elif signal_val == -1:
                        self.log(f"🎯 [V3.0] Tín hiệu BÁN từ Sandbox (Mode: {details.get('mode')})")
                        self._place_trade("SELL", symbol, details)
                        self.last_signal_time[symbol] = current_bar_time

            except Exception as e:
                self.log(f"🔥 Lỗi Daemon Loop: {e}\n{traceback.format_exc()}", error=True)
            
            time.sleep(getattr(config, "DAEMON_LOOP_DELAY", 15))

    def _place_trade(self, direction, symbol, details):
        """ Hàm gọi sang Trade Manager (V3.0) """
        preset_name = getattr(config, "BOT_PRESET", "SCALPING")
        preset = getattr(config, "PRESETS", {}).get(preset_name, {})
        
        bot_risk = preset.get("RISK_PERCENT", getattr(config, "RISK_PER_TRADE_PERCENT", 1.0))
        bot_tsl = getattr(config, "BOT_TSL_MODE", "OFF")
        
        # Trong V3.0, SL/TP tĩnh không còn quan trọng, Trade Manager sẽ ghi đè bằng details
        dummy_sl = 0.0
        dummy_tp = 0.0

        res = self.trade_manager.execute_bot_trade(
            direction=direction,
            symbol=symbol,
            sl_price=dummy_sl,
            tp_price=dummy_tp,
            bot_risk_percent=bot_risk,
            tactic_str=bot_tsl,
            details=details
        )
        
        if "SUCCESS" in res:
            self.log(f"🤖 Bot đã vào lệnh {direction} thành công! (TSL: {bot_tsl})")
        else:
            self.log(f"⚠️ Bot thất bại khi vào lệnh {direction}: {res}", error=True)