# -*- coding: utf-8 -*-
# FILE: core/signal_listener.py
# V4.1: Master-Worker Architecture - Signal Consumer

import json
import os
import time
import threading
import logging
from typing import Callable, Any

import config

logger = logging.getLogger("ExnessBot")
SIGNAL_FILE = os.path.join(config.DATA_DIR, "live_signals.json")

class SignalListener:
    def __init__(
        self, 
        trade_manager: Any, 
        get_auto_trade_cb: Callable[[], bool],
        get_preset_cb: Callable[[], str],
        get_tsl_mode_cb: Callable[[], str],
        ui_heartbeat_cb: Callable[[dict], None],
        log_cb: Callable[[str, bool], None]
    ):
        """
        Khởi tạo Listener đọc tín hiệu từ bot_daemon.
        - trade_manager: Tham chiếu đến bộ máy thực thi.
        - get_auto_trade_cb: Hàm lấy trạng thái Auto-Trade từ UI (True/False).
        - get_preset_cb: Hàm lấy tên Preset đang chọn trên UI.
        - get_tsl_mode_cb: Hàm lấy chuỗi TSL Mode đang bật trên UI (VD: "BE+STEP_R").
        - ui_heartbeat_cb: Hàm cập nhật UI trạng thái của Brain.
        - log_cb: Hàm in log lên UI.
        """
        self.trade_manager = trade_manager
        
        self.get_auto_trade = get_auto_trade_cb
        self.get_preset = get_preset_cb
        self.get_tsl_mode = get_tsl_mode_cb
        self.update_ui_heartbeat = ui_heartbeat_cb
        self.log_ui = log_cb
        
        self.running = False
        self.thread = None
        
        # In-Memory Tracking: Lưu UUID các tín hiệu đã xử lý để không vào lệnh 2 lần
        self.processed_signals = set()

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            self.log_ui("📡 Signal Listener Started. Đang lắng nghe bot_daemon...", error=False)

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=2)

    def _listen_loop(self):
        while self.running:
            try:
                if not os.path.exists(SIGNAL_FILE):
                    time.sleep(1)
                    continue

                # Đọc file JSON (Chỉ Đọc - Read Only)
                with open(SIGNAL_FILE, "r", encoding="utf-8") as f:
                    try:
                        payload = json.load(f)
                    except json.JSONDecodeError:
                        # Bỏ qua nếu P1 đang ghi dở file (Atomic write lỗi nhẹ)
                        time.sleep(0.5)
                        continue

                # 1. Cập nhật trạng thái Brain (Heartbeat) lên UI
                heartbeat = payload.get("brain_heartbeat", {})
                if heartbeat:
                    self.update_ui_heartbeat(heartbeat)

                # 2. Xử lý các tín hiệu mới
                pending_signals = payload.get("pending_signals", [])
                for sig in pending_signals:
                    sig_id = sig.get("signal_id")
                    
                    # Bỏ qua nếu đã xử lý
                    if not sig_id or sig_id in self.processed_signals:
                        continue
                    
                    # Ghi nhận vào RAM ngay lập tức
                    self.processed_signals.add(sig_id)

                    # Kiểm tra TTL (Hết hạn)
                    sig_time = sig.get("timestamp", 0)
                    valid_for = sig.get("valid_for", 300)
                    if time.time() - sig_time > valid_for:
                        self.log_ui(f"⚠️ Bỏ qua tín hiệu {sig.get('action')} do đã quá hạn (EXPIRED).", error=True)
                        continue

                    # Nếu hợp lệ, chuyển sang xử lý thực thi
                    self._process_signal(sig)

            except Exception as e:
                logger.error(f"[Listener] Lỗi vòng lặp: {e}")
            
            # Quét file mỗi giây
            time.sleep(1)

    def _process_signal(self, signal: dict):
        """Xử lý logic khi có 1 tín hiệu mới và còn hạn"""
        action = signal.get("action")
        symbol = signal.get("symbol")
        sl_price = float(signal.get("sl_price", 0.0))
        sig_class = signal.get("signal_class", "ENTRY")

        self.log_ui(f"🧠 [BRAIN SIGNAL] Phân tích thấy lệnh {sig_class} {action} {symbol} | SL Toán học: {sl_price:.5f}", error=False)

        # Kiểm tra trạng thái UI
        if not self.get_auto_trade():
            self.log_ui(f"⏸️ Auto-Trade đang TẮT. Chỉ cảnh báo, không vào lệnh.", error=True)
            return

        # Gọi TradeManager để vào lệnh
        preset = self.get_preset()
        tsl_mode = self.get_tsl_mode()
        
        self.log_ui(f"🤖 Auto-Trade kích hoạt! Bắn lệnh {action} {symbol} theo Preset [{preset}]...", error=False)
        
        # Tái sử dụng hàm execute_manual_trade nhưng truyền manual_sl là SL kỹ thuật từ Brain
        # Bỏ qua manual_lot, manual_tp để hệ thống tự tính dựa vào Preset Risk & RR
        result = self.trade_manager.execute_manual_trade(
            direction=action,
            preset_name=preset,
            symbol=symbol,
            strict_mode=True,      # Luôn check an toàn (Ping, Spread, Daily Loss)
            manual_lot=0.0,        # Auto tính theo Risk
            manual_sl=sl_price,    # SL ép buộc từ Brain (Toán học)
            manual_tp=0.0,         # Auto tính theo RR của Preset
            bypass_checklist=False,# Bot tự đánh thì không được bypass rủi ro
            tsl_mode=tsl_mode      # Kéo TSL mode hiện tại của UI vào lệnh
        )

        if "SUCCESS" in result:
             self.log_ui(f"✅ Bot vào lệnh tự động thành công! Ticket: {result.split('|')[1]}", error=False)
        else:
             self.log_ui(f"❌ Bot vào lệnh THẤT BẠI (Checklist/Lỗi): {result}", error=True)