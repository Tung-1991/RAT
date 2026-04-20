# -*- coding: utf-8 -*-
import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    """
    V3.0: Multi-Candle (Pullback Confirmation).
    Xác nhận cụm nến đảo chiều sau một nhịp điều chỉnh.
    """
    if len(df) < 4:
        return 0
        
    # Lấy 3 nến gần nhất (không tính nến đang chạy)
    c1 = df.iloc[-2] # Nến vừa đóng
    c2 = df.iloc[-3] 
    c3 = df.iloc[-4]
    
    # Logic Pullback BUY: 2 nến giảm liên tiếp, sau đó nến c1 là nến tăng mạnh (Engulfing)
    is_pullback_buy = (c3['close'] < c3['open']) and \
                      (c2['close'] < c2['open']) and \
                      (c1['close'] > c1['open'] and c1['close'] > c2['open'])
                      
    # Logic Pullback SELL: 2 nến tăng liên tiếp, sau đó nến c1 là nến giảm mạnh
    is_pullback_sell = (c3['close'] > c3['open']) and \
                       (c2['close'] > c2['open']) and \
                       (c1['close'] < c1['open'] and c1['close'] < c2['open'])

    if is_pullback_buy: return 1
    if is_pullback_sell: return -1
    
    return 0