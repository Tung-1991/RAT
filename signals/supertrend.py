# -*- coding: utf-8 -*-
import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    """
    V3.0: Supertrend Signal.
    Xác nhận xu hướng bám đuôi (Trend Follower).
    """
    period = params.get("period", 10)
    multiplier = params.get("multiplier", 3.0)
    
    # Tên cột mặc định: SUPERTd_10_3.0 (Cột direction: 1 hoặc -1)
    col_dir = f"SUPERTd_{period}_{multiplier}"
    
    if col_dir not in df.columns:
        return 0

    direction = df[col_dir].iloc[-1]
    
    # Supertrend trả về 1 cho UP và -1 cho DOWN
    return int(direction) if direction in [1, -1] else 0