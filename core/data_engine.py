# -*- coding: utf-8 -*-
# FILE: core/data_engine.py
# V4.1: MULTI-TIMEFRAME DATA ENGINE & TA-LIB FIX (KAISER EDITION)

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import json
import os
import logging
import config
import pandas_ta as ta  # BỔ SUNG: Tính toán nhúng Indicator

logger = logging.getLogger("DataEngine")

class DataEngine:
    def __init__(self):
        self.tf_map = {
            "1m": mt5.TIMEFRAME_M1, "5m": mt5.TIMEFRAME_M5, "15m": mt5.TIMEFRAME_M15,
            "30m": mt5.TIMEFRAME_M30, "1h": mt5.TIMEFRAME_H1, "4h": mt5.TIMEFRAME_H4,
            "1d": mt5.TIMEFRAME_D1
        }
        self.brain_path = "data/brain_settings.json"

    def _get_brain_settings(self):
        try:
            if os.path.exists(self.brain_path):
                with open(self.brain_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi đọc {self.brain_path}: {e}. Dùng default.")
            
        return {
            "G0_TIMEFRAME": getattr(config, "G0_TIMEFRAME", "1d"),
            "G1_TIMEFRAME": getattr(config, "G1_TIMEFRAME", "1h"),
            "G2_TIMEFRAME": getattr(config, "G2_TIMEFRAME", "15m"),
            "G3_TIMEFRAME": getattr(config, "G3_TIMEFRAME", "15m"),
            "trend_timeframe": getattr(config, "trend_timeframe", "1h"),
            "entry_timeframe": getattr(config, "entry_timeframe", "15m"),
            "NUM_H1_BARS": getattr(config, "NUM_H1_BARS", 100),
            "NUM_M15_BARS": getattr(config, "NUM_M15_BARS", 100)
        }

    # =========================================================================
    # [FIX LỖI 2] HÀM SINH CỘT INDICATOR TỰ ĐỘNG BẰNG PANDAS-TA
    # =========================================================================
    def _apply_ta(self, df):
        if df is None or df.empty: 
            return df
        try:
            # 1. Indicator Cơ bản
            df.ta.adx(length=14, append=True)
            df.ta.ema(length=9, append=True)
            df.ta.ema(length=21, append=True)
            df.ta.ema(length=50, append=True)
            df.ta.rsi(length=14, append=True)
            df.ta.macd(fast=12, slow=26, signal=9, append=True)
            df.ta.bbands(length=20, std=2.0, append=True)
            df.ta.supertrend(length=10, multiplier=3.0, append=True)
            df.ta.stoch(k=14, d=3, smooth_k=3, append=True)
            df.ta.psar(af0=0.02, af=0.02, max_af=0.2, append=True)
            
            # 2. Logic Nến Nhật thủ công (Chống spam TA-Lib)
            O, H, L, C = df['open'], df['high'], df['low'], df['close']
            body = (C - O).abs()
            upper_shadow = H - df[['open', 'close']].max(axis=1)
            lower_shadow = df[['open', 'close']].min(axis=1) - L
            
            df["CDL_ENGULFING"] = np.where((C > O) & (C.shift(1) < O.shift(1)) & (C > O.shift(1)) & (O < C.shift(1)), 100,
                                  np.where((C < O) & (C.shift(1) > O.shift(1)) & (C < O.shift(1)) & (O > C.shift(1)), -100, 0))
            df["CDL_HAMMER"] = np.where((lower_shadow > 2 * body) & (upper_shadow < 0.2 * body) & (C > O), 100, 0)
            df["CDL_SHOOTINGSTAR"] = np.where((upper_shadow > 2 * body) & (lower_shadow < 0.2 * body) & (C < O), -100, 0)
            df["CDL_MORNINGSTAR"] = np.where((C.shift(2) < O.shift(2)) & (body.shift(1) < body.shift(2)*0.3) & (C > O) & (C > O.shift(2) + body.shift(2)/2), 100, 0)
            df["CDL_EVENINGSTAR"] = np.where((C.shift(2) > O.shift(2)) & (body.shift(1) < body.shift(2)*0.3) & (C < O) & (C < O.shift(2) - body.shift(2)/2), -100, 0)
            
        except Exception as e:
            logger.error(f"Lỗi tính toán thư viện pandas-ta: {e}")
            
        return df

    def _fetch_bars(self, symbol, timeframe_val, num_bars):
        # =========================================================================
        # [FIX LỖI 1] ÉP KIỂU THÔNG MINH CHO ĐA KHUNG (XỬ LÝ CẢ INT LẪN STR)
        # =========================================================================
        if isinstance(timeframe_val, int):
            tf = timeframe_val
        else:
            tf = self.tf_map.get(str(timeframe_val).lower(), mt5.TIMEFRAME_M15)
            
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, num_bars)
        
        if rates is None or len(rates) == 0:
            return pd.DataFrame()
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Áp dụng tính toán toàn bộ Indicator trước khi trả Data về cho SignalGenerator
        df = self._apply_ta(df)
        
        return df

    def _calc_atr(self, df, period=14):
        if df.empty: return 0.0001
        current_price = float(df['close'].iloc[-1])
        safe_fallback = current_price * 0.0005 

        if len(df) < period + 1:
            try:
                mean_range = (df['high'] - df['low']).mean()
                return float(mean_range) if mean_range > 0 else safe_fallback
            except:
                return safe_fallback
        try:
            high, low, close_prev = df['high'], df['low'], df['close'].shift(1)
            tr = pd.concat([high - low, (high - close_prev).abs(), (low - close_prev).abs()], axis=1).max(axis=1)
            atr = tr.rolling(window=period).mean().iloc[-1]
            return safe_fallback if pd.isna(atr) or atr <= 0 else float(atr)
        except:
            return safe_fallback

    def _calc_swings(self, df, lookback=10):
        if df.empty: return 0.0, 0.0
        try:
            if len(df) < lookback: return float(df['high'].max()), float(df['low'].min())
            recent_df = df.tail(lookback)
            sh, sl = float(recent_df['high'].max()), float(recent_df['low'].min())
            if pd.isna(sh) or pd.isna(sl): return float(df['high'].iloc[-1]), float(df['low'].iloc[-1])
            return sh, sl
        except:
            current_close = float(df['close'].iloc[-1])
            return current_close * 1.001, current_close * 0.999 

    def fetch_data_v4(self, symbol):
        """Kéo độc lập 4 chuỗi dữ liệu cho G0, G1, G2, G3"""
        settings = self._get_brain_settings()
        
        tfs = {
            "G0": settings.get("G0_TIMEFRAME", getattr(config, "G0_TIMEFRAME", "1d")),
            "G1": settings.get("G1_TIMEFRAME", getattr(config, "G1_TIMEFRAME", "1h")),
            "G2": settings.get("G2_TIMEFRAME", getattr(config, "G2_TIMEFRAME", "15m")),
            "G3": settings.get("G3_TIMEFRAME", getattr(config, "G3_TIMEFRAME", "15m"))
        }
        
        num_bars = settings.get("NUM_H1_BARS", 100)
        
        dfs = {grp: self._fetch_bars(symbol, tf, num_bars) for grp, tf in tfs.items()}
        
        if any(df.empty for df in dfs.values()):
            return None, None

        df_entry = dfs["G2"]
        df_trend = dfs["G1"]
        current_price = float(df_entry['close'].iloc[-1])
        
        swing_h_entry, swing_l_entry = self._calc_swings(df_entry, lookback=15)
        swing_h_trend, swing_l_trend = self._calc_swings(df_trend, lookback=15)
        wave_up_dist = swing_h_trend - swing_l_trend

        context = {
            "symbol": symbol,
            "current_price": current_price,
            "atr_entry": self._calc_atr(df_entry, period=14),
            "atr_trend": self._calc_atr(df_trend, period=14),
            "swing_high_entry": float(swing_h_entry),
            "swing_low_entry": float(swing_l_entry),
            "swing_high_trend": float(swing_h_trend),
            "swing_low_trend": float(swing_l_trend),
            "fibo_618_support": float(swing_h_trend - (wave_up_dist * 0.618)),
            "fibo_618_resistance": float(swing_l_trend + (wave_up_dist * 0.618))
        }

        return dfs, context

    def fetch_and_prepare(self, symbol):
        """HÀM CŨ: Phục vụ chạy Bot Daemon bản cũ tránh crash"""
        settings = self._get_brain_settings()
        tf_entry = settings.get("entry_timeframe", "15m")
        tf_trend = settings.get("trend_timeframe", "1h")
        num_entry = settings.get("NUM_M15_BARS", 100)
        num_trend = settings.get("NUM_H1_BARS", 100)

        df_entry = self._fetch_bars(symbol, tf_entry, num_entry)
        df_trend = self._fetch_bars(symbol, tf_trend, num_trend)

        if df_entry.empty or df_trend.empty:
            return None, None, None

        current_price = float(df_entry['close'].iloc[-1])
        atr_entry = self._calc_atr(df_entry, period=14)
        atr_trend = self._calc_atr(df_trend, period=14)
        swing_h_entry, swing_l_entry = self._calc_swings(df_entry, lookback=15)
        swing_h_trend, swing_l_trend = self._calc_swings(df_trend, lookback=15)
        
        wave_up_dist = swing_h_trend - swing_l_trend
        fibo_618_support = swing_h_trend - (wave_up_dist * 0.618)
        fibo_618_resistance = swing_l_trend + (wave_up_dist * 0.618)

        try:
            ema50 = float(df_trend['close'].ewm(span=50, adjust=False).mean().iloc[-1])
            trend_status = "UP" if current_price > ema50 else "DOWN"
        except:
            trend_status = "NONE"

        context = {
            "symbol": symbol, "current_price": float(current_price),
            "entry_timeframe": tf_entry, "trend_timeframe": tf_trend,
            "trend": trend_status, "atr_entry": float(atr_entry), "atr_trend": float(atr_trend),
            "swing_high_entry": float(swing_h_entry), "swing_low_entry": float(swing_l_entry),
            "swing_high_trend": float(swing_h_trend), "swing_low_trend": float(swing_l_trend),
            "fibo_618_support": float(fibo_618_support), "fibo_618_resistance": float(fibo_618_resistance)
        }

        return df_entry, df_trend, context

data_engine = DataEngine()