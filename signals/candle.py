import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    """
    V3.0: Candle Signal.
    Nhận diện các mô hình nến đảo chiều/tiếp diễn cơ bản.
    """
    # Các cột mẫu nến thường được DataEngine tính bằng df.ta.cdl_pattern
    # Ví dụ: 'CDL_ENGULFING', 'CDL_HAMMER', 'CDL_SHOOTINGSTAR'
    
    if len(df) < 2:
        return 0
        
    latest = df.iloc[-1]
    
    # Logic đơn giản cho Pinbar/Hammer/Engulfing
    # Nếu thư viện trả về giá trị dương (>0) là Bullish, âm (<0) là Bearish
    bullish_patterns = [col for col in df.columns if 'CDL' in col and latest[col] > 0]
    bearish_patterns = [col for col in df.columns if 'CDL' in col and latest[col] < 0]

    if bullish_patterns:
        return 1
    if bearish_patterns:
        return -1
        
    return 0