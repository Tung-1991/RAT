# -*- coding: utf-8 -*-
# FILE: core/data_engine.py
# V3.0: UNIFIED DATA ENGINE - DYNAMIC PAYLOAD (KAISER EDITION)

import pandas as pd
import pandas_ta as ta
import logging

logger = logging.getLogger("ExnessBot")

class DataEngine:
    def __init__(self, connector):
        self.connector = connector

    def fetch_and_prepare(self, symbol: str, brain_config: dict) -> dict:
        """
        V3.0: Trạm bơm dữ liệu trung tâm.
        Lấy thông số tính toán trực tiếp từ `brain_config` (Single Source of Truth).
        """
        # 1. Trích xuất cấu hình khung thời gian
        tf_radar = brain_config.get("trend_timeframe", "1h")
        tf_trigger = brain_config.get("entry_timeframe", "15m")
        num_bars_radar = brain_config.get("NUM_H1_BARS", 100)
        num_bars_trigger = brain_config.get("NUM_M15_BARS", 100)

        # 2. Lấy dữ liệu từ Exness
        df_radar = self.connector.get_historical_data(symbol, tf_radar, num_bars_radar)
        df_trigger = self.connector.get_historical_data(symbol, tf_trigger, num_bars_trigger)

        if df_radar is None or df_trigger is None or df_radar.empty or df_trigger.empty:
            logger.error(f"[DataEngine] Failed to fetch data for {symbol}")
            return {}

        # 3. Phân tách Context (H1) và Payload (M15)
        inds_config = brain_config.get("indicators", {})
        context_data = self._build_context(df_radar, inds_config)
        data_payload = self._build_payload(df_trigger, inds_config)

        return {
            "context": context_data,
            "payload": data_payload,
            "raw_radar": df_radar,
            "raw_trigger": df_trigger
        }

    def _build_context(self, df: pd.DataFrame, inds_config: dict) -> dict:
        """
        Khung Radar (H1) - Xác định Trạng thái thị trường tổng thể.
        Chứa: Swing Points, ATR, và Trend Bias.
        """
        df = df.copy()
        
        # Lấy Params từ cấu hình (Nếu không có thì dùng default dự phòng)
        atr_period = inds_config.get("atr", {}).get("params", {}).get("period", 14)
        ema_period = inds_config.get("ema", {}).get("params", {}).get("period", 50)
        swing_period = inds_config.get("swing_point", {}).get("params", {}).get("period", 5)

        # 1. Tính ATR khung H1
        atr_series = df.ta.atr(length=atr_period)
        atr_val = atr_series.iloc[-1] if atr_series is not None else 0.0
        
        # 2. Tính Trend Bias (Price vs EMA)
        ema_series = df.ta.ema(length=ema_period)
        ema_val = ema_series.iloc[-1] if ema_series is not None else df['close'].iloc[-1]
        trend_status = "UP" if df['close'].iloc[-1] > ema_val else "DOWN"
        
        # 3. Tính Exhaustion Flag (Quá xa EMA)
        dist_to_ema = abs(df['close'].iloc[-1] - ema_val) / ema_val if ema_val > 0 else 0
        exhaustion_flag = dist_to_ema > 0.02  # Có thể cấu hình sau
        
        # 4. Tìm Swing Points (Fractal)
        swing_h, swing_l = self._get_swing_points(df, swing_period)

        return {
            "atr": atr_val,
            "trend": trend_status,
            "swing_high": swing_h,
            "swing_low": swing_l,
            "exhaustion_flag": exhaustion_flag
        }

    def _build_payload(self, df: pd.DataFrame, inds_config: dict) -> pd.DataFrame:
        """
        Khung Trigger (M15) - Tính toán Toàn bộ Chỉ báo Kỹ thuật.
        Đảm bảo tên cột khớp 100% với Signal Logic.
        """
        df = df.copy()
        
        # --- NHÓM 1: XU HƯỚNG & ĐỘNG LƯỢNG (TREND/MOMENTUM) ---
        
        # 1. EMA Single (Xác nhận cản M15)
        if "ema" in inds_config:
            p = inds_config["ema"]["params"].get("period", 50)
            df.ta.ema(length=p, append=True)
            
        # 2. EMA Cross
        if "ema_cross" in inds_config:
            fast = inds_config["ema_cross"]["params"].get("fast", 9)
            slow = inds_config["ema_cross"]["params"].get("slow", 21)
            df.ta.ema(length=fast, append=True)
            df.ta.ema(length=slow, append=True)
            
        # 3. MACD
        if "macd" in inds_config:
            f = inds_config["macd"]["params"].get("fast", 12)
            s = inds_config["macd"]["params"].get("slow", 26)
            sig = inds_config["macd"]["params"].get("signal", 9)
            df.ta.macd(fast=f, slow=s, signal=sig, append=True)
            
        # 4. RSI
        if "rsi" in inds_config:
            p = inds_config["rsi"]["params"].get("period", 14)
            df.ta.rsi(length=p, append=True)
            
        # 5. Supertrend
        if "supertrend" in inds_config:
            p = inds_config["supertrend"]["params"].get("period", 10)
            m = inds_config["supertrend"]["params"].get("multiplier", 3.0)
            df.ta.supertrend(length=p, multiplier=m, append=True)
            
        # 6. ADX
        if "adx" in inds_config:
            p = inds_config["adx"]["params"].get("period", 14)
            df.ta.adx(length=p, append=True)
            
        # 7. Parabolic SAR (PSAR)
        if "psar" in inds_config:
            step = inds_config["psar"]["params"].get("step", 0.02)
            max_step = inds_config["psar"]["params"].get("max_step", 0.2)
            df.ta.psar(af=step, max_af=max_step, append=True)

        # --- NHÓM 2: BIẾN ĐỘNG & ĐẢO CHIỀU (VOLATILITY/REVERSAL) ---
        
        # 8. Bollinger Bands
        if "bollinger_bands" in inds_config:
            p = inds_config["bollinger_bands"]["params"].get("period", 20)
            std = inds_config["bollinger_bands"]["params"].get("std_dev", 2.0)
            df.ta.bbands(length=p, std=std, append=True)
            
        # 9. Stochastic
        if "stochastic" in inds_config:
            k = inds_config["stochastic"]["params"].get("k", 14)
            d = inds_config["stochastic"]["params"].get("d", 3)
            sm = inds_config["stochastic"]["params"].get("smooth", 3)
            df.ta.stoch(k=k, d=d, smooth_k=sm, append=True)
            
        # 10. ATR (Trigger)
        if "atr" in inds_config:
            p = inds_config["atr"]["params"].get("period", 14)
            df.ta.atr(length=p, append=True)
            
        # --- NHÓM 3: MẪU HÌNH & HÀNH VI GIÁ (PRICE ACTION) ---
        
        # 11. Cụm Nến Đảo Chiều Đơn (Candle Patterns)
        if "candle" in inds_config or "multi_candle" in inds_config:
            # Tính một số mẫu nến cơ bản để tối ưu hiệu năng
            df.ta.cdl_pattern(name=["engulfing", "hammer", "shootingstar", "morningstar", "eveningstar"], append=True)
            
        # 12. Pivot Points (Tính thủ công cho khung M15)
        if "pivot_points" in inds_config:
            high, low, close = df['high'].shift(1), df['low'].shift(1), df['close'].shift(1)
            df['PP'] = (high + low + close) / 3
            df['R1'] = (2 * df['PP']) - low
            df['S1'] = (2 * df['PP']) - high
            df['R2'] = df['PP'] + (high - low)
            df['S2'] = df['PP'] - (high - low)

        # Xử lý dọn dẹp các ô NaN sinh ra do độ trễ của các chỉ báo (Ví dụ MA 200 cần 200 nến mới có data)
        df.fillna(0, inplace=True)
        
        return df

    def _get_swing_points(self, df: pd.DataFrame, period: int):
        """
        Tìm Fractal Swing Points.
        (Đỉnh/đáy cao/thấp nhất trong một khoảng n=period)
        """
        if len(df) < period: 
            return 0.0, 0.0
            
        n = (period - 1) // 2
        highs, lows = df['high'].values, df['low'].values
        sh, sl = 0.0, 0.0
        
        for i in range(len(df) - 1 - n, n - 1, -1):
            win_h = highs[i-n : i+n+1]
            win_l = lows[i-n : i+n+1]
            
            # Ghi nhận Swing High đầu tiên thỏa mãn
            if sh == 0.0 and highs[i] == win_h.max(): 
                sh = highs[i]
            # Ghi nhận Swing Low đầu tiên thỏa mãn
            if sl == 0.0 and lows[i] == win_l.min(): 
                sl = lows[i]
                
            # Đã tìm đủ 1 cặp Đỉnh - Đáy gần nhất thì thoát
            if sh != 0.0 and sl != 0.0: 
                break
                
        return sh, sl