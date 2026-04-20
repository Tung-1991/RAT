import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    """
    V3.0: Bollinger Bands Signal.
    Hỗ trợ Range (Đảo chiều) và Breakout (Bám biên).
    """
    # Lấy tên cột từ DataEngine (mặc định của pandas_ta)
    length = params.get("period", 20)
    std_dev = params.get("std_dev", 2.0)
    
    # Tên cột chuẩn của pandas_ta: BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
    col_upper = f"BBU_{length}_{std_dev}"
    col_lower = f"BBL_{length}_{std_dev}"
    
    if col_upper not in df.columns or col_lower not in df.columns:
        return 0

    latest = df.iloc[-1]
    close = latest['close']
    upper = latest[col_upper]
    lower = latest[col_lower]

    # Logic 1: Giá vượt biên trên (Quá mua/Breakout trên)
    if close >= upper:
        return 1
    
    # Logic 2: Giá vượt biên dưới (Quá bán/Breakout dưới)
    if close <= lower:
        return -1

    return 0