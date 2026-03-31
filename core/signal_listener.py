# -*- coding: utf-8 -*-
# FILE: core/signal_listener.py
# V5.3: FINAL REFACTOR - PERFECT SYNC WITH BOT_TRADE_MANAGER

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
        - trade_manager: Bộ máy thực thi lệnh.
        - get_auto_trade_cb: Trạng thái nút gạt Auto-Trade trên UI.
        - get_preset_cb: Preset đang chọn trên UI (Dùng làm nhãn, không dùng chia lot cho bot).
        - get_tsl_mode_cb: TSL Mode đang bật trên UI.
        """
        self.trade_manager = trade_manager
        
        self.get_auto_trade = get_auto_trade_cb
        self.get_preset = get_preset_cb
        self.get_tsl_mode = get_tsl_mode_cb
        self.update_ui_heartbeat = ui_heartbeat_cb
        self.log_ui = log_cb
        
        self.running = False
        self.thread = None
        
        # Lưu UUID các tín hiệu đã xử lý để tránh lặp lệnh (Idempotency)
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
                    time.sleep(1)
                    continue

                # Đọc tín hiệu từ file JSON do bot_daemon ghi ra
                with open(SIGNAL_FILE, "r", encoding="utf-8") as f:
                    try:
                        payload = json.load(f)
                    except json.JSONDecodeError:
                        # Tránh lỗi khi Daemon đang ghi file dở (Atomic write)
                        time.sleep(0.5)
                        continue

                # 1. Cập nhật Heartbeat (Dữ liệu thị trường, trạng thái Daemon) lên UI
                heartbeat = payload.get("brain_heartbeat", {})
                if heartbeat:
                    self.update_ui_heartbeat(heartbeat)

                # 2. Quét danh sách tín hiệu chờ (Pending Signals)
                pending_signals = payload.get("pending_signals", [])
                for sig in pending_signals:
                    sig_id = sig.get("signal_id")
                    
                    if not sig_id or sig_id in self.processed_signals:
                        continue
                    
                    self.processed_signals.add(sig_id)

                    # Kiểm tra thời hạn hiệu lực của tín hiệu (TTL)
                    sig_time = sig.get("timestamp", 0)
                    valid_for = sig.get("valid_for", 300)
                    if time.time() - sig_time > valid_for:
                        self.log_ui(f"⚠️ Bỏ qua tín hiệu {sig.get('action')} {sig.get('symbol')}: Đã hết hạn (EXPIRED).", error=True)
                        continue

                    # Xử lý thực thi lệnh
                    self._process_signal(sig)

            except Exception as e:
                logger.error(f"[Listener] Lỗi vòng lặp: {e}")
            
            time.sleep(1)

    def _process_signal(self, signal: dict):
        """Xử lý thực thi khi có tín hiệu hợp lệ"""
        action = signal.get("action")
        symbol = signal.get("symbol")
        sl_price = float(signal.get("sl_price", 0.0))
        sig_class = signal.get("signal_class", "ENTRY")
        
        # [V5.3 MỚI] - Đọc rủi ro và TP (luôn = 0.0) từ JSON do Daemon gửi
        bot_risk = float(signal.get("bot_risk_percent", 0.3))
        tp_price = float(signal.get("tp_price", 0.0))

        self.log_ui(f"🧠 [BRAIN] Phát hiện lệnh {sig_class} {action} {symbol} | SL: {sl_price:.5f}", error=False)

        # Kiểm tra công tắc Auto-Trade trên giao diện
        if not self.get_auto_trade():
            self.log_ui(f"⏸️ Chế độ AUTO đang TẮT. Chỉ hiển thị cảnh báo.", error=True)
            return

        # Lấy chiến thuật TSL từ giao diện
        current_ui_tsl = self.get_tsl_mode()
        
        self.log_ui(f"🤖 Bot chuẩn bị bóp cò! Risk: {bot_risk}% | TP: Không cài (Ăn TSL)...", error=False)
        
        # [V5.3 QUAN TRỌNG] Chạy luồng riêng gọi ĐÚNG hàm execute_bot_trade
        def run_bot_trade():
            result = self.trade_manager.execute_bot_trade(
                direction=action,
                symbol=symbol,
                sl_price=sl_price,
                tp_price=tp_price,
                bot_risk_percent=bot_risk,
                tactic_str=current_ui_tsl
            )
            
            if "SUCCESS" in result:
                # Log thành công đã được in bên trong TradeManager
                pass
            else:
                self.log_ui(f"❌ Bot vào lệnh thất bại: {result}", error=True)

        # Chạy ẩn bằng Thread để không làm đơ vòng lặp lắng nghe tín hiệu
        threading.Thread(target=run_bot_trade, daemon=True).start()