# -*- coding: utf-8 -*-
# FILE: bot_daemon.py
# V3.0: UNIFIED BOT DAEMON - HOT RELOAD & PIPELINE (KAISER EDITION)

import time
import threading
import logging
import os
from datetime import datetime
import config
from core.data_engine import DataEngine
from signals.signal_generator import SignalGenerator

logger = logging.getLogger("ExnessBot")

class BotDaemon:
    def __init__(self, connector, trade_mgr, checklist_mgr, log_callback=None):
        self.connector = connector
        self.trade_mgr = trade_mgr
        self.checklist_mgr = checklist_mgr
        self.log_callback = log_callback
        
        self.data_engine = DataEngine(connector)
        self.signal_gen = SignalGenerator()
        
        self.running = False
        self.thread = None
        self.last_config_mtime = 0
        self.brain_file_path = "data/brain_settings.json"

    def log(self, msg, error=False):
        if self.log_callback:
            self.log_callback(f"[DAEMON] {msg}", error=error)
        else:
            logger.info(f"[DAEMON] {msg}")

    def _check_hot_reload(self):
        """Giám sát sự thay đổi của file cấu hình Sandbox để Hot-Reload"""
        try:
            if os.path.exists(self.brain_file_path):
                current_mtime = os.path.getmtime(self.brain_file_path)
                if current_mtime > self.last_config_mtime:
                    if self.last_config_mtime != 0:
                        self.log("Phát hiện thay đổi cấu hình. Đang tiến hành Hot-Reload...")
                    self.signal_gen.reload_config()
                    self.last_config_mtime = current_mtime
        except Exception as e:
            logger.error(f"[Watchdog] Lỗi Hot-Reload: {e}")

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            self.log("Đã khởi động tiến trình ngầm (Bot Daemon).")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.log("Đã dừng tiến trình ngầm.")

    def _run_loop(self):
        while self.running:
            try:
                # 1. Kiểm tra Hot-Reload
                self._check_hot_reload()

                # 2. Kiểm tra cờ cho phép Auto Trade
                if getattr(config, "AUTO_TRADE_ENABLED", False):
                    self._process_trading_cycle()

            except Exception as e:
                logger.error(f"Lỗi trong vòng lặp Daemon: {e}")
            
            # Nghỉ ngơi giữa các chu kỳ để tránh spam API
            time.sleep(getattr(config, "DAEMON_LOOP_DELAY", 15))

    def _process_trading_cycle(self):
        """Chu kỳ quét và vào lệnh của Bot"""
        
        # 1. Kiểm tra giới hạn số lệnh của Bot trong ngày
        limit = getattr(config, "BOT_DAILY_TRADE_LIMIT", 10)
        bot_trades_today = self._count_bot_trades_today()
        
        if bot_trades_today >= limit:
            return # Đã chạm ngưỡng, im lặng đợi ngày hôm sau

        # Lấy danh sách cặp tiền Bot được phép giao dịch
        active_symbols = getattr(config, "BOT_ACTIVE_SYMBOLS", [])
        
        for symbol in active_symbols:
            if not self.running: break
            
            # Tránh vào lệnh liên tục (Cooldown)
            if self._is_cooling_down(symbol):
                continue

            # 2. Bơm Dữ Liệu (Data Pipeline)
            brain_config = self.signal_gen.config
            data_package = self.data_engine.fetch_and_prepare(symbol, brain_config)
            
            if not data_package or "context" not in data_package:
                continue

            # 3. Phân Tích Tín Hiệu (Signal & Voting)
            final_signal, details = self.signal_gen.generate_signal(data_package)

            # 4. Thực Thi Lệnh
            if final_signal != 0:
                direction = "BUY" if final_signal == 1 else "SELL"
                
                # Tham số lệnh cho Bot
                bot_risk = getattr(config, "BOT_RISK_PERCENT", 0.3)
                bot_tsl = getattr(config, "BOT_DEFAULT_TSL", "BE+STEP_R+SWING")
                
                self.log(f"⚡ Tín hiệu {direction} xác nhận trên {symbol} (Chế độ: {details.get('mode')})")
                
                # TP và SL truyền vào là 0 vì TradeManager V3.0 sẽ tự tính dựa trên `details` (Swing + ATR)
                res = self.trade_mgr.execute_bot_trade(
                    direction=direction,
                    symbol=symbol,
                    sl_price=0.0,
                    tp_price=0.0,
                    bot_risk_percent=bot_risk,
                    tactic_str=bot_tsl,
                    details=details
                )
                
                if res == "SUCCESS":
                    self._mark_cooldown(symbol)

    def _count_bot_trades_today(self) -> int:
        """Đếm số lệnh do đích thân Bot bắn trong ngày (lọc qua Magic Number)"""
        # Đây là ước tính dựa trên tổng lệnh, vì TradeManager V3 gộp chung counter
        # Trong thực tế, có thể đếm từ daily_history hoặc list active_trades.
        # Để đơn giản và an toàn, dùng biến trades_today_count của state hiện tại.
        return self.trade_mgr.state.get("trades_today_count", 0)

    def _is_cooling_down(self, symbol: str) -> bool:
        """Kiểm tra Cooldown (chống spam nhiều lệnh cùng 1 lúc trên 1 cặp)"""
        if not hasattr(self, "_cooldown_map"):
            self._cooldown_map = {}
            
        last_time = self._cooldown_map.get(symbol, 0)
        cooldown_seconds = getattr(config, "COOLDOWN_MINUTES", 1) * 60
        
        return (time.time() - last_time) < cooldown_seconds

    def _mark_cooldown(self, symbol: str):
        if not hasattr(self, "_cooldown_map"):
            self._cooldown_map = {}
        self._cooldown_map[symbol] = time.time()