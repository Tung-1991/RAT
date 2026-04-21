# -*- coding: utf-8 -*-
import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict, context: dict = None) -> int:
    if not context:
        return 0
        
    sh = context.get("swing_high", 0.0)
    sl = context.get("swing_low", 0.0)
    
    if sh == 0.0 or sl == 0.0:
        return 0
        
    close = df['close'].iloc[-1]
    
    # Phá vỡ đỉnh (Breakout Up)
    if close > sh: return 1 
    # Phá vỡ đáy (Breakout Down)
    if close < sl: return -1 
    
    return 0