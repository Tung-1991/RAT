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
    diff = sh - sl
    
    # Fibo thoái lui cơ bản
    fibo_382 = sl + diff * 0.382
    fibo_618 = sl + diff * 0.618
    
    # Bắt phản ứng giá (Sai số 0.1%)
    tolerance = 0.001
    if abs(close - fibo_618) / close < tolerance: return 1 
    if abs(close - fibo_382) / close < tolerance: return -1 
    
    return 0