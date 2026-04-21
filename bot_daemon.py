# -*- coding: utf-8 -*-
# FILE: bot_daemon.py
# V3.0: STANDALONE DAEMON - LIVE SIGNALS WRITER (KAISER EDITION)
# GIẢI QUYẾT TRIỆT ĐỂ LỖI IMPORT BẰNG CÁCH GIAO TIẾP QUA JSON (TÁCH BIỆT HOÀN TOÀN)

import time
import json
import os
import uuid
import logging
from datetime import datetime
import MetaTrader5 as mt5

import config
from core.exness_connector import ExnessConnector
from core.data_engine import DataEngine
from signals.signal_generator import SignalGenerator

# Logging riêng cho Daemon process để dễ debug ngầm
logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [DAEMON] %(message)s")
logger = logging.getLogger("BotDaemon")

SIGNAL_FILE = os.path.join(getattr(config, "DATA_DIR", "data"), "live_signals.json")
STATE_FILE = os.path.join(getattr(config, "DATA_DIR", "data"), "bot_state.json")

class StandaloneBotDaemon:
    def __init__(self):
        self.running = False
        
        # 1. Khởi tạo kết nối MT5 riêng cho tiến trình ngầm
        self.connector = ExnessConnector()
        if not self.connector.connect():
            logger.error("Không thể kết nối MT5. Daemon sẽ dừng.")
            return
            
        self.data_engine = DataEngine(self.connector)
        self.signal_gen = SignalGenerator()
        
        self.dca_pca_interval = 15
        self.last_dca_pca_scan = 0

    def _update_state(self, symbol, status, signal="NONE"):
        """Ghi trạng thái để UI Dashboard hiển thị"""
        state = {}
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    state = json.load(f)
            except: pass
        
        state[symbol] = {
            "status": status,
            "last_signal": signal,
            "timestamp": time.time()
        }
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        try:
            with open(STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except: pass

    def _write_signal(self, action, symbol, context, signal_class="ENTRY"):
        """Ghi tín hiệu vào live_signals.json để SignalListener (trong main.py) bắt lấy"""
        signal_data = {
            "signal_id": str(uuid.uuid4()),
            "timestamp": time.time(),
            "valid_for": 300, # Tín hiệu sống trong 5 phút
            "action": action,
            "symbol": symbol,
            "signal_class": signal_class,
            "sl_price": 0.0, # Nhường TradeManager tính toán SL
            "tp_price": 0.0,
            "bot_risk_percent": getattr(config, "BOT_RISK_PERCENT", 0.3),
            "context": context # Chuyển toàn bộ Context (Swing/ATR) sang cho TradeManager
        }
        
        payload = {
            "brain_heartbeat": {
                "status": "HEALTHY", 
                "wakeup_time": 0, 
                "active_symbols": getattr(config, "BOT_ACTIVE_SYMBOLS", [])
            }, 
            "pending_signals": []
        }
        
        if os.path.exists(SIGNAL_FILE):
            try:
                with open(SIGNAL_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    payload["pending_signals"] = data.get("pending_signals", [])
            except: pass
            
        payload["pending_signals"].append(signal_data)
        
        # Chỉ giữ 10 tín hiệu gần nhất để file không bị phình to
        payload["pending_signals"] = payload["pending_signals"][-10:] 
        
        os.makedirs(os.path.dirname(SIGNAL_FILE), exist_ok=True)
        try:
            with open(SIGNAL_FILE, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4)
            logger.info(f"Đã phát tín hiệu {action} cho {symbol} ({signal_class})")
        except Exception as e:
            logger.error(f"Lỗi ghi tín hiệu: {e}")

    def run(self):
        """Vòng lặp vĩnh cửu của Daemon Process"""
        self.running = True
        logger.info("Bot Daemon (Standalone) đã khởi động thành công.")
        
        while self.running:
            try:
                # Nếu tắt cả Auto Trade lẫn Bot Active thì ngủ
                if not getattr(config, "BOT_ACTIVE", False) and not getattr(config, "AUTO_TRADE_ENABLED", False):
                    time.sleep(2)
                    continue

                symbols = getattr(config, "BOT_ACTIVE_SYMBOLS", getattr(config, "SYMBOLS", []))
                if not symbols:
                    time.sleep(2)
                    continue

                # ==================================
                # LUỒNG 1: QUÉT ENTRY SIGNAL
                # ==================================
                for sym in symbols:
                    if not self.running: break
                    
                    data_package = self.data_engine.fetch_and_prepare(sym, self.signal_gen.config)
                    if not data_package or "context" not in data_package:
                        self._update_state(sym, "Lỗi Data")
                        continue

                    final_signal, details = self.signal_gen.generate_signal(data_package)
                    
                    sig_str = "NONE"
                    if final_signal == 1: sig_str = "BUY"
                    elif final_signal == -1: sig_str = "SELL"
                    
                    self._update_state(sym, "Đang quét", sig_str)

                    if final_signal != 0:
                        action = "BUY" if final_signal == 1 else "SELL"
                        self._write_signal(action, sym, details, "ENTRY")
                        time.sleep(2) # Chống spam lệnh liên thanh

                # ==================================
                # LUỒNG 2: QUÉT DCA/PCA
                # ==================================
                now = time.time()
                if now - self.last_dca_pca_scan >= self.dca_pca_interval:
                    self._scan_dca_pca()
                    self.last_dca_pca_scan = now

                time.sleep(getattr(config, "DAEMON_LOOP_DELAY", 5))

            except Exception as e:
                logger.error(f"Lỗi Loop trong Daemon: {e}")
                time.sleep(5)

    def _scan_dca_pca(self):
        """Quét mở lệnh và bắn tín hiệu nhồi DCA/PCA sang live_signals.json"""
        brain = self.signal_gen.config
        dca_cfg = brain.get("dca_config", getattr(config, "DCA_CONFIG", {}))
        pca_cfg = brain.get("pca_config", getattr(config, "PCA_CONFIG", {}))
        
        if not dca_cfg.get("ENABLED", False) and not pca_cfg.get("ENABLED", False):
            return

        positions = mt5.positions_get()
        if not positions: return

        bot_magic = getattr(config, "BOT_MAGIC_NUMBER", 999999)
        bot_positions = {}
        for pos in positions:
            if pos.magic == bot_magic:
                if pos.symbol not in bot_positions: 
                    bot_positions[pos.symbol] = []
                bot_positions[pos.symbol].append(pos)

        for symbol, pos_list in bot_positions.items():
            data_package = self.data_engine.fetch_and_prepare(symbol, brain)
            if not data_package or "context" not in data_package: continue
            
            df_trigger = data_package["raw_trigger"]
            context = data_package["context"]
            
            tick = mt5.symbol_info_tick(symbol)
            if not tick: continue
            current_price = tick.ask if pos_list[0].type == mt5.ORDER_TYPE_BUY else tick.bid
            atr_val = context.get("atr", 0.0005)
            
            pos_list.sort(key=lambda x: x.time)
            first_pos = pos_list[0]
            
            profit_points = (current_price - first_pos.price_open) if first_pos.type == mt5.ORDER_TYPE_BUY else (first_pos.price_open - current_price)
            
            # LOGIC DCA
            if dca_cfg.get("ENABLED", False) and profit_points < 0 and len(pos_list) < dca_cfg.get("MAX_STEPS", 3):
                dist_atr_r = dca_cfg.get("DISTANCE_ATR_R", 1.0)
                if abs(profit_points) >= (dist_atr_r * atr_val):
                    last_closed_candle = df_trigger.iloc[-2]
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
                    mode = self.signal_gen._detect_market_mode(context, df_trigger)
                    if mode == "BREAKOUT":
                        action = "BUY" if first_pos.type == mt5.ORDER_TYPE_BUY else "SELL"
                        self._write_signal(action, symbol, context, "PCA")
                        time.sleep(1)

# Entry point để Subprocess Popen từ main.py gọi được
if __name__ == "__main__":
    daemon = StandaloneBotDaemon()
    try:
        if daemon.connector._is_connected:
            daemon.run()
    except KeyboardInterrupt:
        logger.info("Đang tắt tiến trình Daemon...")