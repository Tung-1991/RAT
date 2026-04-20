# -*- coding: utf-8 -*-
import pandas as pd
import pandas_ta as ta
import logging

logger = logging.getLogger("ExnessBot")

class DataEngine:
    def __init__(self, connector):
        self.connector = connector

    def fetch_and_prepare(self, symbol: str, config: dict) -> dict:
        """
        V3.0: Trạm bơm dữ liệu trung tâm.
        Tính toán toàn bộ 15+ chỉ báo để phục vụ các khối Lego Signal.
        """
        tf_radar = config.get("trend_timeframe", "1h")
        tf_trigger = config.get("entry_timeframe", "15m")
        num_bars_radar = config.get("NUM_H1_BARS", 100) # Tăng lên để đủ tính EMA200
        num_bars_trigger = config.get("NUM_M15_BARS", 100)

        df_radar = self.connector.get_historical_data(symbol, tf_radar, num_bars_radar)
        df_trigger = self.connector.get_historical_data(symbol, tf_trigger, num_bars_trigger)

        if df_radar is None or df_trigger is None or df_radar.empty or df_trigger.empty:
            logger.error(f"Failed to fetch data for {symbol}")
            return {}

        # 1. Xử lý khung Radar (H1) - Lấy Context
        context_data = self._build_context(df_radar, config)
        
        # 2. Xử lý khung Trigger (M15) - Tính toán Full Indicators cho Payload
        data_payload = self._build_payload(df_trigger, config)

        return {
            "context": context_data,
            "payload": data_payload,
            "raw_radar": df_radar,
            "raw_trigger": df_trigger
        }

    def _build_context(self, df: pd.DataFrame, config: dict) -> dict:
        """Xác định trạng thái thị trường tổng thể (Radar)"""
        df = df.copy()
        
        # Tính toán các chỉ báo cốt lõi cho Radar
        adx_period = config.get("ADX_PERIOD", 14)
        atr_period = config.get("atr_period", 14)
        ema_trend_period = config.get("TREND_EMA_PERIOD", 50)

        # ADX & DMI
        adx_df = df.ta.adx(length=adx_period)
        adx_val = adx_df[f"ADX_{adx_period}"].iloc[-1] if adx_df is not None else 0
        
        # ATR
        atr_series = df.ta.atr(length=atr_period)
        atr_val = atr_series.iloc[-1] if atr_series is not None else 0
        
        # Trend Bias (Price vs EMA)
        ema_series = df.ta.ema(length=ema_trend_period)
        ema_val = ema_series.iloc[-1] if ema_series is not None else df['close'].iloc[-1]
        
        # Exhaustion (Giá quá xa EMA)
        dist_to_ema = abs(df['close'].iloc[-1] - ema_val) / ema_val if ema_val > 0 else 0
        exhaustion_flag = dist_to_ema > config.get("exhaustion_threshold", 0.02)

        # Swing Points (Đỉnh đáy Radar)
        swing_h, swing_l = self._get_swing_points(df, config.get("swing_period", 5))

        return {
            "adx": adx_val,
            "trend": "UP" if df['close'].iloc[-1] > ema_val else "DOWN",
            "swing_high": swing_h,
            "swing_low": swing_l,
            "atr": atr_val,
            "exhaustion_flag": exhaustion_flag
        }

    def _build_payload(self, df: pd.DataFrame, config: dict) -> pd.DataFrame:
        """Bơm toàn bộ Indicators vào khung Trigger (M15)"""
        df = df.copy()
        
        # Nhóm 1: Xu hướng & Động lượng (Trend/Momentum)
        df.ta.ema(length=config.get("EMA_FAST", 9), append=True)
        df.ta.ema(length=config.get("EMA_SLOW", 21), append=True)
        df.ta.ema(length=200, append=True)
        df.ta.macd(fast=12, slow=26, signal=9, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.supertrend(period=10, multiplier=3.0, append=True)
        
        # Nhóm 2: Biến động & Đảo chiều (Volatility/Reversal)
        df.ta.bbands(length=20, std=2.0, append=True)
        df.ta.stoch(k=14, d=3, smooth_k=3, append=True)
        df.ta.psar(af=0.02, max_af=0.2, append=True)
        df.ta.atr(length=14, append=True)
        df.ta.adx(length=14, append=True)
        
        # Nhóm 3: Mô hình nến (Candle Patterns) - Chỉ lấy các mẫu mạnh
        df.ta.cdl_pattern(name=["engulfing", "hammer", "shootingstar", "morningstar", "eveningstar"], append=True)
        
        # Nhóm 4: Pivot Points (Tính thủ công vì pandas_ta cần dữ liệu nến ngày)
        # Giả định đơn giản cho Pivot nội trong khung nến hiện tại
        high, low, close = df['high'].shift(1), df['low'].shift(1), df['close'].shift(1)
        df['PP'] = (high + low + close) / 3
        df['R1'] = (2 * df['PP']) - low
        df['S1'] = (2 * df['PP']) - high
        
        # Làm sạch dữ liệu NaN do độ trễ của các chỉ báo
        df.fillna(0, inplace=True)
        
        return df

    def _get_swing_points(self, df: pd.DataFrame, period: int):
        """Logic tìm Fractal Swing Points (Giữ nguyên từ V8.4 của Ngài)"""
        if len(df) < period: return 0.0, 0.0
        n = (period - 1) // 2
        highs, lows = df['high'].values, df['low'].values
        sh, sl = 0.0, 0.0
        
        for i in range(len(df) - 1 - n, n - 1, -1):
            win_h = highs[i-n : i+n+1]
            win_l = lows[i-n : i+n+1]
            if sh == 0.0 and highs[i] == win_h.max(): sh = highs[i]
            if sl == 0.0 and lows[i] == win_l.min(): sl = lows[i]
            if sh != 0.0 and sl != 0.0: break
        return sh, sl