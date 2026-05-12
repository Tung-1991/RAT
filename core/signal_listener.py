# -*- coding: utf-8 -*-
# FILE: core/signal_listener.py
# V4.4 (FINAL): SIGNAL ROUTER - HANDLING ENTRY, DCA, PCA & REVERSE CLOSE (KAISER EDITION)

import json
import os
import time
import threading
import logging
from typing import Callable, Any

import config

logger = logging.getLogger("SignalListener")

def _get_signal_file():
    """Lấy đường dẫn live_signals.json động theo Account Workspace."""
    try:
        import core.storage_manager as sm
        return os.path.join(sm._active_account_dir, "live_signals.json")
    except:
        return os.path.join("data", "live_signals.json")

def _get_brain_file():
    """Lấy đường dẫn brain_settings.json động theo Account Workspace."""
    try:
        import core.storage_manager as sm
        return sm.BRAIN_FILE
    except:
        return os.path.join("data", "brain_settings.json")


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

        # [NEW V4.3.1] Trí nhớ dài hạn cho Safeguard Log
        self.last_safeguard_reason = {}
        self.last_safeguard_time = {}
        self.last_bot_log_time = {}

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
                signal_file = _get_signal_file()
                if not os.path.exists(signal_file):
                    time.sleep(0.5)
                    continue

                # Đọc file với try-except bắt lỗi JSON đang ghi dở từ Daemon
                # [FIX V4.3.2] Xử lý tranh chấp file (Permission denied) trên Windows
                try:
                    with open(signal_file, "r", encoding="utf-8") as f:
                        try:
                            payload = json.load(f)
                        except json.JSONDecodeError:
                            time.sleep(0.1)
                            continue
                except PermissionError:
                    time.sleep(0.1)  # File đang bị Daemon ghi, đợi một chút rồi thử lại
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

    def _get_log_cooldown_seconds(self) -> float:
        try:
            cpath = _get_brain_file()
            cooldown_min = float(
                getattr(config, "BOT_SAFEGUARD", {}).get("LOG_COOLDOWN_MINUTES", 60.0)
            )
            if os.path.exists(cpath):
                with open(cpath, "r", encoding="utf-8") as cf:
                    b_set = json.load(cf)
                    safe_cfg = b_set.get("bot_safeguard", {})
                    cooldown_min = float(
                        safe_cfg.get(
                            "LOG_COOLDOWN_MINUTES",
                            cooldown_min,
                        )
                    )
        except Exception:
            cooldown_min = float(
                getattr(config, "BOT_SAFEGUARD", {}).get("LOG_COOLDOWN_MINUTES", 60.0)
            )
        return max(0.0, cooldown_min * 60.0)

    def _should_log_bot_status(self, key: str) -> bool:
        now = time.time()
        last_log = self.last_bot_log_time.get(key, 0)
        if now - last_log < self._get_log_cooldown_seconds():
            return False

        self.last_bot_log_time[key] = now
        return True

    def _process_signal(self, signal: dict):
        """Xử lý định tuyến tín hiệu vào TradeManager"""
        action = signal.get("action")
        symbol = signal.get("symbol")
        sig_class = signal.get("signal_class", "ENTRY")
        context = signal.get("context", {})
        market_mode = signal.get("market_mode", "ANY")

        # [NEW V4.4 FINAL] LƯỚI LỌC 0: TỰ ĐỘNG CẮT LỆNH ĐẢO CHIỀU (CLOSE ON REVERSE)
        # Chạy độc lập với AUTO-TRADE. Bất cứ lệnh nào đang ôm tactic REVERSE_CLOSE
        # đều sẽ bị chém ngay lập tức khi có tín hiệu ngược (bảo vệ tài khoản).
        try:
            # REV_C close ownership lives in TradeManager._check_recovery().
            positions = []
            opposite_type = 1 if action == "BUY" else 0  # 1 = SELL, 0 = BUY

            for p in positions:
                b_set = {}
                try:
                    from core.storage_manager import get_brain_settings_for_symbol
                    b_set = get_brain_settings_for_symbol(symbol)
                except Exception:
                    pass

                allow_none_close = b_set.get("bot_safeguard", {}).get("REV_CLOSE_ON_NONE", False)
                is_reverse_match = (
                    action == "NONE" and allow_none_close
                ) or (
                    action != "NONE" and p.type == opposite_type
                )

                if p.symbol == symbol and is_reverse_match:
                    tactic = self.trade_manager.get_trade_tactic(p.ticket)
                    if "REV_C" in tactic or "REVERSE_CLOSE" in tactic:
                        hold_time = time.time() - p.time

                        # Đọc thông số chống nhiễu (Min Hold Time + Min PnL)
                        min_hold = 180.0
                        try:
                            min_hold = float(b_set.get("bot_safeguard", {}).get("CLOSE_ON_REVERSE_MIN_TIME", 180))
                        except Exception:
                            pass

                        profit_usd = p.profit + p.swap + getattr(p, "commission", 0.0)

                        # [NEW V4.4] REFINED PNL CHECK
                        pnl_ok = True
                        safe_cfg = b_set.get("bot_safeguard", {})
                        if safe_cfg.get("CLOSE_ON_REVERSE_USE_PNL", True):
                            equity = 0.0
                            try:
                                acc = self.trade_manager.connector.get_account_info()
                                equity = acc.get("equity", 0.0) if acc else 0.0
                            except Exception:
                                pass
                            min_profit = self.trade_manager._resolve_money_value(
                                safe_cfg.get("REV_CLOSE_MIN_PROFIT", 0.0),
                                safe_cfg.get("REV_CLOSE_MIN_PROFIT_UNIT", "USD"),
                                pos=p,
                                equity=equity,
                            )
                            max_loss = -abs(
                                self.trade_manager._resolve_money_value(
                                    safe_cfg.get("REV_CLOSE_MAX_LOSS", 0.0),
                                    safe_cfg.get("REV_CLOSE_MAX_LOSS_UNIT", "USD"),
                                    pos=p,
                                    equity=equity,
                                )
                            )

                            if profit_usd >= 0:
                                # [REFINED] Nếu đang lãi, kiểm tra lợi nhuận tối thiểu để cắt (Tránh phí)
                                pnl_ok = (profit_usd >= min_profit) if min_profit > 0 else True
                            else:
                                # [REFINED] Nếu đang lỗ, chỉ cắt nếu lỗ chưa vượt quá giới hạn (Chống cắt đáy)
                                # Ví dụ: -5 >= -10 là True (Cắt), -15 >= -10 là False (Giữ)
                                # Current behavior: -15 > -20 -> hold, -20 <= -20 -> close.
                                pnl_ok = (profit_usd <= max_loss) if max_loss != 0 else True

                        if hold_time >= min_hold and pnl_ok:
                            self.log_ui(
                                f"  [REVERSE TACTIC] Đảo chiều {action} | PnL: ${profit_usd:.2f} -> Đóng lệnh #{p.ticket}",
                                False,
                            )

                            # Lưu lý do thoát lệnh để ghi log CSV
                            if "exit_reasons" not in self.trade_manager.state:
                                self.trade_manager.state["exit_reasons"] = {}
                            self.trade_manager.state["exit_reasons"][str(p.ticket)] = (
                                f"Reverse_to_{action}"
                            )

                            threading.Thread(
                                target=self.trade_manager.connector.close_position,
                                args=(p,),
                                daemon=True,
                            ).start()
                        else:
                            reason = "HoldTime" if hold_time < min_hold else "PnL_Filter"
                            if self._should_log_bot_status(
                                f"reverse_hold_{symbol}_{p.ticket}_{reason}"
                            ):
                                self.log_ui(
                                    f"⏳ [REVERSE TACTIC] Tín hiệu {action} nhưng giữ lệnh #{p.ticket} ({reason} | PnL: ${profit_usd:.2f})",
                                    False,
                                )
        except Exception as e:
            logger.error(f"[Listener] Lỗi Reverse Check: {e}")

        if action == "NONE":
            return

        if not self.get_auto_trade():
            try:
                cpath = _get_brain_file()
                manual_log_enable = getattr(config, "BOT_SAFEGUARD", {}).get(
                    "MANUAL_SIGNAL_LOG_ENABLE", False
                )
                manual_log_cooldown = float(
                    getattr(config, "BOT_SAFEGUARD", {}).get(
                        "LOG_COOLDOWN_MINUTES", 60.0
                    )
                )
                if os.path.exists(cpath):
                    with open(cpath, "r", encoding="utf-8") as cf:
                        b_set = json.load(cf)
                        safe_cfg = b_set.get("bot_safeguard", {})
                        manual_log_enable = safe_cfg.get(
                            "MANUAL_SIGNAL_LOG_ENABLE", manual_log_enable
                        )
                        manual_log_cooldown = float(
                            safe_cfg.get(
                                "LOG_COOLDOWN_MINUTES",
                                manual_log_cooldown,
                            )
                        )
            except Exception:
                manual_log_enable = False
                manual_log_cooldown = 60.0

            if not manual_log_enable:
                return

            # [FIX] Thinking Logs (Chống spam)
            now = time.time()
            last_sig = self.last_thinking_signal.get(symbol, {"action": "", "time": 0})

            cooldown_s = max(0.0, manual_log_cooldown * 60.0)
            if last_sig["action"] != action or (now - last_sig["time"] > cooldown_s):
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
            auto_log_enabled = self._should_log_bot_status(
                f"signal_seen_{symbol}_{sig_class}_{action}"
            )
            if auto_log_enabled:
                self.log_ui(
                    f"📡 [SIGNAL] Bot nhận {sig_class}: {action} {symbol}. Đang kiểm tra safeguard...",
                    error=False,
                )
            # Truyền đẩy đủ Context và Signal Class sang TradeManager
            result = self.trade_manager.execute_bot_trade(
                direction=action,
                symbol=symbol,
                context=context,
                market_mode=market_mode,
                signal_class=sig_class,
                tactic_override=None,  # [FIX] Bot phải tự đọc bot_tsl từ Sandbox, KHÔNG dùng Panel TSL
            )

            if "SUCCESS" not in result:
                # [FIX] Tường minh lý do lỗi
                if "SAFEGUARD_FAIL" in result:
                    parts = result.split("|")
                    reason_key = parts[1] if len(parts) > 1 else "UNK"
                    reason_msg = parts[2] if len(parts) > 2 else "Không xác định"

                    # [NEW] Chống Spam Log: CÓ THỜI GIAN COOLDOWN ĐỘNG (Lấy từ UI)
                    track_key = f"{symbol}_{sig_class}"

                    last_key = self.last_safeguard_reason.get(track_key, "")
                    last_time = self.last_safeguard_time.get(track_key, 0)
                    now = time.time()

                    is_cooldown_expired = (
                        now - last_time
                    ) >= self._get_log_cooldown_seconds()

                    # [KAISER FIX] Tránh edgecase khi reason flap (VD: Ping,MaxOrders -> MaxOrders) làm bypass cooldown
                    # Chúng ta sẽ block theo track_key (Symbol + Class). Chỉ báo log mới nếu HẾT COOLDOWN.
                    if is_cooldown_expired:
                        self.log_ui(
                            f"🤖 Bot định bóp cò {sig_class}: {action} {symbol} nhưng bị chặn!",
                            error=False,
                        )
                        self.log_ui(
                            f"⚠️ [BOT SAFEGUARD] Lý do: {reason_msg}", error=True
                        )

                        self.last_safeguard_reason[track_key] = reason_key
                        self.last_safeguard_time[track_key] = now
                else:
                    fail_key = f"bot_trade_fail_{symbol}_{sig_class}_{result}"
                    if self._should_log_bot_status(fail_key):
                        self.log_ui(
                            f"🤖 Bot chuẩn bị bóp cò {sig_class}: {action} {symbol}",
                            error=False,
                        )
                        self.log_ui(f"❌ Bot vào lệnh thất bại: {result}", error=True)
            else:
                # [V4.3.1] Không xóa bộ nhớ lỗi khi thành công nữa để giữ vững Cooldown Log
                pass

        # Chạy Thread độc lập để Listener không bị kẹt
        threading.Thread(target=run_bot_trade, daemon=True).start()
