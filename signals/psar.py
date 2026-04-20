# -*- coding: utf-8 -*-
import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    """
    V3.0: Parabolic SAR Signal.
    Đơn giản: Chấm PSAR nằm dưới giá = Buy, nằm trên giá = Sell.
    """
    # Tên cột mặc định của pandas_ta: PSARl_0.02_0.2 (long) và PSARs_0.02_0.2 (short)
    # Hoặc cột PSAR chung tùy cách append
    psar_cols = [c for c in df.columns if "PSAR" in c]
    if not psar_cols: return 0
    
    latest = df.iloc[-1]
    close = latest['close']
    
    # PSARl thường chứa giá trị khi trend tăng, PSARs chứa giá trị khi trend giảm
    # Nếu PSARl có giá trị (không NaN) -> Trend tăng
    psar_l = latest.get([c for c in psar_cols if "PSARl" in c][0], None)
    psar_s = latest.get([c for c in psar_cols if "PSARs" in c][0], None)
    
    if pd.notna(psar_l): return 1
    if pd.notna(psar_s): return -1
    
    return 0