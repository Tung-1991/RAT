# -*- coding: utf-8 -*-
import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    """
    V3.0: RSI Signal.
    Đánh đảo chiều khi đi vào vùng Quá mua (Overbought) hoặc Quá bán (Oversold).
    """
    length = params.get("period", 14)
    upper = params.get("upper", 70)
    lower = params.get("lower", 30)
    
    col_rsi = f"RSI_{length}"
    if col_rsi not in df.columns:
        return 0

    rsi_val = df[col_rsi].iloc[-1]

    # Quá bán -> Canh Mua (Reversal)
    if rsi_val <= lower:
        return 1
    # Quá mua -> Canh Bán (Reversal)
    if rsi_val >= upper:
        return -1
        
    return 0