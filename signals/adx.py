import pandas as pd

def get_signal_vector(df: pd.DataFrame, params: dict) -> int:
    length = params.get("period", 14)
    weak_threshold = params.get("weak", 18)
    
    col_adx = f"ADX_{length}"
    col_dmp = f"DMP_{length}"
    col_dmn = f"DMN_{length}"

    if col_adx not in df.columns or col_dmp not in df.columns or col_dmn not in df.columns:
        return 0

    latest = df.iloc[-1]
    adx = latest[col_adx]
    dmp = latest[col_dmp]
    dmn = latest[col_dmn]

    if adx < weak_threshold:
        return 0

    if dmp > dmn:
        return 1
    if dmn > dmp:
        return -1
        
    return 0