# -*- coding: utf-8 -*-
import pandas as pd


def get_signal_vector(df: pd.DataFrame, params: dict, context: dict = None) -> int:
    # 1. Lấy thông số trực tiếp từ giao diện UI (params)
    # Nếu Ngài chưa nhập gì, nó sẽ lấy giá trị mặc định (1 nến và 0 đệm)
    lookback = int(params.get("lookback", 1))
    buffer = float(params.get("buffer_points", 0.0))

    # 2. Bẫy lỗi: Đảm bảo có đủ nến để soi
    if df is None or len(df) < lookback + 1:
        return 0

    current_close = df["close"].iloc[-1]

    # 3. Quét tìm Đỉnh/Đáy của cụm nến trong quá khứ dựa theo 'lookback'
    # iloc[-(lookback + 1):-1] nghĩa là lấy từ nến xa nhất đến nến ngay trước nến hiện tại
    prev_high = df["high"].iloc[-(lookback + 1) : -1].max()
    prev_low = df["low"].iloc[-(lookback + 1) : -1].min()

    # 4. Logic bóp cò có tính thêm khoảng đệm chống nhiễu
    if current_close > (prev_high + buffer):
        return 1  # BUY

    if current_close < (prev_low - buffer):
        return -1  # SELL

    return 0  # ĐỨNG IM
