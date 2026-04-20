# -*- coding: utf-8 -*-
import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    """
    V3.0: EMA Bias Signal.
    Xác định xu hướng dựa trên vị trí giá so với đường EMA (ví dụ EMA 200).
    """
    period = params.get("period", 200)
    col_ema = f"EMA_{period}"
    
    if col_ema not in df.columns:
        return 0

    latest = df.iloc[-1]
    close = latest['close']
    ema_val = latest[col_ema]

    # Giá nằm trên EMA -> Ưu tiên Mua
    if close > ema_val:
        return 1
    # Giá nằm dưới EMA -> Ưu tiên Bán
    elif close < ema_val:
        return -1
        
    return 0