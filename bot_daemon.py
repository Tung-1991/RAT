# -*- coding: utf-8 -*-
# FILE: bot_daemon.py
# V5.2: MULTI-COIN SCANNER, TP=0.0 ENFORCED & BOT RISK SYNC

import time
import json
import os
import uuid
import logging
from datetime import datetime, timedelta
import re
import pandas as pd

import config
from core.exness_connector import ExnessConnector

try:
    from signals.signal_generator import get_signal
    from signals.atr import calculate_atr
    from signals.swing_point import get_last_swing_points
except ImportError as e:
    print(f"❌ LỖI IMPORT: {e}")

logger = logging.getLogger("ExnessBot")
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] - %(message)s")

# Đường dẫn file chia sẻ cấu hình giữa UI và Daemon
BRAIN_SETTINGS_FILE = os.path.join(config.DATA_DIR, "brain_settings.json")
SIGNAL_FILE = os.path.join(config.DATA_DIR, "live_signals.json")

def load_live_config():
    """Nạp cấu hình từ file config.py và đè lên bằng dữ liệu từ brain_settings.json (Hot-Reload)"""
    current_cfg = {key: getattr(config, key) for key in dir(config) if not key.startswith('__')}
    
    if os.path.exists(BRAIN_SETTINGS_FILE):
        try:
            with open(BRAIN_SETTINGS_FILE, "r", encoding="utf-8") as f:
                live_data = json.load(f)
                for k, v in live_data.items():
                    current_cfg[k] = v
        except (json.JSONDecodeError, IOError):
            pass
    return current_cfg

def _parse_timeframe_to_minutes(tf_str: str) -> int:
    tf_str = tf_str.lower()
    match = re.match(r"(\d+)([mhd])", tf_str)
    if not match: return 0
    val, unit = int(match.group(1)), match.group(2)
    if unit == 'm': return val
    elif unit == 'h': return val * 60
    elif unit == 'd': return val * 24 * 60
    return 0

