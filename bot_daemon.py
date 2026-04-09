# -*- coding: utf-8 -*-
# FILE: bot_daemon.py
# V8.3: AUTO-WAKEUP MT5 & PERSISTENT CONTEXT (KAISER EDITION)

import time
import json
import os
import logging
import uuid
import re
from datetime import datetime, timedelta

import config
from core.exness_connector import ExnessConnector

# Fail-safe Imports
try:
    from signals.atr import calculate_atr
    from signals.swing_point import get_last_swing_points as get_swing_high_low
    import signals.signal_generator as sg_module
except ImportError as e:
    print(f"❌ LỖI IMPORT MODULE TÍN HIỆU: {e}")

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] - %(message)s')
logger = logging.getLogger("Daemon")

def _get_sleep_time_to_next_candle(timeframe_str):
    try:
        tf_str = timeframe_str.lower()
        match = re.match(r"(\d+)([mhd])", tf_str)
        if not match: return 10
        val, unit = int(match.group(1)), match.group(2)
        minutes = val if unit == 'm' else (val * 60 if unit == 'h' else val * 1440)
        
        now = datetime.now()
        next_run = now.replace(second=2, microsecond=0)
        minute_to_round = (now.minute // minutes) * minutes + minutes
        if minute_to_round >= 60:
            next_run = next_run.replace(minute=0, hour=(now.hour + 1) % 24)
            if next_run.hour == 0: next_run += timedelta(days=1)
        else:
            next_run = next_run.replace(minute=minute_to_round)
        return max(5, int((next_run - now).total_seconds()))
    except: return 10

def reload_brain_config():
    settings_file = os.path.join(config.DATA_DIR, "brain_settings.json")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
                for k, v in settings.items():
                    if hasattr(config, k) and k != "COIN_LIST":
                        setattr(config, k, v)
        except Exception as e:
            logger.error(f"[DAEMON] Lỗi đọc brain_settings.json: {e}")

def run_daemon():
    logger.info("--- ⚙️ DAEMON V8.3: AUTO-WAKEUP & PERSISTENT CONTEXT ---")
    connector = ExnessConnector()
    if not connector.connect(): return

    signal_file = os.path.join(config.DATA_DIR, "live_signals.json")
    
    # Đưa Context ra ngoài vòng lặp để giữ lại data cũ nếu MT5 rớt mạng tạm thời (Chống hiện --)
    all_contexts = {} 
    mt5_error_count = 0

    while True:
        try:
            reload_brain_config()
            active_symbols = getattr(config, "BOT_ACTIVE_SYMBOLS", [])
            entry_tf = getattr(config, "entry_timeframe", "15m")
            
            all_signals = []
            cycle_has_error = False

            for symbol in active_symbols:
                df_h1 = connector.get_historical_data(symbol, config.trend_timeframe, config.NUM_H1_BARS)
                df_m15 = connector.get_historical_data(symbol, entry_tf, config.NUM_M15_BARS)
                
                if df_h1 is None or df_m15 is None or df_m15.empty: 
                    cycle_has_error = True
                    continue

                sig_action = sg_module.get_signal(df_h1, df_m15, config.__dict__) if sg_module else None
                
                atr_val, sh, sl = 0.0, 0.0, 0.0
                atr_series = calculate_atr(df_m15, config.atr_period)
                if atr_series is not None: atr_val = round(atr_series.iloc[-1], 5)
                
                res_h, res_l = get_swing_high_low(df_m15, config.__dict__)
                sh, sl = (round(res_h, 5) if res_h else 0.0), (round(res_l, 5) if res_l else 0.0)

                ema_v = df_h1['close'].ewm(span=config.TREND_EMA_PERIOD, adjust=False).mean().iloc[-1]
                trend_dir = "UP" if df_h1['close'].iloc[-1] > ema_v else "DOWN"

                all_contexts[symbol] = {
                    "trend": trend_dir,
                    "swing_high": sh,
                    "swing_low": sl,
                    "atr": atr_val
                }

                if sig_action in ["BUY", "SELL"]:
                    logger.info(f"🧠 [BRAIN] PHÁT HIỆN TÍN HIỆU {sig_action} - {symbol}")
                    sl_p = sl - (atr_val * config.sl_atr_multiplier) if sig_action == "BUY" else sh + (atr_val * config.sl_atr_multiplier)
                    all_signals.append({"signal_id": str(uuid.uuid4()), "timestamp": time.time(), "symbol": symbol,
                                        "action": sig_action, "sl_price": round(sl_p, 5), "tp_price": 0.0,
                                        "bot_risk_percent": config.BOT_RISK_PERCENT, "signal_class": "ENTRY", "valid_for": 300})

            # Cơ chế AUTO-WAKEUP MT5
            if cycle_has_error:
                mt5_error_count += 1
                if mt5_error_count >= 3:
                    logger.warning("⚠️ [DAEMON] MT5 ngái ngủ (Timeout Data). Đang ép Wakeup...")
                    connector.shutdown()
                    time.sleep(2)
                    connector.connect()
                    mt5_error_count = 0
            else:
                mt5_error_count = 0

            sleep_sec = _get_sleep_time_to_next_candle(entry_tf)
            payload = {
                "brain_heartbeat": {
                    "status": "SLEEPING", 
                    "wakeup_time": time.time() + sleep_sec,
                    "active_symbols": active_symbols, 
                    "context": all_contexts 
                },
                "pending_signals": all_signals
            }
            with open(signal_file, "w", encoding="utf-8") as f: 
                json.dump(payload, f, indent=4)

            time.sleep(sleep_sec)

        except Exception as e:
            logger.error(f"[DAEMON] Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        run_daemon()
    except KeyboardInterrupt:
        logger.info("🛑 Daemon đã dừng bằng tay.")