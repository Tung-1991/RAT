# -*- coding: utf-8 -*-
import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    """
    V3.0: Pivot Points Signal.
    Đánh đảo chiều tại các vùng hỗ trợ/kháng cự cứng.
    """
    # Giả định DataEngine đã tính các cột PP, R1, S1, R2, S2
    # Thường tính dựa trên giá Day/Week trước đó
    if 'PP' not in df.columns: return 0
    
    latest = df.iloc[-1]
    close = latest['close']
    s1, s2 = latest.get('S1', 0), latest.get('S2', 0)
    r1, r2 = latest.get('R1', 0), latest.get('R2', 0)
    
    # Chạm hỗ trợ S1 hoặc S2 -> Buy
    if (s1 > 0 and close <= s1) or (s2 > 0 and close <= s2):
        return 1
        
    # Chạm kháng cự R1 hoặc R2 -> Sell
    if (r1 > 0 and close >= r1) or (r2 > 0 and close >= r2):
        return -1
        
    return 0