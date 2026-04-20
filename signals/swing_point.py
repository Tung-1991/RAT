# -*- coding: utf-8 -*-
import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict, context: dict = None) -> int:
    """
    V3.0: Swing Point Signal.
    Xác nhận phá vỡ cấu trúc (Market Structure Break) hoặc chạm cản Swing.
    """
    if not context: return 0
    
    sh = context.get("swing_high", 0)
    sl = context.get("swing_low", 0)
    
    if sh == 0 or sl == 0: return 0
    
    close = df['close'].iloc[-1]
    
    # Phá đỉnh Swing High -> Tiếp diễn tăng
    if close > sh: return 1
    # Phá đáy Swing Low -> Tiếp diễn giảm
    if close < sl: return -1
    
    return 0