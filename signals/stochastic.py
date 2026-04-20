# -*- coding: utf-8 -*-
import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    """
    V3.0: Stochastic Signal.
    Giao cắt %K và %D trong vùng cực biên.
    """
    k_period = params.get("k", 14)
    d_period = params.get("d", 3)
    smooth = params.get("smooth", 3)
    upper = params.get("upper", 80)
    lower = params.get("lower", 20)
    
    # Tên cột mặc định: STOCHk_14_3_3, STOCHd_14_3_3
    col_k = f"STOCHk_{k_period}_{smooth}_{d_period}"
    col_d = f"STOCHd_{k_period}_{smooth}_{d_period}"
    
    if col_k not in df.columns or col_d not in df.columns or len(df) < 2:
        return 0

    curr_k, curr_d = df[col_k].iloc[-1], df[col_d].iloc[-1]
    prev_k, prev_d = df[col_k].iloc[-2], df[col_d].iloc[-2]

    # %K cắt lên %D dưới vùng Oversold -> Buy
    if curr_k <= lower and prev_k <= prev_d and curr_k > curr_d:
        return 1
    # %K cắt xuống %D trên vùng Overbought -> Sell
    if curr_k >= upper and prev_k >= prev_d and curr_k < curr_d:
        return -1
        
    return 0