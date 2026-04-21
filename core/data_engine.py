# -*- coding: utf-8 -*-
# FILE: core/data_engine.py
# V3.0: MULTI-TIMEFRAME DATA ENGINE & SMART SL CONTEXT (KAISER EDITION)

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import json
import os
import logging
import config

logger = logging.getLogger("DataEngine")

class DataEngine:
    def __init__(self):
        self.tf_map = {
            "1m": mt5.TIMEFRAME_M1,
            "5m": mt5.TIMEFRAME_M5,
            "15m": mt5.TIMEFRAME_M15,
            "30m": mt5.TIMEFRAME_M30,
            "1h": mt5.TIMEFRAME_H1,
            "4h": mt5.TIMEFRAME_H4,
            "1d": mt5.TIMEFRAME_D1
        }
        self.brain_path = "data/brain_settings.json"

    def _get_brain_settings(self):
        """Đọc cấu hình chiến thuật từ Brain Settings"""
        try:
            if os.path.exists(self.brain_path):
                with open(self.brain_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi đọc {self.brain_path}: {e}. Dùng default.")
            
        return {
            "trend_timeframe": getattr(config, "trend_timeframe", "1h"),
            "entry_timeframe": getattr(config, "entry_timeframe", "15m"),
            "NUM_H1_BARS": getattr(config, "NUM_H1_BARS", 100),
            "NUM_M15_BARS": getattr(config, "NUM_M15_BARS", 100)
        }

    def _fetch_bars(self, symbol, timeframe_str, num_bars):
        """Kéo dữ liệu nến từ MT5 và chuyển thành DataFrame"""
        tf = self.tf_map.get(timeframe_str.lower(), mt5.TIMEFRAME_M15)
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, num_bars)
        
        if rates is None or len(rates) == 0:
            logger.error(f"Không thể lấy dữ liệu {symbol} khung {timeframe_str}")
            return pd.DataFrame()
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def _calc_atr(self, df, period=14):
        """Tính toán Average True Range (ATR) nhanh cho Context"""
        if len(df) < period + 1:
            return 0.0
        
        high = df['high']
        low = df['low']
        close_prev = df['close'].shift(1)
        
        tr1 = high - low
        tr2 = (high - close_prev).abs()
        tr3 = (low - close_prev).abs()
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        return atr.iloc[-1]

    def _calc_swings(self, df, lookback=10):
        """Tìm đỉnh/đáy gần nhất trong N nến (Swing High/Low)"""
        if len(df) < lookback:
            return df['high'].max(), df['low'].min()
            
        recent_df = df.tail(lookback)
        return recent_df['high'].max(), recent_df['low'].min()

    def fetch_and_prepare(self, symbol):
        """
        Hàm cốt lõi: 
        1. Kéo Data đa khung (Entry & Trend).
        2. Sinh các mốc giá trị (Context) để phục vụ cho SL/TP.
        Trả về: df_entry, df_trend, context_dict
        """
        settings = self._get_brain_settings()
        tf_entry = settings.get("entry_timeframe", "15m")
        tf_trend = settings.get("trend_timeframe", "1h")
        num_entry = settings.get("NUM_M15_BARS", 100)
        num_trend = settings.get("NUM_H1_BARS", 100)

        # 1. Kéo DataFrame
        df_entry = self._fetch_bars(symbol, tf_entry, num_entry)
        df_trend = self._fetch_bars(symbol, tf_trend, num_trend)

        if df_entry.empty or df_trend.empty:
            return None, None, None

        # 2. Xây dựng Context & Smart SL Points
        current_price = df_entry['close'].iloc[-1]
        
        # Tính ATR
        atr_entry = self._calc_atr(df_entry, period=14)
        atr_trend = self._calc_atr(df_trend, period=14)
        
        # Tính Swing
        swing_h_entry, swing_l_entry = self._calc_swings(df_entry, lookback=15)
        swing_h_trend, swing_l_trend = self._calc_swings(df_trend, lookback=15)
        
        # Tính Fibo 61.8% dựa trên sóng của khung Trend (H1/D1)
        # Sóng Tăng (Để tìm Support cho lệnh Buy)
        wave_up_dist = swing_h_trend - swing_l_trend
        fibo_618_support = swing_h_trend - (wave_up_dist * 0.618)
        
        # Sóng Giảm (Để tìm Resistance cho lệnh Sell)
        fibo_618_resistance = swing_l_trend + (wave_up_dist * 0.618)

        # Đóng gói toàn bộ vào Context
        context = {
            "symbol": symbol,
            "current_price": current_price,
            "entry_timeframe": tf_entry,
            "trend_timeframe": tf_trend,
            
            # Smart SL Data Points
            "atr_entry": atr_entry,
            "atr_trend": atr_trend,
            "swing_high_entry": swing_h_entry,
            "swing_low_entry": swing_l_entry,
            "swing_high_trend": swing_h_trend,
            "swing_low_trend": swing_l_trend,
            "fibo_618_support": fibo_618_support,
            "fibo_618_resistance": fibo_618_resistance
        }

        return df_entry, df_trend, context

# Singleton instance
data_engine = DataEngine()