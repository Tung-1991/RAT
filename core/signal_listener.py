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
        get_preset_cb: Callable[[], str],  # [ĐÃ FIX] Thêm tham số này để không bị Crash
        get_tsl_mode_cb: Callable[
            [], str
        ],  # [ĐÃ FIX] Thêm tham số này để không bị Crash
        ui_heartbeat_cb: Callable[[dict], None],
        log_cb: Callable[[str, bool], None],
    ):
        """
        Lắng nghe và điều phối tín hiệu từ Daemon.
        """
        self.trade_manager = trade_manager
        self.get_auto_trade = get_auto_trade_cb
        self.get_preset = get_preset_cb  # [ĐÃ FIX] Khởi tạo biến
        self.get_tsl_mode = get_tsl_mode_cb  # [ĐÃ FIX] Khởi tạo biến
        self.update_ui_heartbeat = ui_heartbeat_cb
        self.log_ui = log_cb

        self.running = False
        self.thread = None

        # Lưu UUID các tín hiệu đã xử lý để tránh lặp lệnh
        self.processed_signals = set()
        self.last_thinking_signal = {}  # [NEW] Track để chống spam log

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.thread.start()
            self.log_ui(
                "📡 Signal Listener Online. Đang đợi tín hiệu từ Brain...", error=False
            )

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
                        logger.debug(
                            f"Bỏ qua tín hiệu {sig.get('action')} {sig.get('symbol')}: Đã hết hạn."
                        )
                        continue

                    # Thực thi
                    self._process_signal(sig)

            except Exception as e:
                logger.error(f"[Listener] Lỗi vòng lặp: {e}")

            time.sleep(0.5)  # Quét nhanh mỗi 0.5s để bắt nhịp DCA/PCA

    def _process_signal(self, signal: dict):
        """Xử lý định tuyến tín hiệu vào TradeManager"""
        action = signal.get("action")
        symbol = signal.get("symbol")
        sig_class = signal.get("signal_class", "ENTRY")
        context = signal.get("context", {})
        market_mode = signal.get("market_mode", "ANY")

        if not self.get_auto_trade():
            # [FIX] Thinking Logs (Chống spam)
            now = time.time()
            last_sig = self.last_thinking_signal.get(symbol, {"action": "", "time": 0})

            # Chỉ báo cáo khi đổi hướng hoặc sau mỗi 15 phút (900s)
            if last_sig["action"] != action or (now - last_sig["time"] > 900):
                self.log_ui(
                    f"📡 [SIGNAL] Phát hiện {action} {symbol}. (Chế độ: MANUAL - Bỏ qua)",
                    error=False,
                )
                self.last_thinking_signal[symbol] = {"action": action, "time": now}
            return

        # Khi AUTO đang bật, reset lại tracker để khi tắt đi nó sẽ báo ngay
        if symbol in self.last_thinking_signal:
            del self.last_thinking_signal[symbol]

        def run_bot_trade():
            # Truyền đẩy đủ Context và Signal Class sang TradeManager
            result = self.trade_manager.execute_bot_trade(
                direction=action,
                symbol=symbol,
                context=context,
                market_mode=market_mode,
                signal_class=sig_class,
            )

            if "SUCCESS" not in result:
                # [FIX] Tường minh lý do lỗi
                if "SAFEGUARD_FAIL" in result:
                    parts = result.split("|")
                    reason_key = parts[1] if len(parts) > 1 else "UNK"
                    reason_msg = parts[2] if len(parts) > 2 else "Không xác định"

                    # [NEW] Chống Spam Log: CÓ THỜI GIAN COOLDOWN ĐỘNG (Lấy từ UI)
                    track_key = f"{symbol}_{sig_class}"
                    last_key = getattr(self, "last_safeguard_reason", {}).get(
                        track_key, ""
                    )
                    last_time = getattr(self, "last_safeguard_time", {}).get(
                        track_key, 0
                    )
                    now = time.time()
                    
                    try:
                        import json as _json, os as _os
                        _cpath = "data/brain_settings.json"
                        cmin = 60.0
                        if _os.path.exists(_cpath):
                            with open(_cpath, "r", encoding="utf-8") as _cf:
                                cmin = float(_json.load(_cf).get("bot_safeguard", {}).get("LOG_COOLDOWN_MINUTES", 60.0))
                    except:
                        cmin = 60.0
                        
                    is_cooldown_expired = (now - last_time) >= (cmin * 60)

                    if reason_key != last_key or is_cooldown_expired:
                        # Chỉ in ra khi BẮT ĐẦU bị lỗi này HOẶC đã hết 30s kể từ lần in cuối
                        self.log_ui(
                            f"🤖 Bot định bóp cò {sig_class}: {action} {symbol} nhưng bị chặn!",
                            error=False,
                        )
                        self.log_ui(
                            f"⚠️ [BOT SAFEGUARD] Lý do: {reason_msg}", error=True
                        )

                        if not hasattr(self, "last_safeguard_reason"):
                            self.last_safeguard_reason = {}
                        if not hasattr(self, "last_safeguard_time"):
                            self.last_safeguard_time = {}
                            
                        self.last_safeguard_reason[track_key] = reason_key
                        self.last_safeguard_time[track_key] = now
                else:
                    self.log_ui(
                        f"🤖 Bot chuẩn bị bóp cò {sig_class}: {action} {symbol}",
                        error=False,
                    )
                    self.log_ui(f"❌ Bot vào lệnh thất bại: {result}", error=True)
            else:
                # Nếu lệnh THÀNH CÔNG, xóa bộ nhớ lỗi cũ để lần sau lỗi lại báo
                if (
                    hasattr(self, "last_safeguard_reason")
                    and symbol in self.last_safeguard_reason
                ):
                    del self.last_safeguard_reason[symbol]

        # Chạy Thread độc lập để Listener không bị kẹt
        threading.Thread(target=run_bot_trade, daemon=True).start()
