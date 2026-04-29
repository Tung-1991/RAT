# -*- coding: utf-8 -*-
# FILE: core/data_engine.py
# V4.2.1: DYNAMIC TA OPTIMIZATION & MULTI-TIMEFRAME (KAISER EDITION)

import MetaTrader5 as mt5
import pandas as pd
import numpy as np
import json
import os
import logging
import config
import pandas_ta as ta 

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
            "NUM_M15_BARS": getattr(config, "NUM_M15_BARS", 100),
            "indicators": getattr(config, "SANDBOX_CONFIG", {}).get("indicators", {})
        }

    # =========================================================================
    # [TỐI ƯU CPU] CHỈ TÍNH TOÁN CÁC INDICATOR ĐƯỢC BẬT (ON)
    # =========================================================================
    def _apply_ta(self, df, inds_config, tsl_config=None):
        if df is None or df.empty: 
            return df
        try:
            # ADX
            if inds_config.get("adx", {}).get("active"):
                p = int(inds_config["adx"].get("params", {}).get("period", 14))
                df.ta.adx(length=p, append=True)
            
            # EMA Cơ bản
            if inds_config.get("ema", {}).get("active"):
                p = int(inds_config["ema"].get("params", {}).get("period", 50))
                df.ta.ema(length=p, append=True)
            
            # EMA Cross (Cần 2 đường EMA)
            if inds_config.get("ema_cross", {}).get("active"):
                f = int(inds_config["ema_cross"].get("params", {}).get("fast", 9))
                s = int(inds_config["ema_cross"].get("params", {}).get("slow", 21))
                df.ta.ema(length=f, append=True)
                df.ta.ema(length=s, append=True)
            
            # RSI
            if inds_config.get("rsi", {}).get("active"):
                p = int(inds_config["rsi"].get("params", {}).get("period", 14))
                df.ta.rsi(length=p, append=True)
            
            # MACD
            if inds_config.get("macd", {}).get("active"):
                f = int(inds_config["macd"].get("params", {}).get("fast", 12))
                s = int(inds_config["macd"].get("params", {}).get("slow", 26))
                sig = int(inds_config["macd"].get("params", {}).get("signal", 9))
                df.ta.macd(fast=f, slow=s, signal=sig, append=True)
            
            # Bollinger Bands
            if inds_config.get("bollinger_bands", {}).get("active"):
                p = int(inds_config["bollinger_bands"].get("params", {}).get("period", 20))
                std = float(inds_config["bollinger_bands"].get("params", {}).get("std_dev", 2.0))
                df.ta.bbands(length=p, std=std, append=True)
            
            # Supertrend
            if inds_config.get("supertrend", {}).get("active"):
                p = int(inds_config["supertrend"].get("params", {}).get("period", 10))
                m = float(inds_config["supertrend"].get("params", {}).get("multiplier", 3.0))
                df.ta.supertrend(length=p, multiplier=m, append=True)
            
            # Stochastic
            if inds_config.get("stochastic", {}).get("active"):
                k = int(inds_config["stochastic"].get("params", {}).get("k", 14))
                d = int(inds_config["stochastic"].get("params", {}).get("d", 3))
                sm = int(inds_config["stochastic"].get("params", {}).get("smooth", 3))
                df.ta.stoch(k=k, d=d, smooth_k=sm, append=True)
            
            # Parabolic SAR
            if inds_config.get("psar", {}).get("active") or (tsl_config and "PSAR_STEP" in tsl_config):
                # Ưu tiên thông số từ TSL Config nếu có
                step = 0.02
                max_step = 0.2
                if tsl_config and "PSAR_STEP" in tsl_config:
                    step = float(tsl_config["PSAR_STEP"])
                    max_step = float(tsl_config["PSAR_MAX"])
                elif inds_config.get("psar"):
                    step = float(inds_config["psar"].get("params", {}).get("step", 0.02))
                    max_step = float(inds_config["psar"].get("params", {}).get("max_step", 0.2))
                
                df.ta.psar(af0=step, af=step, max_af=max_step, append=True)

            # Pivot Points (Standard Floor)
            if inds_config.get("pivot_points", {}).get("active"):
                prev_h = df['high'].shift(1)
                prev_l = df['low'].shift(1)
                prev_c = df['close'].shift(1)
                df['PP'] = (prev_h + prev_l + prev_c) / 3
                df['R1'] = (2 * df['PP']) - prev_l
                df['S1'] = (2 * df['PP']) - prev_h

            # ATR
            if inds_config.get("atr", {}).get("active"):
                p = int(inds_config["atr"].get("params", {}).get("period", 14))
                df.ta.atr(length=p, append=True)
            
            # Nến Nhật
            is_candle_active = inds_config.get("candle", {}).get("active")
            is_mc_active = inds_config.get("multi_candle", {}).get("active")
            if is_candle_active or is_mc_active:
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

    def _fetch_bars(self, symbol, timeframe_val, num_bars, inds_config, tsl_config=None):
        if isinstance(timeframe_val, int):
            tf = timeframe_val
        else:
            tf = self.tf_map.get(str(timeframe_val).lower(), mt5.TIMEFRAME_M15)
            
        rates = mt5.copy_rates_from_pos(symbol, tf, 0, num_bars)
        
        if rates is None or len(rates) == 0:
            return pd.DataFrame()
            
        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        
        # Chỉ tính những Indicator đang bật
        df = self._apply_ta(df, inds_config, tsl_config)
        
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
        """Kéo độc lập 4 chuỗi dữ liệu cho G0, G1, G2, G3 và tính Cản/ATR cho tất cả"""
        settings = self._get_brain_settings()
        inds_config = settings.get("indicators", {})
        tsl_config = settings.get("tsl_config", getattr(config, "TSL_CONFIG", {}))
        
        tfs = {
            "G0": settings.get("G0_TIMEFRAME", getattr(config, "G0_TIMEFRAME", "1d")),
            "G1": settings.get("G1_TIMEFRAME", getattr(config, "G1_TIMEFRAME", "1h")),
            "G2": settings.get("G2_TIMEFRAME", getattr(config, "G2_TIMEFRAME", "15m")),
            "G3": settings.get("G3_TIMEFRAME", getattr(config, "G3_TIMEFRAME", "15m"))
        }
        
        num_bars = settings.get("NUM_H1_BARS", 100)
        
        # Truyền cấu hình Indicator và TSL vào để lọc
        dfs = {grp: self._fetch_bars(symbol, tf, num_bars, inds_config, tsl_config) for grp, tf in tfs.items()}
        
        if any(df.empty for df in dfs.values()):
            return None, None

        current_price = float(dfs["G2"]['close'].iloc[-1])
        
        context = {
            "symbol": symbol,
            "current_price": current_price
        }

        # [NEW V4.4 FINAL] Lấy giá trị PSAR hiện tại cho TSL PSAR_TRAIL
        try:
            tsl_cfg = settings.get("tsl_config", getattr(config, "TSL_CONFIG", {}))
            psar_grp = tsl_cfg.get("PSAR_GROUP", "G2")
            if psar_grp not in dfs: psar_grp = "G2"
            
            df_psar = dfs[psar_grp]
            psar_cols = [c for c in df_psar.columns if c.startswith("PSARl_") or c.startswith("PSARs_")]
            for col in psar_cols:
                val = df_psar[col].iloc[-1]
                if not pd.isna(val):
                    context["psar"] = float(val)
                    break
        except Exception:
            pass

        for grp in ["G0", "G1", "G2", "G3"]:
            df_grp = dfs[grp]
            sh, sl = self._calc_swings(df_grp, lookback=15)
            atr = self._calc_atr(df_grp, period=14)
            
            context[f"swing_high_{grp}"] = float(sh)
            context[f"swing_low_{grp}"] = float(sl)
            context[f"atr_{grp}"] = float(atr)

        context["atr_entry"] = context["atr_G2"]
        context["atr_trend"] = context["atr_G1"]
        context["swing_high_entry"] = context["swing_high_G2"]
        context["swing_low_entry"] = context["swing_low_G2"]
        context["swing_high_trend"] = context["swing_high_G1"]
        context["swing_low_trend"] = context["swing_low_G1"]

        return dfs, context

    def fetch_and_prepare(self, symbol):
        """HÀM CŨ: Phục vụ chạy Bot Daemon bản cũ tránh crash"""
        settings = self._get_brain_settings()
        inds_config = settings.get("indicators", {})
        tsl_config = settings.get("tsl_config", getattr(config, "TSL_CONFIG", {}))
        
        tf_entry = settings.get("entry_timeframe", "15m")
        tf_trend = settings.get("trend_timeframe", "1h")
        num_entry = settings.get("NUM_M15_BARS", 100)
        num_trend = settings.get("NUM_H1_BARS", 100)

        df_entry = self._fetch_bars(symbol, tf_entry, num_entry, inds_config, tsl_config)
        df_trend = self._fetch_bars(symbol, tf_trend, num_trend, inds_config, tsl_config)

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