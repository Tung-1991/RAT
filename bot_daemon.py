# -*- coding: utf-8 -*-
# FILE: bot_daemon.py
# V4.3.7: REFACTORED - FIXED SYMBOL ERROR & SIGNALS SYNC

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

# Import chính xác từ thư mục signals với đúng tên hàm trong file của Ngài
try:
    from signals.signal_generator import get_signal
    from signals.atr import calculate_atr
    from signals.swing_point import get_last_swing_points
except ImportError as e:
    print(f"❌ LỖI IMPORT: {e}")

# Khởi tạo Logger
logger = logging.getLogger("ExnessBot")
if not logger.hasHandlers():
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s] - %(message)s")

# Đường dẫn file giao tiếp
SIGNAL_FILE = os.path.join(config.DATA_DIR, "live_signals.json")

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
        next_run = now.replace(second=2, microsecond=0) # Đợi thêm 2s cho chắc chắn đóng nến
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
    """Ghi file nguyên tử (Atomic Write)"""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    temp_file = SIGNAL_FILE + ".tmp"
    try:
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4)
        os.replace(temp_file, SIGNAL_FILE)
    except Exception as e:
        logger.error(f"Lỗi khi ghi file tín hiệu: {e}")

def run_daemon():
    logger.info("--- ⚙️ DAEMON V4.3.7: STANDARDIZED STARTING ---")
    
    connector = ExnessConnector()
    if not connector.connect():
        logger.critical("Daemon không thể kết nối MT5. Dừng.")
        return

    # Lấy config dưới dạng dict để truyền vào các hàm signal
    config_dict = {key: getattr(config, key) for key in dir(config) if not key.startswith('__')}
    sym = config.DEFAULT_SYMBOL
    
    while True:
        try:
            entry_tf = config.entry_timeframe
            sleep_sec = _get_sleep_time_to_next_candle(entry_tf)
            
            # Gửi Heartbeat báo hiệu Daemon vẫn sống cho UI hiện đèn
            heartbeat_payload = {
                "pending_signals": [],
                "brain_heartbeat": {
                    "last_scan": time.time(),
                    "active_symbols": [sym],
                    "status": f"SLEEPING ({sleep_sec}s)",
                    "context": {}
                }
            }
            write_signal_atomically(heartbeat_payload)
            
            logger.info(f"[DAEMON] Chờ nến {entry_tf} đóng trong {sleep_sec}s...")
            time.sleep(sleep_sec)
            
            logger.info("[DAEMON] Đang tải dữ liệu & phân tích...")
            # Sử dụng đúng các hằng số từ config.py
            data_h1 = connector.get_historical_data(sym, config.trend_timeframe.lower(), config.NUM_H1_BARS)
            data_m15 = connector.get_historical_data(sym, config.entry_timeframe.lower(), config.NUM_M15_BARS)

            if data_h1 is None or data_m15 is None or data_h1.empty or data_m15.empty:
                logger.warning("[DAEMON] Dữ liệu trống. Thử lại sau.")
                continue

            # --- GỌI BỘ NÃO TÌM TÍN HIỆU (Signals folder) ---
            # get_signal của Ngài nhận (df_h1, df_m15, config_dict)
            signal_type = get_signal(data_h1, data_m15, config_dict)
            
            # Tính toán Context để hiển thị lên UI Dashboard
            atr_series = calculate_atr(data_m15, config.atr_period)
            current_atr = float(atr_series.iloc[-1]) if atr_series is not None and not atr_series.empty else 0.0
            last_high, last_low = get_last_swing_points(data_m15, config_dict)

            # Cập nhật context thực tế cho UI
            market_context = {
                "trend": "UP" if data_h1['close'].iloc[-1] > data_h1['close'].ewm(span=50).mean().iloc[-1] else "DOWN",
                "swing_high": float(last_high) if last_high else 0.0,
                "swing_low": float(last_low) if last_low else 0.0,
                "atr": current_atr
            }

            payload = {
                "pending_signals": [],
                "brain_heartbeat": {
                    "last_scan": time.time(),
                    "active_symbols": [sym],
                    "status": "HEALTHY",
                    "context": market_context
                }
            }

            if signal_type:
                logger.info(f"[DAEMON] PHÁT HIỆN TÍN HIỆU {signal_type}! Đang đóng gói...")
                
                sl_atr_mult = config.sl_atr_multiplier
                sl_price = 0.0
                if signal_type == "BUY":
                    sl_price = last_low - (sl_atr_mult * current_atr) if last_low else data_m15['close'].iloc[-1] * 0.99
                else:
                    sl_price = last_high + (sl_atr_mult * current_atr) if last_high else data_m15['close'].iloc[-1] * 1.01

                payload["pending_signals"].append({
                    "signal_id": str(uuid.uuid4()),
                    "timestamp": time.time(),
                    "symbol": sym,
                    "action": signal_type,
                    "signal_class": "ENTRY", 
                    "suggested_price": float(data_m15['close'].iloc[-1]),
                    "sl_price": float(sl_price),
                    "valid_for": 300,
                    "status": "NEW"
                })

            write_signal_atomically(payload)
            logger.info(f"✅ Dashboard Synced cho {sym}")
                
        except Exception as e:
            logger.error(f"[DAEMON] Lỗi vòng lặp: {e}", exc_info=True)
            time.sleep(10)

if __name__ == "__main__":
    try:
        run_daemon()
    except KeyboardInterrupt:
        logger.info("--- 🛑 DAEMON ĐÃ DỪNG THEO YÊU CẦU (Ctrl+C) ---")
        # Thêm các lệnh dọn dẹp nếu cần (ví dụ: đóng kết nối MT5)
        try:
            import MetaTrader5 as mt5
            mt5.shutdown()
            logger.info("✅ Đã đóng kết nối MetaTrader5.")
        except:
            pass