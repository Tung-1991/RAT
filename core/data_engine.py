# -*- coding: utf-8 -*-
# FILE: core/data_engine.py
# V3.2: MULTI-TIMEFRAME DATA ENGINE & FAIL-SAFE CONTEXT (KAISER EDITION)

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
        """Tính toán ATR với cơ chế Fallback chống trả về 0.0"""
        if df.empty:
            return 0.0001 # Giá trị siêu nhỏ để tránh chia 0

        current_price = float(df['close'].iloc[-1])
        safe_fallback = current_price * 0.0005 # Fallback đệm: 0.05% giá hiện tại

        # Nếu không đủ nến để tính ATR, dùng biên độ nến trung bình của số nến hiện có
        if len(df) < period + 1:
            try:
                mean_range = (df['high'] - df['low']).mean()
                return float(mean_range) if mean_range > 0 else safe_fallback
            except:
                return safe_fallback
        
        try:
            high = df['high']
            low = df['low']
            close_prev = df['close'].shift(1)
            
            tr1 = high - low
            tr2 = (high - close_prev).abs()
            tr3 = (low - close_prev).abs()
            
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean().iloc[-1]
            
            if pd.isna(atr) or atr <= 0:
                return safe_fallback
            return float(atr)
        except:
            return safe_fallback

    def _calc_swings(self, df, lookback=10):
        """Tìm đỉnh/đáy gần nhất (Swing High/Low) với Fallback an toàn"""
        if df.empty:
            return 0.0, 0.0
            
        try:
            if len(df) < lookback:
                return float(df['high'].max()), float(df['low'].min())
                
            recent_df = df.tail(lookback)
            sh = float(recent_df['high'].max())
            sl = float(recent_df['low'].min())
            
            if pd.isna(sh) or pd.isna(sl):
                # Fallback: Râu nến của nến hiện tại
                return float(df['high'].iloc[-1]), float(df['low'].iloc[-1])
                
            return sh, sl
        except:
            current_close = float(df['close'].iloc[-1])
            return current_close * 1.001, current_close * 0.999 # Fake Swing nếu lỗi nặng

    def fetch_and_prepare(self, symbol):
        """
        Hàm cốt lõi: 
        1. Kéo Data đa khung (Entry & Trend).
        2. Sinh các mốc giá trị (Context) để phục vụ cho SL/TP.
        Trả về: df_entry, df_trend, context_dict (Đảm bảo 100% dữ liệu Float sạch)
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

        # 2. Xây dựng Context & Smart SL Points (Bọc an toàn)
        current_price = float(df_entry['close'].iloc[-1])
        
        # Tính ATR
        atr_entry = self._calc_atr(df_entry, period=14)
        atr_trend = self._calc_atr(df_trend, period=14)
        
        # Tính Swing
        swing_h_entry, swing_l_entry = self._calc_swings(df_entry, lookback=15)
        swing_h_trend, swing_l_trend = self._calc_swings(df_trend, lookback=15)
        
        # Tính Fibo 61.8% dựa trên sóng của khung Trend (H1/D1)
        wave_up_dist = swing_h_trend - swing_l_trend
        fibo_618_support = swing_h_trend - (wave_up_dist * 0.618)
        fibo_618_resistance = swing_l_trend + (wave_up_dist * 0.618)

        # ====== [FALLBACK] TREND EMA50 (Sẽ được ghi đè bởi G1 ở bot_daemon) ======
        try:
            ema50 = float(df_trend['close'].ewm(span=50, adjust=False).mean().iloc[-1])
            trend_status = "UP" if current_price > ema50 else "DOWN"
        except:
            trend_status = "NONE"
        # =================================================

        # Đóng gói toàn bộ vào Context (Ép chuẩn Float để tránh lỗi JSON Serialize)
        context = {
            "symbol": symbol,
            "current_price": float(current_price),
            "entry_timeframe": tf_entry,
            "trend_timeframe": tf_trend,
            "trend": trend_status, 
            
            # Smart SL Data Points
            "atr_entry": float(atr_entry),
            "atr_trend": float(atr_trend),
            "swing_high_entry": float(swing_h_entry),
            "swing_low_entry": float(swing_l_entry),
            "swing_high_trend": float(swing_h_trend),
            "swing_low_trend": float(swing_l_trend),
            "fibo_618_support": float(fibo_618_support),
            "fibo_618_resistance": float(fibo_618_resistance)
        }

        return df_entry, df_trend, context

# Singleton instance
data_engine = DataEngine()