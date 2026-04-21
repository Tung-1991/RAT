# -*- coding: utf-8 -*-
# FILE: bot_daemon.py
# V3.0: STANDALONE DAEMON - LIVE SIGNALS WRITER (KAISER EDITION FINAL)

import time
import json
import os
import uuid
import logging
from datetime import datetime
import MetaTrader5 as mt5

import config
from core.exness_connector import ExnessConnector
from core.data_engine import data_engine
from signals.signal_generator import signal_generator

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [DAEMON] %(message)s")
logger = logging.getLogger("BotDaemon")

SIGNAL_FILE = os.path.join(getattr(config, "DATA_DIR", "data"), "live_signals.json")
STATE_FILE = os.path.join(getattr(config, "DATA_DIR", "data"), "bot_state.json")

class StandaloneBotDaemon:
    def __init__(self):
        self.running = False
        
        self.connector = ExnessConnector()
        if not self.connector.connect():
            logger.error("Không thể kết nối MT5. Daemon sẽ dừng.")
            
        self.dca_pca_interval = 15
        self.last_dca_pca_scan = 0

    def _update_state(self, symbol, status, signal="NONE"):
        state = {}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except Exception:
                pass
        
        state[symbol] = {
            "status": status,
            "last_signal": signal,
            "timestamp": time.time()
        }
        
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception:
            pass

    def _write_signal(self, action, symbol, context, signal_class="ENTRY"):
        signal_data = {
            "signal_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "valid_for": 300, 
            "action": action,
            "symbol": symbol,
            "signal_class": signal_class,
            "sl_price": 0.0, 
            "tp_price": 0.0,
            "bot_risk_percent": getattr(config, "BOT_RISK_PERCENT", 0.3),
            "context": context 
        }
        
        payload = {
            "brain_heartbeat": {
                "status": "HEALTHY", 
                "wakeup_time": 0, 
                "active_symbols": getattr(config, "BOT_ACTIVE_SYMBOLS", getattr(config, "SYMBOLS", []))
            }, 
            "pending_signals": []
        }
        
        if os.path.exists(SIGNAL_FILE):
            try:
                with open(SIGNAL_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    payload["pending_signals"] = data.get("pending_signals", [])
            except Exception:
                pass
            
        payload["pending_signals"].append(signal_data)
        payload["pending_signals"] = payload["pending_signals"][-10:] 
        
        os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)
        try:
            with open(SIGNAL_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
            logger.info(f"Đã phát tín hiệu {action} cho {symbol} ({signal_class})")
        except Exception as e:
            logger.error(f"Lỗi ghi tín hiệu: {e}")

    def run(self):
        self.running = True
        logger.info("Bot Daemon (Standalone) đã khởi động thành công.")
        
        while self.running:
            try:
                if not getattr(config, "BOT_ACTIVE", False) and not getattr(config, "AUTO_TRADE_ENABLED", False):
                    time.sleep(2)
                    continue

                symbols = getattr(config, "BOT_ACTIVE_SYMBOLS", getattr(config, "SYMBOLS", []))
                if not symbols:
                    time.sleep(2)
                    continue

                # QUÉT ENTRY
                for sym in symbols:
                    if not self.running: break
                    
                    df_entry, df_trend, context = data_engine.fetch_and_prepare(sym)
                    if df_entry is None or context is None:
                        self._update_state(sym, "Lỗi Data")
                        continue

                    signal = signal_generator.generate_signal(df_entry, df_trend, context)
                    
                    sig_str = "NONE"
                    if signal == 1: sig_str = "BUY"
                    elif signal == -1: sig_str = "SELL"
                    
                    self._update_state(sym, "Đang quét", sig_str)

                    if signal != 0:
                        action = "BUY" if signal == 1 else "SELL"
                        self._write_signal(action, sym, context, "ENTRY")
                        time.sleep(2) 

                # QUÉT DCA/PCA
                now = time.time()
                if now - self.last_dca_pca_scan >= self.dca_pca_interval:
                    self._scan_dca_pca()
                    self.last_dca_pca_scan = now

                time.sleep(getattr(config, "DAEMON_LOOP_DELAY", 5))

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
            df_entry, df_trend, context = data_engine.fetch_and_prepare(symbol)
            if df_entry is None or context is None: continue
            
            current_price = context.get("current_price", 0)
            atr_val = context.get("atr_entry", 0.0005)
            
            pos_list.sort(key=lambda x: x.time)
            first_pos = pos_list[0]
            
            profit_points = (current_price - first_pos.price_open) if first_pos.type == mt5.ORDER_TYPE_BUY else (first_pos.price_open - current_price)
            
            # LOGIC DCA
            if dca_cfg.get("ENABLED", False) and profit_points < 0 and len(pos_list) < dca_cfg.get("MAX_STEPS", 3):
                dist_atr_r = dca_cfg.get("DISTANCE_ATR_R", 1.0)
                if abs(profit_points) >= (dist_atr_r * atr_val):
                    last_closed_candle = df_entry.iloc[-2]
                    is_bullish = last_closed_candle['close'] > last_closed_candle['open']
                    if (first_pos.type == mt5.ORDER_TYPE_BUY and is_bullish) or (first_pos.type == mt5.ORDER_TYPE_SELL and not is_bullish):
                        action = "BUY" if first_pos.type == mt5.ORDER_TYPE_BUY else "SELL"
                        self._write_signal(action, symbol, context, "DCA")
                        time.sleep(1)
                        continue

            # LOGIC PCA
            if pca_cfg.get("ENABLED", False) and profit_points > 0 and len(pos_list) < pca_cfg.get("MAX_STEPS", 2):
                dist_atr_r = pca_cfg.get("DISTANCE_ATR_R", 1.5)
                is_safe = False
                if first_pos.type == mt5.ORDER_TYPE_BUY and first_pos.sl > first_pos.price_open: is_safe = True
                if first_pos.type == mt5.ORDER_TYPE_SELL and (first_pos.sl > 0 and first_pos.sl < first_pos.price_open): is_safe = True

                if is_safe and profit_points >= (dist_atr_r * atr_val):
                    adx_val = df_trend[f"ADX_{14}"].iloc[-1] if f"ADX_{14}" in df_trend.columns else 0
                    if adx_val >= pca_cfg.get("CONFIRM_ADX", 23):
                        action = "BUY" if first_pos.type == mt5.ORDER_TYPE_BUY else "SELL"
                        self._write_signal(action, symbol, context, "PCA")
                        time.sleep(1)

if __name__ == "__main__":
    daemon = StandaloneBotDaemon()
    try:
        if daemon.connector._is_connected:
            daemon.run()
    except KeyboardInterrupt:
        logger.info("Đang tắt tiến trình Daemon...")