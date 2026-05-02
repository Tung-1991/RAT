# -*- coding: utf-8 -*-
import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict, context: dict = None) -> int:
    if df is None or len(df) < 2:
        return 0
        
    current_close = df['close'].iloc[-1]
    prev_high = df['high'].iloc[-2]
    prev_low = df['low'].iloc[-2]
    
    if current_close > prev_high:
        return 1
    if current_close < prev_low:
        return -1
        
    return 0
