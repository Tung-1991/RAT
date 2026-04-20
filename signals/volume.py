# -*- coding: utf-8 -*-
import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    """
    V3.0: Volume Signal (Price-Volume Relationship).
    Xử lý logic dòng tiền: 
    - Giá tăng + Vol tăng = 1 (Dòng tiền vào mạnh)
    - Giá tăng + Vol giảm = -1 (Dòng tiền out/Bẫy tăng giá)
    - Giá giảm + Vol tăng = -1 (Áp lực bán mạnh)
    - Giá giảm + Vol giảm = 1 (Cạn kiệt lực bán)
    """
    col_vol = 'tick_volume' if 'tick_volume' in df.columns else 'volume'
    if col_vol not in df.columns or len(df) < 20:
        return 0

    period = params.get("period", 20)
    # Ngưỡng để xác định Volume thế nào là "Tăng/Giảm" so với trung bình
    multiplier = params.get("multiplier", 1.1) 
    
    avg_vol = df[col_vol].shift(1).rolling(window=period).mean().iloc[-1]
    curr_vol = df[col_vol].iloc[-1]
    
    curr_close = df['close'].iloc[-1]
    prev_close = df['close'].iloc[-2]
    
    price_up = curr_close > prev_close
    vol_high = curr_vol > (avg_vol * multiplier)
    vol_low = curr_vol < (avg_vol / multiplier)

    # --- LOGIC DÒNG TIỀN THEO YÊU CẦU CỦA NGÀI ---

    if price_up:
        if vol_high:
            return 1   # Giá tăng + Vol tăng = Hội tụ tăng (Strong Buy)
        if vol_low:
            return -1  # Giá tăng + Vol giảm = Phân kỳ giảm (Cash Out/Bull Trap)
    else:
        if vol_high:
            return -1  # Giá giảm + Vol tăng = Hội tụ giảm (Strong Sell)
        if vol_low:
            return 1   # Giá giảm + Vol giảm = Phân kỳ tăng (Bearish Exhaustion)

    return 0