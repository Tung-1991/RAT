# HEDGE Dual V1

## Scope

HEDGE Dual là module riêng. Không ghi vào BOT/manual/GRID state. Lệnh HEDGE dùng `hedge_magic` và comment `HEDGE_BUY` / `HEDGE_SELL`.

Những phần dùng lại từ hệ thống cũ:
- Signal engine: chỉ đọc `latest_signal`/context để lọc entry nếu bật.
- Log UI: ghi vào tab/kênh HEDGE.
- Daily reset date: dùng cùng mốc ngày reset của hệ thống, nhưng PnL/loss/session counter là riêng HEDGE.

## Auto Scan

- `ENABLED = ON`: daemon quét `WATCHLIST` của HEDGE.
- `WATCHLIST`: danh sách symbol được phép Auto HEDGE scan/mở cặp.
- `HEDGE_SCAN_INTERVAL_SECONDS`: chu kỳ quét riêng của HEDGE, không dùng interval BOT/GRID.
- Manual HEDGE vẫn mở theo symbol đang chọn, không phụ thuộc watchlist.

## Entry Gate

- `USE_SIGNAL_FILTER = OFF`: không cần signal.
- `USE_SIGNAL_FILTER = ON`: `latest_signal` phải khác `0`.
- `USE_SWING_FILTER = ON`: giá phải gần swing high/low của `SWING_GROUP` + `SWING_TIMEFRAME` trong biên `SWING_TOLERANCE_ATR`.
- Bật cả hai filter thì cả hai phải pass.

## Start Pair

HEDGE mở đồng thời một BUY và một SELL cùng symbol, cùng lot. Nếu mở một chân thành công nhưng chân còn lại fail, module đóng ngay chân đã mở.

## Tactic

- `BASKET`: nhìn tổng PnL cả cặp. Chạm `PAIR_TP_USD` thì đóng cả cặp, chạm `PAIR_SL_USD` thì đóng cả cặp.
- `LEG_OUT`: nếu một chân âm tới `LOSING_LEG_SL_USD`, đóng chân âm và giữ chân còn lại để gỡ. Chân recovery đóng khi đạt `RECOVERY_TARGET_USD` hoặc bị nhả lợi nhuận quá `RECOVERY_GIVEBACK_USD`.

## Safety

HEDGE có settings/state riêng trong workspace account.

- `HEDGE_MAX_DAILY_LOSS`: lỗ ngày tối đa riêng của HEDGE. `0` = tắt rule.
- `MAX_SESSIONS_PER_DAY`: số session HEDGE tối đa/ngày. `0` = không giới hạn.
- `COOLDOWN_AFTER_CLOSE_SECONDS`: nghỉ sau khi đóng một session bất kỳ.
- `COOLDOWN_AFTER_LOSS_SECONDS`: nghỉ lâu hơn nếu session vừa đóng bị âm.
- `MAX_CONSECUTIVE_LOSSES` + `GLOBAL_COOLDOWN_SECONDS`: thua liên tiếp thì bật cooldown tổng.
- `SYMBOL_OVERRIDES`: cấu hình riêng theo symbol, ví dụ ETHUSD/BTCUSD có lot, swing group, TP/SL khác nhau.

Clear block/reset cooldown không reset PnL hoặc counters hôm nay. Stop session không đóng lệnh đang mở.
