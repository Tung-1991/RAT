# -*- coding: utf-8 -*-
import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    """
    V3.0: MACD Signal.
    Dựa trên giao cắt giữa MACD Line và Signal Line (MACDs).
    """
    fast = params.get("fast", 12)
    slow = params.get("slow", 26)
    signal = params.get("signal", 9)
    
    # Tên cột mặc định của pandas_ta: MACD_12_26_9, MACDs_12_26_9, MACDh_12_26_9
    col_macd = f"MACD_{fast}_{slow}_{signal}"
    col_signal = f"MACDs_{fast}_{slow}_{signal}"
    
    if col_macd not in df.columns or col_signal not in df.columns or len(df) < 2:
        return 0

    curr_macd = df[col_macd].iloc[-1]
    curr_sig = df[col_signal].iloc[-1]
    prev_macd = df[col_macd].iloc[-2]
    prev_sig = df[col_signal].iloc[-2]

    # MACD cắt lên Signal Line -> Buy
    if prev_macd <= prev_sig and curr_macd > curr_sig:
        return 1
    # MACD cắt xuống Signal Line -> Sell
    if prev_macd >= prev_sig and curr_macd < curr_sig:
        return -1
        
    return 0