def _get_sleep_time_to_next_candle(timeframe_str: str) -> int:
    try:
        minutes = _parse_timeframe_to_minutes(timeframe_str)
        if minutes == 0: return 60
        now = datetime.now()
        # Cộng thêm 2 giây bù độ trễ của sàn MT5 khi nến mới mở
        next_run = now.replace(second=2, microsecond=0) 
        minute_to_round = (now.minute // minutes) * minutes + minutes
        
        if minute_to_round >= 60:
            next_run = next_run.replace(minute=0, hour=(now.hour + 1) % 24)
            if next_run.hour == 0: next_run += timedelta(days=1)
        else:
            next_run = next_run.replace(minute=minute_to_round)
            
        sleep_seconds = (next_run - now).total_seconds()
        return max(1, int(sleep_seconds))
    except Exception as e:
        logger.error(f"Lỗi tính thời gian ngủ: {e}")
        return 60

def write_signal_atomically(payload: dict):
    os.makedirs(config.DATA_DIR, exist_ok=True)
    temp_file = SIGNAL_FILE + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
        os.replace(temp_file, SIGNAL_FILE)
    except Exception as e:
        logger.error(f"Lỗi khi ghi file tín hiệu: {e}")

def run_daemon():
    logger.info("--- ⚙️ DAEMON V5.2: MULTI-COIN SCANNER & HOT-RELOAD READY ---")
    
    connector = ExnessConnector()
    if not connector.connect():
        logger.critical("Daemon không thể kết nối MT5. Dừng.")
        return

    while True:
        try:
            # 1. NẠP CẤU HÌNH MỚI NHẤT
            config_dict = load_live_config()
            ui_symbol = config_dict.get("UI_ACTIVE_SYMBOL", config.DEFAULT_SYMBOL)
            watchlist = config_dict.get("BOT_ACTIVE_SYMBOLS", [])
            
            entry_tf = config_dict.get("entry_timeframe", "15M")
            trend_tf = config_dict.get("trend_timeframe", "1H")
            num_h1 = config_dict.get("NUM_H1_BARS", 70)
            num_m15 = config_dict.get("NUM_M15_BARS", 70)
            bot_risk = float(config_dict.get("BOT_RISK_PERCENT", 0.3))

            # Master Payload gửi lên UI
            payload = {
                "pending_signals": [],
                "brain_heartbeat": {
                    "last_scan": time.time(),
                    "active_symbols": watchlist,
                    "status": "MONITORING",
                    "context": {} # Dành riêng cho đồng coin đang mở trên UI
                }
            }

            # 2. XỬ LÝ CONTEXT CHO ĐỒNG COIN TRÊN GIAO DIỆN (Để hiển thị Dashboard)
            ui_h1 = connector.get_historical_data(ui_symbol, trend_tf.lower(), num_h1)
            ui_m15 = connector.get_historical_data(ui_symbol, entry_tf.lower(), num_m15)
            
            if ui_h1 is not None and ui_m15 is not None and not ui_h1.empty and not ui_m15.empty:
                atr_p = config_dict.get("atr_period", 14)
                atr_series = calculate_atr(ui_m15, atr_p)
                cur_atr = float(atr_series.iloc[-1]) if atr_series is not None and not atr_series.empty else 0.0
                
                shigh, slow = get_last_swing_points(ui_m15, config_dict)
                
                ema_trend_p = config_dict.get("TREND_EMA_PERIOD", 50)
                ema_trend = ui_h1['close'].ewm(span=ema_trend_p, adjust=False).mean().iloc[-1]
                
                payload["brain_heartbeat"]["context"] = {
                    "trend": "UP" if ui_h1['close'].iloc[-1] > ema_trend else "DOWN",
                    "swing_high": float(shigh) if shigh else 0.0,
                    "swing_low": float(slow) if slow else 0.0,
                    "atr": cur_atr
                }

            # 3. QUÉT TOÀN BỘ DANH SÁCH COIN (WATCHLIST) TÌM TÍN HIỆU
            if not watchlist:
                logger.warning("[DAEMON] Watchlist trống! Vui lòng chọn coin trên giao diện.")
                payload["brain_heartbeat"]["status"] = "NO COINS SELECTED"
            else:
                logger.info(f"🔍 [DAEMON] Đang quét: {', '.join(watchlist)}")
                
                for sym in watchlist:
                    data_h1 = connector.get_historical_data(sym, trend_tf.lower(), num_h1)
                    data_m15 = connector.get_historical_data(sym, entry_tf.lower(), num_m15)

                    if data_h1 is None or data_m15 is None or data_h1.empty or data_m15.empty:
                        continue

                    # Bot ra quyết định
                    signal_type = get_signal(data_h1, data_m15, config_dict)
                    
                    if signal_type:
                        logger.info(f"🧠 [DAEMON] PHÁT HIỆN TÍN HIỆU {signal_type} CHO {sym}!")
                        
                        atr_series = calculate_atr(data_m15, config_dict.get("atr_period", 14))
                        cur_atr = float(atr_series.iloc[-1]) if atr_series is not None else 0.0
                        shigh, slow = get_last_swing_points(data_m15, config_dict)
                        
                        sl_mult = config_dict.get("sl_atr_multiplier", 0.2)
                        sl_price = 0.0
                        
                        # Tính Math SL
                        if signal_type == "BUY":
                            sl_price = float(slow) - (sl_mult * cur_atr) if slow else float(data_m15['close'].iloc[-1]) * 0.99
                        else:
                            sl_price = float(shigh) + (sl_mult * cur_atr) if shigh else float(data_m15['close'].iloc[-1]) * 1.01

                        # ĐÓNG GÓI TÍN HIỆU (GỬI KÈM BOT_RISK VÀ ÉP TP = 0.0)
                        payload["pending_signals"].append({
                            "signal_id": str(uuid.uuid4()),
                            "timestamp": time.time(),
                            "symbol": sym,
                            "action": signal_type,
                            "signal_class": "ENTRY", 
                            "suggested_price": float(data_m15['close'].iloc[-1]),
                            "sl_price": float(sl_price),
                            "tp_price": 0.0,               # Ép TP = 0.0 tuyệt đối
                            "bot_risk_percent": bot_risk,  # Gửi mức rủi ro độc lập của Bot
                            "valid_for": 300,
                            "status": "NEW"
                        })

            # 4. CẬP NHẬT GIAO DIỆN & NẰM NGỦ
            write_signal_atomically(payload)
            
            sleep_sec = _get_sleep_time_to_next_candle(entry_tf)
            logger.info(f"💤 Đã quét xong. Daemon ngủ {sleep_sec} giây chờ nến {entry_tf} tiếp theo.")
            
            payload["brain_heartbeat"]["status"] = f"SLEEPING ({sleep_sec}s)"
            write_signal_atomically(payload)
            
            time.sleep(sleep_sec)
                
        except Exception as e:
            logger.error(f"[DAEMON] Lỗi vòng lặp chính: {e}", exc_info=True)
            time.sleep(5) # Ngủ ngắn nếu gặp lỗi hệ thống để tránh spam loop

if __name__ == "__main__":
    try:
        run_daemon()
    except KeyboardInterrupt:
        logger.info("🛑 Daemon đã dừng bằng tay.")