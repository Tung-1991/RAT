# -*- coding: utf-8 -*-
# FILE: bot_daemon.py
# V6.8: SILENT MODE & CANDLE SYNC (KAISER EDITION)

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
    """Tính thời gian ngủ tới giây thứ 2 của nến tiếp theo (Đồng bộ sàn)"""
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

def run_daemon():
    logger.info("--- ⚙️ DAEMON V6.8: SILENT & CANDLE SYNC (KAISER EDITION) ---")
    connector = ExnessConnector()
    if not connector.connect(): return

    signal_file = os.path.join(config.DATA_DIR, "live_signals.json")

    while True:
        try:
            active_symbols = getattr(config, "BOT_ACTIVE_SYMBOLS", [])
            ui_symbol = getattr(config, "UI_ACTIVE_SYMBOL", config.DEFAULT_SYMBOL)
            entry_tf = getattr(config, "entry_timeframe", "15m")
            
            all_signals = []
            market_context_ui = {}

            # QUÉT TÍN HIỆU
            for symbol in active_symbols:
                df_h1 = connector.get_historical_data(symbol, config.trend_timeframe, config.NUM_H1_BARS)
                df_m15 = connector.get_historical_data(symbol, entry_tf, config.NUM_M15_BARS)
                
                if df_h1 is None or df_m15 is None or df_m15.empty: continue

                # 1. Tính toán tín hiệu
                sig_action = sg_module.get_signal(df_h1, df_m15, config.__dict__) if sg_module else None
                
                # 2. Lấy Swing/ATR (Cập nhật Dashboard cho đồng đang xem trên UI)
                atr_val, sh, sl = 0.0, 0.0, 0.0
                atr_series = calculate_atr(df_m15, config.atr_period)
                if atr_series is not None: atr_val = round(atr_series.iloc[-1], 5)
                
                res_h, res_l = get_swing_high_low(df_m15, config.__dict__)
                sh, sl = (round(res_h, 5) if res_h else 0.0), (round(res_l, 5) if res_l else 0.0)

                if symbol == ui_symbol:
                    ema_v = df_h1['close'].ewm(span=config.TREND_EMA_PERIOD, adjust=False).mean().iloc[-1]
                    market_context_ui = {"trend": "UP" if df_h1['close'].iloc[-1] > ema_v else "DOWN",
                                         "swing_high": sh, "swing_low": sl, "atr": atr_val}

                if sig_action in ["BUY", "SELL"]:
                    logger.info(f"🧠 [BRAIN] PHÁT HIỆN TÍN HIỆU {sig_action} - {symbol}")
                    sl_p = sl - (atr_val * config.sl_atr_multiplier) if sig_action == "BUY" else sh + (atr_val * config.sl_atr_multiplier)
                    all_signals.append({"signal_id": str(uuid.uuid4()), "timestamp": time.time(), "symbol": symbol,
                                        "action": sig_action, "sl_price": round(sl_p, 5), "tp_price": 0.0,
                                        "bot_risk_percent": config.BOT_RISK_PERCENT, "signal_class": "ENTRY", "valid_for": 300})

            # GHI HEARTBEAT ĐỂ UI GIỮ TRẠNG THÁI ONLINE VÀ ĐẾM NGƯỢC
            sleep_sec = _get_sleep_time_to_next_candle(entry_tf)
            payload = {
                "brain_heartbeat": {
                    "status": "SLEEPING", 
                    "wakeup_time": time.time() + sleep_sec, # Trả về timestamp thức dậy
                    "active_symbols": active_symbols, 
                    "context": market_context_ui
                },
                "pending_signals": all_signals
            }
            with open(signal_file, "w") as f: json.dump(payload, f, indent=4)

            # NGỦ ĐẾN NẾN TIẾP THEO
            time.sleep(sleep_sec)

        except Exception as e:
            logger.error(f"[DAEMON] Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        run_daemon()
    except KeyboardInterrupt:
        logger.info("🛑 Daemon đã dừng bằng tay.")