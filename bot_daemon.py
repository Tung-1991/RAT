# -*- coding: utf-8 -*-
# FILE: bot_daemon.py
# V3.1: STANDALONE DAEMON - SAFE ATOMIC WRITER & CONTEXT BROADCASTER (KAISER EDITION)

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

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [DAEMON] %(message)s")
logger = logging.getLogger("BotDaemon")

SIGNAL_FILE = os.path.join(getattr(config, "DATA_DIR", "data"), "live_signals.json")
SIGNAL_FILE_TMP = SIGNAL_FILE + ".tmp"
BRAIN_SETTINGS_FILE = os.path.join(getattr(config, "DATA_DIR", "data"), "brain_settings.json")

class StandaloneBotDaemon:
    def __init__(self):
        self.running = False
        
        self.connector = ExnessConnector()
        if not self.connector.connect():
            logger.error("Không thể kết nối MT5. Daemon sẽ dừng.")
            
        self.dca_pca_interval = 2 # Quét DCA/PCA nhanh mỗi 2s
        self.last_dca_pca_scan = 0
        
        self.pending_signals = []
        self.heartbeat_contexts = {} # Lưu trữ Swing, ATR để đẩy lên UI

    def _atomic_write_signals(self, active_symbols):
        """Ghi file an toàn (Atomic Write) để UI đọc không bao giờ bị crash"""
        
        payload = {
            "brain_heartbeat": {
                "status": "HEALTHY", 
                "wakeup_time": time.time(), 
                "active_symbols": active_symbols,
                "contexts": self.heartbeat_contexts # Bơm data sang UI để vẽ Swing/Trend
            }, 
            "pending_signals": self.pending_signals[-10:] # Chỉ giữ 10 tín hiệu gần nhất
        }
        
        os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)
        try:
            with open(SIGNAL_FILE_TMP, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
            os.replace(SIGNAL_FILE_TMP, SIGNAL_FILE) # Đổi tên nguyên tử
        except Exception as e:
            logger.error(f"Lỗi ghi tín hiệu: {e}")

    def _add_signal(self, action, symbol, context, signal_class="ENTRY"):
        sig_id = str(uuid.uuid4())
        self.pending_signals.append({
            "signal_id": sig_id,
            "timestamp": time.time(),
            "valid_for": 300 if signal_class == "ENTRY" else 60, # DCA/PCA chỉ sống 60s
            "action": action,
            "symbol": symbol,
            "signal_class": signal_class,
            "context": context 
        })
        logger.info(f"Đã phát tín hiệu {action} cho {symbol} ({signal_class})")
        # Ghi ngay lập tức, tự đọc lại active_symbols từ file json để ghi
        live_cfg = self._read_live_config()
        syms = live_cfg.get("BOT_ACTIVE_SYMBOLS", getattr(config, "SYMBOLS", []))
        self._atomic_write_signals(syms) 

    def _read_live_config(self):
        """[ĐÃ FIX] Đọc cấu hình JSON liên tục để hỗ trợ Hot-Reload từ UI"""
        try:
            if os.path.exists(BRAIN_SETTINGS_FILE):
                with open(BRAIN_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def run(self):
        self.running = True
        logger.info("Bot Daemon (Standalone) đã khởi động thành công.")
        
        while self.running:
            try:
                # 1. ĐỌC CONFIG MỚI NHẤT (HOT-RELOAD TỪ SANDBOX V3.0)
                live_cfg = self._read_live_config()
                
                # Ưu tiên lấy từ JSON (UI vừa chỉnh), nếu không có mới lấy từ config.py mặc định
                bot_active = live_cfg.get("BOT_ACTIVE", live_cfg.get("AUTO_TRADE_ENABLED", getattr(config, "AUTO_TRADE_ENABLED", False)))
                symbols = live_cfg.get("BOT_ACTIVE_SYMBOLS", getattr(config, "BOT_ACTIVE_SYMBOLS", getattr(config, "SYMBOLS", [])))
                
                if bot_active and symbols:
                    # 2. QUÉT ENTRY & CẬP NHẬT CONTEXT CHO UI
                    for sym in symbols:
                        if not self.running: break
                        
                        df_entry, df_trend, context = data_engine.fetch_and_prepare(sym)
                        if df_entry is None or context is None:
                            continue

                        # Lưu context để bơm sang UI qua Heartbeat
                        self.heartbeat_contexts[sym] = {
                            "trend": context.get("trend", "NONE"), # <--- [ĐÃ FIX] Bổ sung Trend lên UI
                            "swing_high": context.get("swing_high_entry", 0),
                            "swing_low": context.get("swing_low_entry", 0),
                            "atr": context.get("atr_entry", 0),
                            "current_price": context.get("current_price", 0),
                            "timestamp": time.time()
                        }

                        signal = signal_generator.generate_signal(df_entry, df_trend, context)
                        if signal != 0:
                            action = "BUY" if signal == 1 else "SELL"
                            self._add_signal(action, sym, context, "ENTRY")

                    # 3. QUÉT DCA/PCA LIÊN TỤC
                    now = time.time()
                    if now - self.last_dca_pca_scan >= self.dca_pca_interval:
                        self._scan_dca_pca()
                        self.last_dca_pca_scan = now

                # 4. GHI HEARTBEAT CẬP NHẬT LIÊN TỤC LÊN UI (Truyền symbol mới nhất)
                self._atomic_write_signals(symbols)
                time.sleep(getattr(config, "DAEMON_LOOP_DELAY", 2))

            except Exception as e:
                logger.error(f"Lỗi Loop trong Daemon: {e}")
                time.sleep(5)

    def _scan_dca_pca(self):
        brain = signal_generator._get_brain_settings()
        dca_cfg = brain.get("dca_config", getattr(config, "DCA_CONFIG", {}))
        pca_cfg = brain.get("pca_config", getattr(config, "PCA_CONFIG", {}))
        
        if not dca_cfg.get("ENABLED", False) and not pca_cfg.get("ENABLED", False):
            return

        positions = mt5.positions_get()
        if not positions: return

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
                _, _, context = data_engine.fetch_and_prepare(symbol)
                if not context: continue

            current_price = context.get("current_price", 0)
            atr_val = context.get("atr", context.get("atr_entry", 0.0005))
            
            pos_list.sort(key=lambda x: x.time)
            first_pos = pos_list[0]
            
            profit_points = (current_price - first_pos.price_open) if first_pos.type == mt5.ORDER_TYPE_BUY else (first_pos.price_open - current_price)
            
            # LOGIC DCA
            if dca_cfg.get("ENABLED", False) and profit_points < 0 and len(pos_list) < dca_cfg.get("MAX_STEPS", 3):
                dist_atr_r = dca_cfg.get("DISTANCE_ATR_R", 1.0)
                if abs(profit_points) >= (dist_atr_r * atr_val):
                    action = "BUY" if first_pos.type == mt5.ORDER_TYPE_BUY else "SELL"
                    self._add_signal(action, symbol, context, "DCA")
                    time.sleep(0.5)
                    continue

            # LOGIC PCA
            if pca_cfg.get("ENABLED", False) and profit_points > 0 and len(pos_list) < pca_cfg.get("MAX_STEPS", 2):
                dist_atr_r = pca_cfg.get("DISTANCE_ATR_R", 1.5)
                is_safe = False
                if first_pos.type == mt5.ORDER_TYPE_BUY and first_pos.sl > first_pos.price_open: is_safe = True
                if first_pos.type == mt5.ORDER_TYPE_SELL and (first_pos.sl > 0 and first_pos.sl < first_pos.price_open): is_safe = True

                if is_safe and profit_points >= (dist_atr_r * atr_val):
                    action = "BUY" if first_pos.type == mt5.ORDER_TYPE_BUY else "SELL"
                    self._add_signal(action, symbol, context, "PCA")
                    time.sleep(0.5)

if __name__ == "__main__":
    daemon = StandaloneBotDaemon()
    try:
        if daemon.connector._is_connected:
            daemon.run()
    except KeyboardInterrupt:
        logger.info("Đang tắt tiến trình Daemon...")