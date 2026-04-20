import pandas as pd
import numpy as np

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    """
    V3.0: ATR xác nhận Volatility Expansion.
    Đã fix lỗi Zero/NaN ATR để tránh hỏng logic tính Lot/SL.
    """
    length = params.get("period", 14)
    multiplier = params.get("multiplier", 1.5)
    
    col_atr = f"ATR_{length}"
    
    # 1. Kiểm tra sự tồn tại của cột và độ dài dữ liệu
    if col_atr not in df.columns or len(df) < 2:
        return 0

    # 2. Lấy giá trị và xử lý NaN/Zero (Bước FIX quan trọng)
    current_atr = df[col_atr].iloc[-1]
    prev_atr = df[col_atr].iloc[-2]

    # Kiểm tra NaN
    if pd.isna(current_atr) or pd.isna(prev_atr):
        return 0

    # Fix lỗi Zero ATR: Đảm bảo không bao giờ nhỏ hơn một giá trị sàn (ví dụ 1e-7)
    safe_prev_atr = max(prev_atr, 1e-7)
    safe_current_atr = max(current_atr, 1e-7)

    # 3. Logic xác nhận Volatility Expansion
    # Nếu ATR hiện tại vượt qua ngưỡng biến động trung bình (multiplier)
    if safe_current_atr > (safe_prev_atr * multiplier):
        return 1
        
    return 0