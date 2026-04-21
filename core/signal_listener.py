# -*- coding: utf-8 -*-
# FILE: core/signal_listener.py
# V3.1: SIGNAL ROUTER - HANDLING ENTRY, DCA, PCA (KAISER EDITION)

import json
import os
import time
import threading
import logging
from typing import Callable, Any

import config

logger = logging.getLogger("SignalListener")
SIGNAL_FILE = os.path.join(getattr(config, "DATA_DIR", "data"), "live_signals.json")

class SignalListener:
    def __init__(
        self, 
        trade_manager: Any, 
        get_auto_trade_cb: Callable[[], bool],
        ui_heartbeat_cb: Callable[[dict], None],
        log_cb: Callable[[str, bool], None]
    ):
        """
        Lắng nghe và điều phối tín hiệu từ Daemon.
        """
        self.trade_manager = trade_manager
        self.get_auto_trade = get_auto_trade_cb
        self.update_ui_heartbeat = ui_heartbeat_cb
        self.log_ui = log_cb
        
        self.running = False
        self.thread = None
        
        # Lưu UUID các tín hiệu đã xử lý để tránh lặp lệnh
        self.processed_signals = set()

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            self.log_ui("📡 Signal Listener Online. Đang đợi tín hiệu từ Brain...", error=False)

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _listen_loop(self):
        while self.running:
            try:
                if not os.path.exists(SIGNAL_FILE):
                    time.sleep(0.5)
                    continue

                # Đọc file với try-except bắt lỗi JSON đang ghi dở từ Daemon
                with open(SIGNAL_FILE, "r", encoding="utf-8") as f:
                    try:
                        payload = json.load(f)
                    except json.JSONDecodeError:
                        time.sleep(0.1)
                        continue

                # 1. Cập nhật Heartbeat (Sync Context) lên UI
                heartbeat = payload.get("brain_heartbeat", {})
                if heartbeat:
                    self.update_ui_heartbeat(heartbeat)

                # 2. Quét tín hiệu chờ (Signals)
                pending_signals = payload.get("pending_signals", [])
                for sig in pending_signals:
                    sig_id = sig.get("signal_id")
                    
                    if not sig_id or sig_id in self.processed_signals:
                        continue
                    
                    self.processed_signals.add(sig_id)

                    # Kiểm tra TTL (Tránh đánh lệnh cũ nếu Bot UI vừa bật lên)
                    sig_time = sig.get("timestamp", 0)
                    valid_for = sig.get("valid_for", 300)
                    if time.time() - sig_time > valid_for:
                        self.log_ui(f"⚠️ Bỏ qua tín hiệu {sig.get('action')} {sig.get('symbol')}: Đã hết hạn.", error=True)
                        continue

                    # Thực thi
                    self._process_signal(sig)

            except Exception as e:
                logger.error(f"[Listener] Lỗi vòng lặp: {e}")
            
            time.sleep(0.5) # Quét nhanh mỗi 0.5s để bắt nhịp DCA/PCA

    def _process_signal(self, signal: dict):
        """Xử lý định tuyến tín hiệu vào TradeManager"""
        action = signal.get("action")
        symbol = signal.get("symbol")
        sig_class = signal.get("signal_class", "ENTRY")
        context = signal.get("context", {})
        market_mode = signal.get("market_mode", "ANY")

        self.log_ui(f"🧠 [BRAIN] Phát hiện tín hiệu {sig_class}: {action} {symbol}", error=False)

        if not self.get_auto_trade():
            self.log_ui(f"⏸️ Chế độ AUTO đang TẮT. Bỏ qua lệnh {sig_class}.", error=True)
            return

        self.log_ui(f"🤖 Bot chuẩn bị bóp cò! Phân loại: {sig_class}", error=False)
        
        def run_bot_trade():
            # Truyền đẩy đủ Context và Signal Class sang TradeManager
            result = self.trade_manager.execute_bot_trade(
                direction=action,
                symbol=symbol,
                context=context,
                market_mode=market_mode,
                signal_class=sig_class
            )
            
            if "SUCCESS" not in result:
                self.log_ui(f"❌ Bot vào lệnh thất bại: {result}", error=True)

        # Chạy Thread độc lập để Listener không bị kẹt
        threading.Thread(target=run_bot_trade, daemon=True).start()