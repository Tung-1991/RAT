# -*- coding: utf-8 -*-
import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict, context: dict = None) -> int:
    """
    V3.0: Fibonacci Retracement Signal.
    Sử dụng Swing High/Low từ Radar (H1) để tìm điểm hồi quy trên Trigger (M15).
    """
    if not context:
        return 0
        
    sh = context.get("swing_high", 0)
    sl = context.get("swing_low", 0)
    trend = context.get("trend", "NONE")
    
    if sh == 0 or sl == 0 or sh <= sl:
        return 0

    latest_close = df['close'].iloc[-1]
    diff = sh - sl
    
    # Các mốc Fibo quan trọng (Thường là vùng Buy/Sell zone)
    fibo_618 = sh - (diff * 0.618)
    fibo_500 = sh - (diff * 0.500)
    fibo_382 = sh - (diff * 0.382)
    fibo_786 = sh - (diff * 0.786)

    # Logic: Nếu Trend H1 là UP, giá hồi về vùng 0.5 - 0.786 của H1 -> Canh Mua
    if trend == "UP":
        if fibo_786 <= latest_close <= fibo_500:
            return 1
            
    # Logic: Nếu Trend H1 là DOWN, giá hồi về vùng 0.5 - 0.786 của H1 -> Canh Bán
    elif trend == "DOWN":
        # Với Down trend: fibo_500 = sl + (diff * 0.5), fibo_786 = sl + (diff * 0.786)
        fibo_up_500 = sl + (diff * 0.500)
        fibo_up_786 = sl + (diff * 0.786)
        if fibo_up_500 <= latest_close <= fibo_up_786:
            return -1

    return 0