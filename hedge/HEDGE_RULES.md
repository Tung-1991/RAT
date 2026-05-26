# HEDGE Dual Rules

HEDGE Dual là module độc lập state/log, chỉ gọi lại rule có sẵn của bot.

## Entry
- Nếu `USE_SIGNAL_FILTER = ON`: cần `latest_signal != 0`.
- Nếu `USE_ENTRY_EXIT_FILTER = ON`: chạy Entry/Exit engine theo hướng signal nếu có, hoặc cả BUY/SELL nếu không dùng signal. Ít nhất một hướng phải `READY`.
- Nếu filter tắt thì bỏ qua filter đó.
- Dù filter thế nào vẫn phải qua hard safety, max pairs, cooldown, daily loss, ping/spread.

## Orders
- Khi pass, HEDGE mở đồng thời BUY và SELL cùng lot.
- SL/TP lấy từ Entry/Exit decision nếu direction đó `READY`.
- Nếu thiếu SL từ Entry/Exit và `USE_HEDGE_SLTP = ON`, HEDGE tính SL/TP bằng rule riêng của HEDGE. Rule này tái dùng cùng công thức base SL/TP của sandbox/bot nhưng không dùng chung toggle/state sandbox.
- Nếu `USE_HEDGE_SLTP = OFF`, HEDGE tôn trọng cấu hình và có thể mở lệnh không SL/TP.

## Exit
- Không dùng basket TP/SL USD.
- Không dùng leg-out/recovery guard.
- Mỗi chân tự thoát bằng SL/TP/TSL.
- Nếu một chân đóng trước, chân còn lại là survivor. `SURVIVOR_PROTECT` có thể kéo SL về `BE_FEE`, `BE_ONLY`, hoặc không can thiệp.

## Isolation
- HEDGE ghi `hedge_state.json`, `hedge_settings.json` và log `hedge`/`hedge-log`.
- Không ghi state bot/grid.
