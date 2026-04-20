import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    """
    V3.0: EMA Cross Signal.
    Xác định điểm giao cắt (Golden/Death Cross).
    """
    fast_p = params.get("fast", 9)
    slow_p = params.get("slow", 21)
    
    col_fast = f"EMA_{fast_p}"
    col_slow = f"EMA_{slow_p}"
    
    if col_fast not in df.columns or col_slow not in df.columns or len(df) < 2:
        return 0

    # Lấy giá trị nến hiện tại và nến trước đó để check Crossover
    curr_fast = df[col_fast].iloc[-1]
    curr_slow = df[col_slow].iloc[-1]
    prev_fast = df[col_fast].iloc[-2]
    prev_slow = df[col_slow].iloc[-2]

    # Golden Cross (Cắt lên)
    if prev_fast <= prev_slow and curr_fast > curr_slow:
        return 1
        
    # Death Cross (Cắt xuống)
    if prev_fast >= prev_slow and curr_fast < curr_slow:
        return -1
        
    return 0