# -*- coding: utf-8 -*-
# FILE: bot_daemon.py
# V4.2.1: DECOUPLED THREADS & DYNAMIC TREND COMPASS (FIXED UI SYNC) (KAISER EDITION)

import time
import json
import os
import uuid
import logging
import MetaTrader5 as mt5

import config
from core.exness_connector import ExnessConnector
from core.data_engine import data_engine
from signals.signal_generator import signal_generator
from core.logger_setup import setup_logging  # [NEW V4.3] Import hệ thống Log

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [DAEMON] %(message)s")
logger = logging.getLogger("BotDaemon")

SIGNAL_FILE = os.path.join(getattr(config, "DATA_DIR", "data"), "live_signals.json")
SIGNAL_FILE_TMP = SIGNAL_FILE + ".tmp"
BRAIN_SETTINGS_FILE = os.path.join(
    getattr(config, "DATA_DIR", "data"), "brain_settings.json"
)
DEBUG_STATE_FILE = os.path.join(
    getattr(config, "DATA_DIR", "data"), "current_signal_state.json"
)


class StandaloneBotDaemon:
    def __init__(self):
        self.running = False
        self.connector = ExnessConnector()
        if not self.connector.connect():
            logger.error("Không thể kết nối MT5. Daemon sẽ dừng.")

        self.dca_pca_interval = 2
        self.last_dca_pca_scan = 0
        self.pending_signals = []
        self.heartbeat_contexts = {}

    def _atomic_write_signals(self, active_symbols):
        payload = {
            "brain_heartbeat": {
                "status": "HEALTHY",
                "wakeup_time": time.time(),
                "active_symbols": active_symbols,
                "contexts": self.heartbeat_contexts,
            },
            "pending_signals": self.pending_signals[-10:],
        }
        os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)
        try:
            with open(SIGNAL_FILE_TMP, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
            os.replace(SIGNAL_FILE_TMP, SIGNAL_FILE)
        except Exception as e:
            logger.error(f"Lỗi ghi tín hiệu: {e}")

    def _write_signal_debugger(self, debug_state):
        try:
            os.makedirs(os.path.dirname(DEBUG_STATE_FILE), exist_ok=True)
            with open(DEBUG_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        "states": debug_state,
                    },
                    f,
                    indent=4,
                    ensure_ascii=False,
                )
        except Exception:
            pass

    def _add_signal(self, action, symbol, context, signal_class="ENTRY"):
        sig_id = str(uuid.uuid4())
        self.pending_signals.append(
            {
                "signal_id": sig_id,
                "timestamp": time.time(),
                "valid_for": 300 if signal_class == "ENTRY" else 60,
                "action": action,
                "symbol": symbol,
                "signal_class": signal_class,
                "context": context,
            }
        )
        logger.debug(f"Đã phát tín hiệu {action} cho {symbol} ({signal_class})")
        live_cfg = self._read_live_config()
        syms = live_cfg.get("BOT_ACTIVE_SYMBOLS", getattr(config, "SYMBOLS", []))
        self._atomic_write_signals(syms)

    def _read_live_config(self):
        try:
            if os.path.exists(BRAIN_SETTINGS_FILE):
                with open(BRAIN_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except:
            pass
        return {}

    def run(self):
        self.running = True
        logger.info(
            "Bot Daemon V4.2.1 (Decoupled Threads & Dynamic Trend) đã khởi động."
        )
        last_signal_scan = 0

        while self.running:
            try:
                live_cfg = self._read_live_config()
                bot_active = live_cfg.get(
                    "BOT_ACTIVE",
                    live_cfg.get(
                        "AUTO_TRADE_ENABLED",
                        getattr(config, "AUTO_TRADE_ENABLED", False),
                    ),
                )
                symbols = live_cfg.get(
                    "BOT_ACTIVE_SYMBOLS",
                    getattr(
                        config, "BOT_ACTIVE_SYMBOLS", getattr(config, "SYMBOLS", [])
                    ),
                )
                daemon_delay = getattr(config, "DAEMON_LOOP_DELAY", 15)
                now = time.time()

                # 1. QUÉT TÍN HIỆU ENTRY (Chu kỳ 15s)
                if symbols and (now - last_signal_scan >= daemon_delay):
                    self._scan_signals(symbols, bot_active)
                    last_signal_scan = now
                    self._atomic_write_signals(symbols)

                # 2. QUÉT DCA/PCA (Chu kỳ 2s - Độc lập hoàn toàn)
                if (
                    bot_active
                    and symbols
                    and (now - self.last_dca_pca_scan >= self.dca_pca_interval)
                ):
                    self._scan_dca_pca()
                    self.last_dca_pca_scan = now

                # Luồng gốc ngủ rất ngắn để không gây kẹt tiến trình
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Lỗi Loop trong Daemon: {e}")
                time.sleep(2)

    def _scan_signals(self, symbols, bot_active):
        signal_debug_state = {}

        for sym in symbols:
            if not self.running:
                break

            dfs, context = data_engine.fetch_data_v4(sym)
            if dfs is None or context is None:
                signal_debug_state[sym] = "Đang tải dữ liệu MT5..."
                continue

            # [FIX CORE]: Luôn chạy hàm generate_signal_v4 để tính toán và lưu Trend, Mode vào biến context
            # Đảm bảo UI luôn nhận được cấu trúc thị trường mới nhất ngay cả khi Bot đang tắt (Manual Mode)
            signal = signal_generator.generate_signal_v4(dfs, context)

            # --- [V4.2.1] Gói toàn bộ context (đã được generate_signal_v4 bơm data) vào Heartbeat ---
            self.heartbeat_contexts[sym] = context.copy()
            self.heartbeat_contexts[sym].update({"timestamp": time.time()})

            # [FIX] Luôn gửi tín hiệu vào hàng chờ (để SignalListener hiển thị Thinking Logs)
            if signal == 1:
                self._add_signal("BUY", sym, context, "ENTRY")
                signal_debug_state[sym] = (
                    "✅ ĐÃ BÓP CÒ BUY" if bot_active else "⏸️ (TEST) Tín hiệu BUY"
                )
            elif signal == -1:
                self._add_signal("SELL", sym, context, "ENTRY")
                signal_debug_state[sym] = (
                    "✅ ĐÃ BÓP CÒ SELL" if bot_active else "⏸️ (TEST) Tín hiệu SELL"
                )
            else:
                signal_debug_state[sym] = (
                    "⏳ Đang chờ điều kiện bóp cò..."
                    if bot_active
                    else "⏸️ Đang theo dõi..."
                )

        self._write_signal_debugger(signal_debug_state)

    def _scan_dca_pca(self):
        brain = signal_generator._get_brain_settings()
        dca_cfg = brain.get("dca_config", getattr(config, "DCA_CONFIG", {}))
        pca_cfg = brain.get("pca_config", getattr(config, "PCA_CONFIG", {}))

        if not dca_cfg.get("ENABLED", False) and not pca_cfg.get("ENABLED", False):
            return

        positions = mt5.positions_get()
        if not positions:
            return

        bot_magic = getattr(config, "BOT_MAGIC_NUMBER", 9999)
        bot_positions = {}
        for pos in positions:
            if pos.magic == bot_magic:
                if pos.symbol not in bot_positions:
                    bot_positions[pos.symbol] = []
                bot_positions[pos.symbol].append(pos)

        for symbol, pos_list in bot_positions.items():
            context = self.heartbeat_contexts.get(symbol)
            if not context:
                dfs, ctx = data_engine.fetch_data_v4(symbol)
                if not ctx:
                    continue
                context = ctx

            current_price = context.get("current_price", 0)
            atr_val = context.get("atr", context.get("atr_entry", 0.0005))
            if atr_val == 0:
                atr_val = 0.0005

            pos_list.sort(key=lambda x: x.time)
            first_pos = pos_list[0]
            profit_points = (
                (current_price - first_pos.price_open)
                if first_pos.type == mt5.ORDER_TYPE_BUY
                else (first_pos.price_open - current_price)
            )

            # DCA
            if (
                dca_cfg.get("ENABLED", False)
                and profit_points < 0
                and len(pos_list) < dca_cfg.get("MAX_STEPS", 3)
            ):
                if abs(profit_points) >= (dca_cfg.get("DISTANCE_ATR_R", 1.0) * atr_val):
                    self._add_signal(
                        "BUY" if first_pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                        symbol,
                        context,
                        "DCA",
                    )
                    time.sleep(0.5)
                    continue

            # PCA
            if (
                pca_cfg.get("ENABLED", False)
                and profit_points > 0
                and len(pos_list) < pca_cfg.get("MAX_STEPS", 2)
            ):
                is_safe = (
                    first_pos.type == mt5.ORDER_TYPE_BUY
                    and first_pos.sl > first_pos.price_open
                ) or (
                    first_pos.type == mt5.ORDER_TYPE_SELL
                    and (first_pos.sl > 0 and first_pos.sl < first_pos.price_open)
                )
                if is_safe and profit_points >= (
                    pca_cfg.get("DISTANCE_ATR_R", 1.5) * atr_val
                ):
                    self._add_signal(
                        "BUY" if first_pos.type == mt5.ORDER_TYPE_BUY else "SELL",
                        symbol,
                        context,
                        "PCA",
                    )
                    time.sleep(0.5)


if __name__ == "__main__":
    # [NEW V4.3] Khởi chạy hệ thống Log 3 Lớp chuẩn xác cho luồng Bot ngầm
    setup_logging(debug_mode=getattr(config, "ENABLE_DEBUG_LOGGING", False))

    daemon = StandaloneBotDaemon()
    try:
        if daemon.connector._is_connected:
            daemon.run()
    except KeyboardInterrupt:
        import logging

        logger = logging.getLogger("BotDaemon")
        logger.info("Đang tắt tiến trình Daemon...")
