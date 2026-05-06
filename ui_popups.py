# -*- coding: utf-8 -*-
# FILE: ui_popups.py
# V3.8: SUPREME FINAL - TRANSIENT LOCK & TACTIC PREVIEW (KAISER EDITION)

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import config
import csv
import os

# --- BẢNG MÀU & FONT CHUẨN ---
FONT_BOLD = ("Roboto", 13, "bold")
COL_GREEN = "#00C853"
COL_RED = "#D50000"
COL_BLUE_ACCENT = "#1565C0"
COL_GRAY_BTN = "#424242"
COL_WARN = "#FFAB00"
COL_BOT_TAG = "#E040FB"


def _add_popup_hint(parent, text, padx=15, pady=(5, 10), wraplength=900):
    hint_f = ctk.CTkFrame(
        parent,
        fg_color="#332B00",
        corner_radius=6,
        border_width=1,
        border_color="#FFD600",
    )
    hint_f.pack(fill="x", padx=padx, pady=pady)
    ctk.CTkLabel(
        hint_f,
        text=text,
        font=("Roboto", 13, "italic"),
        text_color="#FFD600",
        justify="left",
        anchor="w",
        wraplength=wraplength,
    ).pack(fill="x", padx=10, pady=6)
    return hint_f


# ==============================================================================
# 1. POPUP CẤU HÌNH TỪNG CẶP GIAO DỊCH (SYMBOL CONFIG)
# ==============================================================================
def open_symbol_config_popup(app, symbol):
    import json

    import core.storage_manager as storage_manager
    cfg_path = storage_manager.BRAIN_FILE
    existing_data = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except:
            pass

    symbol_configs = existing_data.get("symbol_configs", {})
    sym_cfg = symbol_configs.get(symbol, {})

    top = ctk.CTkToplevel(app)
    top.title(f"Cấu hình riêng: {symbol}")
    top.geometry("720x720")
    top.minsize(620, 520)
    top.attributes("-topmost", True)
    top.focus_force()
    body = ctk.CTkScrollableFrame(top, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=12, pady=(10, 4))
    top.grab_set()  # Khóa (Block) cửa sổ mẹ, bắt buộc người dùng thao tác trên popup này

    ctk.CTkLabel(
        body, text=f"THIẾT LẬP SAFEGUARD: {symbol}", font=FONT_BOLD, text_color="#2196F3"
    ).pack(pady=10)
    _add_popup_hint(
        body,
        "- Cấu hình này chỉ áp dụng cho symbol đang chọn.\n"
        "- Fixed Lot > 0 sẽ bỏ qua risk %, dùng lot cố định.\n"
        "- Watermark/Basket/Max Lot là hàng rào riêng trước khi bot vào hoặc giữ lệnh.",
        padx=20,
        pady=(0, 5),
        wraplength=620,
    )

    f_grid = ctk.CTkFrame(body, fg_color="transparent")
    f_grid.pack(fill="x", padx=20, pady=10)
    f_grid.grid_columnconfigure(0, weight=1)

    # Max Orders
    ctk.CTkLabel(f_grid, text="Max Lệnh Tối Đa:").grid(
        row=0, column=0, sticky="w", pady=10
    )
    e_max_orders = ctk.CTkEntry(f_grid, width=100, justify="center")
    e_max_orders.insert(0, str(sym_cfg.get("max_orders", 1)))
    e_max_orders.grid(row=0, column=1, sticky="e", pady=10)

    # Max Spread
    ctk.CTkLabel(f_grid, text="Max Spread (points):").grid(
        row=1, column=0, sticky="w", pady=10
    )
    e_max_spread = ctk.CTkEntry(f_grid, width=100, justify="center")
    e_max_spread.insert(0, str(sym_cfg.get("max_spread", 150)))
    e_max_spread.grid(row=1, column=1, sticky="e", pady=10)

    # Max Ping
    ctk.CTkLabel(f_grid, text="Max Ping (ms):").grid(
        row=2, column=0, sticky="w", pady=10
    )
    e_max_ping = ctk.CTkEntry(f_grid, width=100, justify="center")
    e_max_ping.insert(0, str(sym_cfg.get("max_ping", 150)))
    e_max_ping.grid(row=2, column=1, sticky="e", pady=10)

    # [NEW V4.4] Fixed Lot Mode
    ctk.CTkLabel(
        f_grid,
        text="Fixed Lot (0 = Tắt):",
        text_color="#FFB300",
        font=("Roboto", 12, "bold"),
    ).grid(row=3, column=0, sticky="w", pady=10)
    e_fixed_lot = ctk.CTkEntry(f_grid, width=100, justify="center")
    e_fixed_lot.insert(0, str(sym_cfg.get("fixed_lot", 0.0)))
    e_fixed_lot.grid(row=3, column=1, sticky="e", pady=10)

    # [NEW V4.4] Max Lot Cap
    ctk.CTkLabel(
        f_grid,
        text="Max Lot Cap (0=Tắt):",
        text_color="#FFB300",
        font=("Roboto", 12, "bold"),
    ).grid(row=4, column=0, sticky="w", pady=10)
    e_max_lot_cap = ctk.CTkEntry(f_grid, width=100, justify="center")
    e_max_lot_cap.insert(0, str(sym_cfg.get("max_lot_cap", 0.0)))
    e_max_lot_cap.grid(row=4, column=1, sticky="e", pady=10)

    # [NEW V5] Watermark & Options
    ctk.CTkLabel(f_grid, text="Watermark Trigger:", text_color="#00C853").grid(row=5, column=0, sticky="w", pady=10)
    e_wm_trigger = ctk.CTkEntry(f_grid, width=100, justify="center")
    e_wm_trigger.insert(0, str(sym_cfg.get("watermark_trigger", 0.0)))
    e_wm_trigger.grid(row=5, column=1, sticky="e", pady=10)
    cbo_wm_trigger_unit = ctk.CTkOptionMenu(f_grid, values=["USD", "%Equity"], width=90)
    cbo_wm_trigger_unit.set(sym_cfg.get("watermark_trigger_unit", "USD"))
    cbo_wm_trigger_unit.grid(row=5, column=2, sticky="w", padx=(8, 0), pady=10)

    ctk.CTkLabel(f_grid, text="Watermark Sụt giảm:", text_color="#00C853").grid(row=6, column=0, sticky="w", pady=10)
    e_wm_drawdown = ctk.CTkEntry(f_grid, width=100, justify="center")
    e_wm_drawdown.insert(0, str(sym_cfg.get("watermark_drawdown", 0.0)))
    e_wm_drawdown.grid(row=6, column=1, sticky="e", pady=10)
    cbo_wm_drawdown_unit = ctk.CTkOptionMenu(f_grid, values=["USD", "%Equity"], width=90)
    cbo_wm_drawdown_unit.set(sym_cfg.get("watermark_drawdown_unit", "USD"))
    cbo_wm_drawdown_unit.grid(row=6, column=2, sticky="w", padx=(8, 0), pady=10)

    ctk.CTkLabel(f_grid, text="SL Tối thiểu (Points):").grid(row=7, column=0, sticky="w", pady=10)
    e_min_sl = ctk.CTkEntry(f_grid, width=100, justify="center")
    e_min_sl.insert(0, str(sym_cfg.get("min_sl_points", 0)))
    e_min_sl.grid(row=7, column=1, sticky="e", pady=10)

    ctk.CTkLabel(f_grid, text="Max Basket Drawdown (DCA/PCA):").grid(row=8, column=0, sticky="w", pady=10)
    e_basket_dd = ctk.CTkEntry(f_grid, width=100, justify="center")
    e_basket_dd.insert(0, str(sym_cfg.get("max_basket_drawdown", 0.0)))
    e_basket_dd.grid(row=8, column=1, sticky="e", pady=10)
    cbo_basket_dd_unit = ctk.CTkOptionMenu(f_grid, values=["USD", "%Equity"], width=90)
    cbo_basket_dd_unit.set(sym_cfg.get("max_basket_drawdown_unit", "USD"))
    cbo_basket_dd_unit.grid(row=8, column=2, sticky="w", padx=(8, 0), pady=10)

    var_reject_lot = ctk.BooleanVar(value=sym_cfg.get("reject_on_max_lot", False))
    ctk.CTkCheckBox(f_grid, text="Hủy lệnh nếu vượt Max Lot (Tắt = Ép bằng Max Lot)", variable=var_reject_lot, font=("Roboto", 11)).grid(row=9, column=0, columnspan=2, sticky="w", pady=10)

    def save_sym():
        try:
            mo = int(e_max_orders.get())
            ms = int(e_max_spread.get())
            mp = int(e_max_ping.get())

            if "symbol_configs" not in existing_data:
                existing_data["symbol_configs"] = {}
            existing_data["symbol_configs"][symbol] = {
                "max_orders": mo,
                "max_spread": ms,
                "max_ping": mp,
                "fixed_lot": float(e_fixed_lot.get()),
                "max_lot_cap": float(e_max_lot_cap.get()),
                "watermark_trigger": float(e_wm_trigger.get()),
                "watermark_trigger_unit": cbo_wm_trigger_unit.get(),
                "watermark_drawdown": float(e_wm_drawdown.get()),
                "watermark_drawdown_unit": cbo_wm_drawdown_unit.get(),
                "min_sl_points": int(e_min_sl.get()),
                "max_basket_drawdown": float(e_basket_dd.get()),
                "max_basket_drawdown_unit": cbo_basket_dd_unit.get(),
                "reject_on_max_lot": var_reject_lot.get(),
            }
            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=4)
            from core.storage_manager import invalidate_settings_cache
            invalidate_settings_cache()
            app.log_message(f"✅ Đã lưu cấu hình riêng cho {symbol}.", target="bot")
            top.destroy()
        except ValueError:
            messagebox.showerror("Lỗi", "Dữ liệu nhập sai, vui lòng nhập số nguyên!", parent=top)

    ctk.CTkButton(
        top,
        text="LƯU CẤU HÌNH",
        fg_color=COL_GREEN,
        font=FONT_BOLD,
        height=40,
        command=save_sym,
    ).pack(pady=15, fill="x", padx=30)


# ==============================================================================
# 2. POPUP CẤU HÌNH LÕI (CHỈ CÒN SAFETY & WATCHLIST)
# ==============================================================================
def open_bot_setting_popup(app):
    top = ctk.CTkToplevel(app)
    top.title("Cấu hình Lõi Hệ Thống (Core Settings)")
    top.geometry("1050x720")
    top.minsize(860, 560)
    top.attributes("-topmost", True)
    # top.transient(app) # Khóa Z-index, luôn nổi trên App chính

    tab_core = ctk.CTkScrollableFrame(top, fg_color="transparent")
    tab_core.pack(fill="both", expand=True, padx=15, pady=15)

    # Switch Auto Trade
    f_auto = ctk.CTkFrame(tab_core, fg_color="transparent")
    f_auto.pack(fill="x", pady=10)
    ctk.CTkLabel(
        f_auto, text="Tự động bóp cò khi Brain có tín hiệu:", text_color="gray"
    ).pack()
    sw_auto = ctk.CTkSwitch(
        f_auto,
        text="AUTO-TRADING DAEMON",
        variable=app.var_auto_trade,
        font=("Roboto", 14, "bold"),
        progress_color=COL_GREEN,
        fg_color=COL_RED,
        command=app.on_auto_trade_toggle,
    )
    sw_auto.pack(pady=5)

    ctk.CTkFrame(tab_core, height=2, fg_color="#333").pack(fill="x", padx=30, pady=5)

    # Watchlist (Đã chuyển lên đầu)
    ctk.CTkLabel(
        tab_core,
        text="WATCHLIST - BOT CHỈ QUÉT CÁC COIN SAU:",
        font=FONT_BOLD,
        text_color="#2196F3",
    ).pack(pady=(5, 5))
    _add_popup_hint(
        tab_core,
        "- Watchlist quyết định symbol bot được quét; nút bánh răng là safeguard riêng từng symbol.\n"
        "- AUTO-TRADING bật/tắt bóp cò thật, nhưng preview/context vẫn có thể chạy để quan sát.\n"
        "- Cấu hình Global là mặc định; cấu hình riêng theo symbol sẽ ghi đè.",
        padx=30,
        pady=(0, 10),
    )
    f_coins = ctk.CTkFrame(tab_core, fg_color="transparent")
    f_coins.pack(fill="x", padx=30, pady=(0, 10))
    app.bot_coin_vars = {}
    allowed_list = getattr(config, "BOT_ACTIVE_SYMBOLS", config.COIN_LIST)

    # Tạo layout lưới cho các cặp tiền
    row_idx = 0
    col_idx = 0
    for coin in config.COIN_LIST:
        var = tk.BooleanVar(value=(coin in allowed_list))
        app.bot_coin_vars[coin] = var

        f_single_coin = ctk.CTkFrame(f_coins, fg_color="transparent")
        f_single_coin.grid(row=row_idx, column=col_idx, sticky="w", pady=5, padx=10)

        chk = ctk.CTkCheckBox(
            f_single_coin, text=coin, variable=var, font=("Consolas", 13), width=80
        )
        chk.pack(side="left")

        btn_cfg = ctk.CTkButton(
            f_single_coin,
            text="⚙",
            width=25,
            height=20,
            fg_color="#444",
            hover_color="#666",
            command=lambda c=coin: open_symbol_config_popup(app, c),
        )
        btn_cfg.pack(side="left", padx=(5, 0))

        col_idx += 1
        if col_idx > 1:
            col_idx = 0
            row_idx += 1

    ctk.CTkFrame(tab_core, height=2, fg_color="#333").pack(fill="x", padx=30, pady=5)

    # Safety Guard (Bot ONLY - Độc lập hoàn toàn với Manual)
    ctk.CTkLabel(
        tab_core,
        text="HÀNG RÀO BẢO VỆ BOT (BOT SAFEGUARD)",
        font=FONT_BOLD,
        text_color="#FFB300",
    ).pack(pady=(5, 5))
    _add_popup_hint(
        tab_core,
        "- Global Brake chặn toàn bot khi chạm ngưỡng lỗ/streak/cooldown.\n"
        "- Safeguard bảo vệ lợi nhuận, rổ DCA/PCA, SL tối thiểu và điều kiện TP.\n"
        "- Giá trị 0 thường là tắt giới hạn tương ứng.",
        padx=30,
        pady=(0, 10),
    )

    # --- [NEW] LIVE PREVIEW ---
    from core.storage_manager import load_state, save_state
    import time

    st = load_state()
    start_bal = st.get("starting_balance", 0)
    pnl = st.get("bot_pnl_today", 0.0)
    loss_pct = (pnl / start_bal * 100) if start_bal > 0 else 0
    trades = st.get("bot_trades_today", 0)
    losses = st.get("bot_daily_loss_count", 0)
    cooldown_until = st.get("cooldown_until", 0.0)

    f_preview = ctk.CTkFrame(tab_core, fg_color="#1E1E1E", corner_radius=8)
    f_preview.pack(fill="x", padx=15, pady=(0, 10))

    cooldown_str = "Sẵn sàng"
    now = time.time()
    if now < cooldown_until:
        rem = int((cooldown_until - now) / 60)
        cooldown_str = f"BỊ CHẶN ({rem} phút)"

    pnl_color = COL_GREEN if loss_pct >= 0 else COL_RED
    preview_text = f"PNL Today: {loss_pct:+.2f}% | Lệnh: {trades} | Thua: {losses} | Cooldown: {cooldown_str}"

    ctk.CTkLabel(
        f_preview,
        text="LIVE PREVIEW:",
        font=("Roboto", 12, "bold"),
        text_color="#00E676",
    ).pack(side="left", padx=10, pady=8)

    lbl_preview = ctk.CTkLabel(
        f_preview, text=preview_text, font=("Consolas", 12, "bold"), text_color=pnl_color
    )
    lbl_preview.pack(side="left", padx=10, pady=8)

    f_iso = ctk.CTkFrame(tab_core, fg_color="#171717", corner_radius=8)
    f_iso.pack(fill="x", padx=15, pady=(0, 10))

    def render_isolation_preview():
        for child in f_iso.winfo_children():
            child.destroy()

        latest_state = load_state()
        now_ts = time.time()
        active_iso = []
        for sym, deadline in latest_state.get("bot_last_fail_times", {}).items():
            try:
                deadline = float(deadline)
            except (TypeError, ValueError):
                continue
            if deadline > now_ts:
                rem = int(deadline - now_ts)
                active_iso.append((sym, rem))

        ctk.CTkLabel(
            f_iso,
            text="Isolation:",
            font=("Roboto", 11, "bold"),
            text_color="#FFB300" if active_iso else "#757575",
        ).pack(side="left", padx=(10, 6), pady=6)

        if not active_iso:
            ctk.CTkLabel(
                f_iso,
                text="Không có",
                font=("Consolas", 11),
                text_color="#757575",
            ).pack(side="left", padx=4, pady=6)
            return

        def reset_symbol(sym):
            latest = load_state()
            latest.get("bot_last_fail_times", {}).pop(sym, None)
            save_state(latest)
            if hasattr(app, "trade_mgr"):
                app.trade_mgr.state = latest
            if hasattr(app, "log_message"):
                app.log_message(f"✅ Đã reset isolation cho {sym}.", target="bot")
            render_isolation_preview()

        for sym, rem in active_iso:
            time_str = f"{rem // 3600}h{(rem % 3600) // 60}m" if rem >= 3600 else f"{rem // 60}m"
            ctk.CTkLabel(
                f_iso,
                text=f"{sym} {time_str}",
                font=("Consolas", 11, "bold"),
                text_color="#FF5252",
            ).pack(side="left", padx=(8, 3), pady=6)
            ctk.CTkButton(
                f_iso,
                text="Reset",
                width=54,
                height=24,
                fg_color="#424242",
                hover_color="#616161",
                command=lambda s=sym: reset_symbol(s),
            ).pack(side="left", padx=(0, 6), pady=6)

    render_isolation_preview()

    f_safety = ctk.CTkFrame(tab_core, fg_color="#2b2b2b", corner_radius=8)
    f_safety.pack(fill="x", padx=15, pady=5)
    f_safety.columnconfigure((0, 2), weight=1)

    # [FIX] Đọc safeguard từ brain_settings.json TRƯỚC, fallback về config.py
    safe_cfg = {}
    try:
        import json as _json

        import core.storage_manager as storage_manager
        _cfg_path = storage_manager.BRAIN_FILE
        if os.path.exists(_cfg_path):
            with open(_cfg_path, "r", encoding="utf-8") as _f:
                safe_cfg = _json.load(_f).get("bot_safeguard", {})
    except Exception:
        pass

    ctk.CTkLabel(f_safety, text="Bot Max Loss/Ngày (%):").grid(
        row=0, column=0, sticky="w", padx=10, pady=8
    )
    e_max_loss = ctk.CTkEntry(f_safety, width=70, justify="center")
    e_max_loss.insert(
        0,
        str(
            safe_cfg.get(
                "MAX_DAILY_LOSS_PERCENT", getattr(config, "MAX_DAILY_LOSS_PERCENT", 2.5)
            )
        ),
    )
    # --- [GROUP 1: ⚠️ PHANH KHẨN CẤP GLOBAL (EMERGENCY)] ---
    # --- [GROUP 1: ⚠️ PHANH KHẨN CẤP GLOBAL (EMERGENCY)] ---
    f_global = ctk.CTkFrame(f_safety, border_width=1, border_color="#F44336")
    f_global.grid(row=0, column=0, columnspan=4, sticky="nsew", padx=5, pady=8)
    ctk.CTkLabel(f_global, text="⚠️ PHANH KHẨN CẤP (GLOBAL BRAKE)", text_color="#F44336", font=("Roboto", 13, "bold")).pack(pady=5)
    
    f_gl_content = ctk.CTkFrame(f_global, fg_color="transparent")
    f_gl_content.pack(fill="x", padx=10, pady=5)
    
    ctk.CTkLabel(f_gl_content, text="Bot Max Loss/Ngày (%):").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    e_max_loss = ctk.CTkEntry(f_gl_content, width=70, justify="center")
    e_max_loss.insert(0, str(safe_cfg.get("MAX_DAILY_LOSS_PERCENT", 2.5)))
    e_max_loss.grid(row=0, column=1, sticky="w", padx=10, pady=5)

    ctk.CTkLabel(f_gl_content, text="Bot Max Thua (Streak):").grid(row=0, column=2, sticky="w", padx=10, pady=5)
    e_max_streak = ctk.CTkEntry(f_gl_content, width=70, justify="center")
    e_max_streak.insert(0, str(safe_cfg.get("MAX_LOSING_STREAK", 3)))
    e_max_streak.grid(row=0, column=3, sticky="w", padx=10, pady=5)

    ctk.CTkLabel(f_gl_content, text="Global Cooldown (Giờ):", font=("Roboto", 12, "bold")).grid(row=1, column=0, sticky="w", padx=10, pady=5)
    e_global_cooldown = ctk.CTkEntry(f_gl_content, width=70, justify="center", fg_color="#311B92")
    e_global_cooldown.insert(0, str(safe_cfg.get("GLOBAL_COOLDOWN_HOURS", 4.0)))
    e_global_cooldown.grid(row=1, column=1, sticky="w", padx=10, pady=5)

    var_gl_on_sg = ctk.BooleanVar(value=safe_cfg.get("APPLY_GLOBAL_COOLDOWN_ON_SAFEGUARD", False))
    chk_gl_on_sg = ctk.CTkCheckBox(f_gl_content, text="Dính Basket/Watermark -> Chặn Global luôn", variable=var_gl_on_sg, text_color="#FF5252", font=("Roboto", 11, "italic"))
    chk_gl_on_sg.grid(row=1, column=2, columnspan=2, sticky="w", padx=10, pady=5)

    # --- [GROUP 2: 📉 SAFEGUARD & PROFIT (PROTECTION)] ---
    f_sg = ctk.CTkFrame(f_safety, border_width=1, border_color="#00C853")
    f_sg.grid(row=1, column=0, columnspan=4, sticky="nsew", padx=5, pady=8)
    ctk.CTkLabel(f_sg, text="📉 BẢO VỆ LỢI NHUẬN & RỔ LỆNH (SAFEGUARD)", text_color="#00C853", font=("Roboto", 13, "bold")).pack(pady=5)
    
    f_sg_content = ctk.CTkFrame(f_sg, fg_color="transparent")
    f_sg_content.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(f_sg_content, text="Watermark Global:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    e_gl_wm_trigger = ctk.CTkEntry(f_sg_content, width=60, justify="center")
    e_gl_wm_trigger.insert(0, str(safe_cfg.get("WATERMARK_TRIGGER", 0.0)))
    e_gl_wm_trigger.grid(row=0, column=1, sticky="w", padx=5, pady=5)
    cbo_gl_wm_trigger_unit = ctk.CTkOptionMenu(f_sg_content, values=["USD", "%Equity"], width=90)
    cbo_gl_wm_trigger_unit.set(safe_cfg.get("WATERMARK_TRIGGER_UNIT", "USD"))
    cbo_gl_wm_trigger_unit.grid(row=0, column=2, sticky="w", padx=(0, 10), pady=5)

    ctk.CTkLabel(f_sg_content, text="Drawdown:").grid(row=0, column=3, sticky="w", padx=10, pady=5)
    e_gl_wm_drawdown = ctk.CTkEntry(f_sg_content, width=60, justify="center")
    e_gl_wm_drawdown.insert(0, str(safe_cfg.get("WATERMARK_DRAWDOWN", 0.0)))
    e_gl_wm_drawdown.grid(row=0, column=4, sticky="w", padx=5, pady=5)
    cbo_gl_wm_drawdown_unit = ctk.CTkOptionMenu(f_sg_content, values=["USD", "%Equity"], width=90)
    cbo_gl_wm_drawdown_unit.set(safe_cfg.get("WATERMARK_DRAWDOWN_UNIT", "USD"))
    cbo_gl_wm_drawdown_unit.grid(row=0, column=5, sticky="w", padx=(0, 10), pady=5)

    ctk.CTkLabel(f_sg_content, text="Max Basket Loss (DCA/PCA):").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    e_gl_basket_dd = ctk.CTkEntry(f_sg_content, width=60, justify="center")
    e_gl_basket_dd.insert(0, str(safe_cfg.get("MAX_BASKET_DRAWDOWN_USD", 0.0)))
    e_gl_basket_dd.grid(row=1, column=1, sticky="w", padx=5, pady=5)
    cbo_gl_basket_dd_unit = ctk.CTkOptionMenu(f_sg_content, values=["USD", "%Equity"], width=90)
    cbo_gl_basket_dd_unit.set(safe_cfg.get("MAX_BASKET_DRAWDOWN_UNIT", "USD"))
    cbo_gl_basket_dd_unit.grid(row=1, column=2, sticky="w", padx=(0, 10), pady=5)

    ctk.CTkLabel(f_sg_content, text="SL Tối thiểu (pts):").grid(row=1, column=3, sticky="w", padx=10, pady=5)
    e_gl_min_sl = ctk.CTkEntry(f_sg_content, width=60, justify="center")
    e_gl_min_sl.insert(0, str(safe_cfg.get("MIN_SL_POINTS", 0)))
    e_gl_min_sl.grid(row=1, column=4, sticky="w", padx=5, pady=5)

    # Dòng TP & Safeguard bổ sung
    var_bot_use_swing_tp = ctk.BooleanVar(value=safe_cfg.get("BOT_USE_SWING_TP", False))
    ctk.CTkCheckBox(f_sg_content, text="Dùng TP SwingPoint", variable=var_bot_use_swing_tp, font=("Roboto", 11)).grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=2)
    
    var_bot_use_rr_tp = ctk.BooleanVar(value=safe_cfg.get("BOT_USE_RR_TP", True))
    ctk.CTkCheckBox(f_sg_content, text="Dùng TP R (Ratio):", variable=var_bot_use_rr_tp, font=("Roboto", 11)).grid(row=2, column=2, sticky="w", padx=10, pady=2)
    e_bot_tp_rr = ctk.CTkEntry(f_sg_content, width=50, justify="center")
    e_bot_tp_rr.insert(0, str(safe_cfg.get("BOT_TP_RR_RATIO", 1.5)))
    e_bot_tp_rr.grid(row=2, column=3, sticky="w", padx=5, pady=2)

    var_strict_min_lot = ctk.BooleanVar(value=safe_cfg.get("STRICT_MIN_LOT", False))
    ctk.CTkCheckBox(f_sg_content, text="Strict Min Lot", variable=var_strict_min_lot, text_color="#F44336", font=("Roboto", 11, "bold")).grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=2)

    var_gl_reject_lot = ctk.BooleanVar(value=safe_cfg.get("REJECT_ON_MAX_LOT", False))
    ctk.CTkCheckBox(f_sg_content, text="Hủy lệnh vượt Max Lot", variable=var_gl_reject_lot, font=("Roboto", 11)).grid(row=3, column=2, columnspan=2, sticky="w", padx=10, pady=2)

    # --- [NEW V5.2] GLOBAL BRAKE MODE ---
    ctk.CTkLabel(f_sg_content, text="Global Brake Mode:").grid(row=4, column=0, sticky="w", padx=10, pady=(10, 0))
    current_brake_mode = safe_cfg.get("GLOBAL_BRAKE_MODE", "Mode 1: Total Freeze")
    cbo_brake_mode = ctk.CTkOptionMenu(
        f_sg_content, 
        values=["Mode 1: Total Freeze", "Mode 2: Symbol Isolation"],
        width=200
    )
    cbo_brake_mode.set(current_brake_mode)
    cbo_brake_mode.grid(row=4, column=1, columnspan=3, sticky="w", padx=10, pady=(10, 0))

    # --- [GROUP 3: 🛡️ ĐIỀU KIỆN VẬN HÀNH (OPERATIONAL)] ---
    f_op = ctk.CTkFrame(f_safety, border_width=1, border_color="#2196F3")
    f_op.grid(row=2, column=0, columnspan=4, sticky="nsew", padx=5, pady=8)
    ctk.CTkLabel(f_op, text="🛡️ ĐIỀU KIỆN VẬN HÀNH (OPERATIONAL)", text_color="#2196F3", font=("Roboto", 13, "bold")).pack(pady=5)
    
    f_op_content = ctk.CTkFrame(f_op, fg_color="transparent")
    f_op_content.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(f_op_content, text="Max Lệnh Mở:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    e_max_open = ctk.CTkEntry(f_op_content, width=60, justify="center")
    e_max_open.insert(0, str(safe_cfg.get("MAX_OPEN_POSITIONS", 3)))
    e_max_open.grid(row=0, column=1, sticky="w", padx=5, pady=5)

    ctk.CTkLabel(f_op_content, text="Bot Cooldown (M):").grid(row=0, column=2, sticky="w", padx=10, pady=5)
    e_cooldown = ctk.CTkEntry(f_op_content, width=60, justify="center")
    e_cooldown.insert(0, str(safe_cfg.get("COOLDOWN_MINUTES", 1)))
    e_cooldown.grid(row=0, column=3, sticky="w", padx=5, pady=5)

    ctk.CTkLabel(f_op_content, text="Tổng Lệnh/Ngày:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    e_max_trades = ctk.CTkEntry(f_op_content, width=60, justify="center")
    e_max_trades.insert(0, str(safe_cfg.get("MAX_TRADES_PER_DAY", 30)))
    e_max_trades.grid(row=1, column=1, sticky="w", padx=5, pady=5)

    ctk.CTkLabel(f_op_content, text="Chế độ tính Loss:").grid(row=1, column=2, sticky="w", padx=10, pady=5)
    cbo_loss_mode = ctk.CTkOptionMenu(f_op_content, values=["TOTAL", "STREAK"], width=80, height=24)
    cbo_loss_mode.set(safe_cfg.get("LOSS_COUNT_MODE", "TOTAL"))
    cbo_loss_mode.grid(row=1, column=3, sticky="w", padx=5, pady=5)

    var_check_ping = ctk.BooleanVar(value=safe_cfg.get("CHECK_PING", True))
    ctk.CTkCheckBox(f_op_content, text="Ping (ms):", variable=var_check_ping, font=("Roboto", 11)).grid(row=2, column=0, sticky="w", padx=10, pady=5)
    e_max_ping = ctk.CTkEntry(f_op_content, width=60, justify="center")
    e_max_ping.insert(0, str(safe_cfg.get("MAX_PING_MS", 150)))
    e_max_ping.grid(row=2, column=1, sticky="w", padx=5, pady=5)

    var_check_spread = ctk.BooleanVar(value=safe_cfg.get("CHECK_SPREAD", True))
    ctk.CTkCheckBox(f_op_content, text="Spread (pts):", variable=var_check_spread, font=("Roboto", 11)).grid(row=2, column=2, sticky="w", padx=10, pady=5)
    e_max_spread = ctk.CTkEntry(f_op_content, width=60, justify="center")
    e_max_spread.insert(0, str(safe_cfg.get("MAX_SPREAD_POINTS", 50)))
    e_max_spread.grid(row=2, column=3, sticky="w", padx=5, pady=5)

    ctk.CTkLabel(f_op_content, text="Nghỉ sau đóng (s):", text_color="#FFB300").grid(row=3, column=0, sticky="w", padx=10, pady=5)
    e_post_close = ctk.CTkEntry(f_op_content, width=60, justify="center")
    e_post_close.insert(0, str(safe_cfg.get("POST_CLOSE_COOLDOWN", 0)))
    e_post_close.grid(row=3, column=1, sticky="w", padx=5, pady=5)

    # --- [GROUP 4: ⚙️ HỆ THỐNG & TẦN SUẤT (SYSTEM)] ---
    f_sys = ctk.CTkFrame(f_safety, border_width=1, border_color="#757575")
    f_sys.grid(row=3, column=0, columnspan=4, sticky="nsew", padx=5, pady=8)
    ctk.CTkLabel(f_sys, text="⚙️ HỆ THỐNG & TẦN SUẤT (SYSTEM)", text_color="#757575", font=("Roboto", 13, "bold")).pack(pady=5)
    
    f_sys_content = ctk.CTkFrame(f_sys, fg_color="transparent")
    f_sys_content.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(f_sys_content, text="Loop (s):").grid(row=0, column=0, sticky="w", padx=10, pady=5)
    e_daemon_loop = ctk.CTkEntry(f_sys_content, width=50, justify="center")
    e_daemon_loop.insert(0, str(safe_cfg.get("DAEMON_LOOP_DELAY", 15)))
    e_daemon_loop.grid(row=0, column=1, sticky="w", padx=5, pady=5)

    ctk.CTkLabel(f_sys_content, text="Nhồi (s):").grid(row=0, column=2, sticky="w", padx=10, pady=5)
    e_scan_delay = ctk.CTkEntry(f_sys_content, width=50, justify="center")
    e_scan_delay.insert(0, str(safe_cfg.get("DCA_PCA_SCAN_INTERVAL", 2)))
    e_scan_delay.grid(row=0, column=3, sticky="w", padx=5, pady=5)

    ctk.CTkLabel(f_sys_content, text="Nến Trend:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
    e_num_h1 = ctk.CTkEntry(f_sys_content, width=50, justify="center")
    e_num_h1.insert(0, str(safe_cfg.get("NUM_H1_BARS", 70)))
    e_num_h1.grid(row=1, column=1, sticky="w", padx=5, pady=5)

    ctk.CTkLabel(f_sys_content, text="Nến Entry:").grid(row=1, column=2, sticky="w", padx=10, pady=5)
    e_num_m15 = ctk.CTkEntry(f_sys_content, width=50, justify="center")
    e_num_m15.insert(0, str(safe_cfg.get("NUM_M15_BARS", 70)))
    e_num_m15.grid(row=1, column=3, sticky="w", padx=5, pady=5)

    ctk.CTkLabel(f_sys_content, text="Log Spam (M):").grid(row=2, column=0, sticky="w", padx=10, pady=5)
    e_log_cooldown = ctk.CTkEntry(f_sys_content, width=50, justify="center")
    e_log_cooldown.insert(0, str(safe_cfg.get("LOG_COOLDOWN_MINUTES", 60)))
    e_log_cooldown.grid(row=2, column=1, sticky="w", padx=5, pady=5)

    # [HINT / LEGEND AT BOTTOM]
    f_hint = ctk.CTkFrame(f_safety, fg_color="#212121")
    f_hint.grid(row=4, column=0, columnspan=4, sticky="nsew", padx=5, pady=5)
    for text, color in [
        ("Phanh Global", "#F44336"),
        ("Bảo vệ", "#00C853"),
        ("Điều kiện", "#2196F3"),
        ("Hệ thống", "#BDBDBD"),
    ]:
        ctk.CTkLabel(
            f_hint,
            text=f"● {text}",
            font=("Roboto", 10, "italic"),
            text_color=color,
        ).pack(side="left", padx=(10, 2), pady=2)

    def save():
        try:
            import json, os
            import core.storage_manager as storage_manager
            cfg_path = storage_manager.BRAIN_FILE
            existing_data = {}
            if os.path.exists(cfg_path):
                with open(cfg_path, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)

            if "bot_safeguard" not in existing_data:
                existing_data["bot_safeguard"] = {}

            existing_data["bot_safeguard"].update(
                {
                    "MAX_DAILY_LOSS_PERCENT": float(e_max_loss.get()),
                    "MAX_OPEN_POSITIONS": int(e_max_open.get()),
                    "MAX_TRADES_PER_DAY": int(e_max_trades.get()),
                    "MAX_LOSING_STREAK": int(e_max_streak.get()),
                    "LOSS_COUNT_MODE": cbo_loss_mode.get(),
                    "COOLDOWN_MINUTES": int(e_cooldown.get()),
                    "NUM_H1_BARS": int(e_num_h1.get()),
                    "NUM_M15_BARS": int(e_num_m15.get()),
                    "CHECK_PING": var_check_ping.get(),
                    "MAX_PING_MS": int(e_max_ping.get()),
                    "CHECK_SPREAD": var_check_spread.get(),
                    "MAX_SPREAD_POINTS": int(e_max_spread.get()),
                    "DAEMON_LOOP_DELAY": float(e_daemon_loop.get()),
                    "DCA_PCA_SCAN_INTERVAL": float(e_scan_delay.get()),
                    "LOG_COOLDOWN_MINUTES": float(e_log_cooldown.get()),
                    "BOT_USE_SWING_TP": var_bot_use_swing_tp.get(),
                    "BOT_USE_RR_TP": var_bot_use_rr_tp.get(),
                    "BOT_TP_RR_RATIO": float(e_bot_tp_rr.get()),
                    "STRICT_MIN_LOT": var_strict_min_lot.get(),
                    "POST_CLOSE_COOLDOWN": int(e_post_close.get()),
                    "GLOBAL_COOLDOWN_HOURS": float(e_global_cooldown.get()),
                    "APPLY_GLOBAL_COOLDOWN_ON_SAFEGUARD": var_gl_on_sg.get(),
                    "WATERMARK_TRIGGER": float(e_gl_wm_trigger.get()),
                    "WATERMARK_TRIGGER_UNIT": cbo_gl_wm_trigger_unit.get(),
                    "WATERMARK_DRAWDOWN": float(e_gl_wm_drawdown.get()),
                    "WATERMARK_DRAWDOWN_UNIT": cbo_gl_wm_drawdown_unit.get(),
                    "MIN_SL_POINTS": int(e_gl_min_sl.get()),
                    "MAX_BASKET_DRAWDOWN_USD": float(e_gl_basket_dd.get()),
                    "MAX_BASKET_DRAWDOWN_UNIT": cbo_gl_basket_dd_unit.get(),
                    "REJECT_ON_MAX_LOT": var_gl_reject_lot.get(),
                    "GLOBAL_BRAKE_MODE": cbo_brake_mode.get(),
                }
            )

            existing_data["BOT_ACTIVE_SYMBOLS"] = [
                coin for coin, var in app.bot_coin_vars.items() if var.get()
            ]
            config.BOT_ACTIVE_SYMBOLS = existing_data["BOT_ACTIVE_SYMBOLS"]

            with open(cfg_path, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=4)
            
            from core.storage_manager import invalidate_settings_cache
            invalidate_settings_cache()

            if hasattr(app, "reload_config_from_json"):
                app.reload_config_from_json()

            app.log_message("✅ Đã cập nhật đầy đủ Bot Settings.", target="bot")
            top.destroy()
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Lỗi", f"Lỗi lưu cấu hình: {e}", parent=top)

    ctk.CTkButton(
        top,
        text="LƯU CẤU HÌNH BOT SETTINGS",
        fg_color=COL_BLUE_ACCENT,
        height=45,
        font=("Roboto", 13, "bold"),
        command=save,
    ).pack(pady=15, fill="x", padx=40)


# ==============================================================================
# 2. POPUP PRESET (CÓ LIVE PREVIEW ĐẦY ĐỦ)
# ==============================================================================
def open_preset_config_popup(app):
    p_name = app.cbo_preset.get()
    data = config.PRESETS.get(p_name, {})
    top = ctk.CTkToplevel(app)
    top.title(f"Preset: {p_name}")
    top.geometry("430x620")
    top.attributes("-topmost", True)
    # top.transient(app)

    acc = app.connector.get_account_info()
    eq = acc["equity"] if acc else 1000.0
    tick = app.connector.get_market_status(app.cbo_symbol.get())
    cp = tick.get("ask", 1000.0) if isinstance(tick, dict) else 1000.0

    ctk.CTkLabel(top, text=f"PRESET: {p_name}", font=FONT_BOLD).pack(pady=10)
    _add_popup_hint(
        top,
        "- Preset này dùng cho lệnh manual theo preset đang chọn.\n"
        "- Risk % + SL % quyết định lot; TP RR tính lời/lỗ theo R.\n"
        "- SwingPoint nếu bật sẽ ưu tiên cấu trúc giá thay cho % cố định.",
        padx=20,
        pady=(0, 10),
        wraplength=370,
    )

    ctk.CTkLabel(top, text="Risk Per Trade (%):").pack()
    e_risk = ctk.CTkEntry(top, justify="center")
    e_risk.insert(0, str(data.get("RISK_PERCENT", 0.3)))
    e_risk.pack()
    lbl_h_risk = ctk.CTkLabel(
        top, text="~ -$0.00", text_color="gray", font=("Roboto", 11)
    )
    lbl_h_risk.pack(pady=(0, 5))

    ctk.CTkLabel(top, text="Stop Loss (%):").pack()
    e_sl = ctk.CTkEntry(top, justify="center")
    e_sl.insert(0, str(data.get("SL_PERCENT", 0.5)))
    e_sl.pack()
    lbl_h_sl = ctk.CTkLabel(
        top, text="~ Price: 0.00", text_color="gray", font=("Roboto", 11)
    )
    lbl_h_sl.pack(pady=(0, 5))

    ctk.CTkLabel(top, text="Take Profit (RR):").pack()
    e_tp = ctk.CTkEntry(top, justify="center")
    e_tp.insert(0, str(data.get("TP_RR_RATIO", 2.0)))
    e_tp.pack()
    lbl_h_tp = ctk.CTkLabel(
        top, text="~ +$0.00", text_color="gray", font=("Roboto", 11)
    )
    lbl_h_tp.pack(pady=(0, 10))

    # [NEW] Thêm Checkbox Strict Risk (Tính phí Spread/Comm)
    var_strict = ctk.BooleanVar(value=data.get("STRICT_RISK", False))
    chk_strict = ctk.CTkCheckBox(
        top,
        text="Strict Risk (Trừ phí Spread/Comm vào Lot)",
        variable=var_strict,
        text_color="#F44336",
        font=("Roboto", 12, "bold"),
    )
    chk_strict.pack(pady=(5, 10))

    # --- THÊM MỚI TỪ ĐÂY ---
    var_swing_sl = ctk.BooleanVar(value=data.get("USE_SWING_SL", False))
    chk_swing_sl = ctk.CTkCheckBox(
        top,
        text="Dùng SL theo cấu trúc SwingPoint (Giống Bot)",
        variable=var_swing_sl,
        text_color="#29B6F6",
        font=("Roboto", 12, "bold"),
    )
    chk_swing_sl.pack(pady=(0, 10))

    var_swing_tp = ctk.BooleanVar(value=data.get("USE_SWING_TP", False))
    chk_swing_tp = ctk.CTkCheckBox(
        top,
        text="Dùng TP theo cấu trúc SwingPoint (Giống Bot)",
        variable=var_swing_tp,
        text_color="#66BB6A",
        font=("Roboto", 12, "bold"),
    )
    chk_swing_tp.pack(pady=(0, 10))
    # --- KẾT THÚC THÊM MỚI ---

    def live(*args):
        try:
            r, s, t = (
                float(e_risk.get() or 0),
                float(e_sl.get() or 0),
                float(e_tp.get() or 0),
            )
            risk_usd = eq * (r / 100)
            lbl_h_risk.configure(
                text=f"(~ Mất ${risk_usd:.2f} nếu dính SL)", text_color="#EF5350"
            )
            lbl_h_sl.configure(
                text=f"(~ Đặt SL quanh {cp * (1 - s / 100):.2f} cho BUY)",
                text_color="gray",
            )
            lbl_h_tp.configure(
                text=f"(~ Lãi ${risk_usd * t:.2f} nếu chạm TP)", text_color="#66BB6A"
            )
        except ValueError:
            pass

    e_risk.bind("<KeyRelease>", live)
    e_sl.bind("<KeyRelease>", live)
    e_tp.bind("<KeyRelease>", live)
    live()

    def save_preset():
        config.PRESETS[p_name].update(
            {
                "RISK_PERCENT": float(e_risk.get()),
                "SL_PERCENT": float(e_sl.get()),
                "TP_RR_RATIO": float(e_tp.get()),
                "STRICT_RISK": var_strict.get(),
                "USE_SWING_SL": var_swing_sl.get(),  # Lưu biến mới
                "USE_SWING_TP": var_swing_tp.get(),
            }
        )
        app.save_settings()
        top.destroy()

    ctk.CTkButton(top, text="LƯU PRESET", command=save_preset, fg_color=COL_GREEN).pack(
        pady=20, fill="x", padx=30
    )


# ==============================================================================
# 3. POPUP TSL (CÓ BE SOFT/SMART, PNL LEVELS +, STEP R)
# ==============================================================================
def open_tsl_popup(app, override_symbol=None):
    top = ctk.CTkToplevel(app)
    title = "TSL Logic Configuration"
    if override_symbol:
        title += f" - CẤU HÌNH CON: {override_symbol}"
    top.title(title)
    top.geometry("900x780")
    top.minsize(760, 560)
    top.attributes("-topmost", True)
    top.resizable(True, True)  # Khôi phục tính năng co giãn/phóng to
    if override_symbol:
        top.grab_set()  # Modal: Không cho chạm vào UI mẹ khi đang chỉnh UI con

    tsl_cfg = config.TSL_CONFIG.copy()
    if override_symbol:
        from core.storage_manager import get_brain_settings_for_symbol
        brain = get_brain_settings_for_symbol(override_symbol)
        if "TSL_CONFIG" in brain:
            tsl_cfg.update(brain["TSL_CONFIG"])

    # [FIX V4.4] CHIA LÀM 2 TAB GỌN GÀNG THEO YÊU CẦU CỦA BOSS
    tabview = ctk.CTkTabview(top, height=620)
    tabview.pack(fill="both", expand=True, padx=10, pady=5)

    tab_basic_root = tabview.add("Basic (BE, PNL, STEP)")
    tab_adv_root = tabview.add("Advanced (CASH, PSAR)")
    tab_basic = ctk.CTkScrollableFrame(tab_basic_root, fg_color="transparent")
    tab_basic.pack(fill="both", expand=True, padx=4, pady=4)
    tab_adv = ctk.CTkScrollableFrame(tab_adv_root, fg_color="transparent")
    tab_adv.pack(fill="both", expand=True, padx=4, pady=4)
    
    if not override_symbol:
        tab_ow = tabview.add("Overwrite (Mẹ-Con)")

    def sec(parent, t):
        ctk.CTkLabel(
            parent, text=t, font=("Roboto", 12, "bold"), text_color="#03A9F4"
        ).pack(fill="x", padx=15, pady=(10, 2), anchor="w")
        return ctk.CTkFrame(parent, fg_color="transparent")

    # ================= TAB 1: BASIC =================
    _add_popup_hint(
        tab_basic,
        "- BE kéo SL về hòa/lãi nhẹ khi đạt R trigger.\n"
        "- PNL Levels khóa lãi theo % win; STEP R bám theo từng bậc R.\n"
        "- Chỉ tactic được bật ở lệnh/Bot TSL mới dùng các tham số này.",
        padx=15,
        pady=(10, 5),
        wraplength=400,
    )
    f_be = sec(tab_basic, "1. BREAK-EVEN (BE)")
    f_be.pack(fill="x", padx=15)
    cbo_be = ctk.CTkOptionMenu(f_be, values=["SOFT", "SMART"], width=100)
    cbo_be.set(tsl_cfg.get("BE_MODE", "SOFT"))
    cbo_be.pack(side="right")
    e_be_rr = ctk.CTkEntry(f_be, width=50)
    e_be_rr.insert(0, str(tsl_cfg.get("BE_OFFSET_RR", 0.8)))
    e_be_rr.pack(side="left", padx=5)
    ctk.CTkLabel(f_be, text="Trigger(R):").pack(side="left")

    f_pnl = sec(tab_basic, "2. KHÓA LÃI PNL (LEVELS)")
    f_pnl.pack(fill="both", expand=True, padx=15)
    scroll_pnl = ctk.CTkScrollableFrame(f_pnl, height=100)
    scroll_pnl.pack(fill="both", expand=True)
    pnl_entries = []

    def add_p(v1=0.0, v2=0.0):
        r = ctk.CTkFrame(scroll_pnl, fg_color="transparent")
        r.pack(fill="x", pady=2)
        e1, e2 = ctk.CTkEntry(r, width=60), ctk.CTkEntry(r, width=60)
        e1.insert(0, str(v1))
        e1.pack(side="left")
        ctk.CTkLabel(r, text="% Win -> Lock %").pack(side="left", padx=5)
        e2.insert(0, str(v2))
        e2.pack(side="right")
        pnl_entries.append((r, e1, e2))

    for lvl in tsl_cfg.get("PNL_LEVELS", []):
        add_p(lvl[0], lvl[1])

    f_pbtns = ctk.CTkFrame(f_pnl, fg_color="transparent")
    f_pbtns.pack(fill="x")
    ctk.CTkButton(f_pbtns, text="+", width=40, command=lambda: add_p(0.0, 0.0)).pack(
        side="left", padx=5
    )
    ctk.CTkButton(
        f_pbtns,
        text="-",
        width=40,
        command=lambda: pnl_entries.pop()[0].destroy() if pnl_entries else None,
    ).pack(side="right", padx=5)

    f_step = sec(tab_basic, "3. STEP R (TRAIL)")
    f_step.pack(fill="x", padx=15)
    e_sz = ctk.CTkEntry(f_step, width=50)
    e_sz.insert(0, str(tsl_cfg.get("STEP_R_SIZE", 1.0)))
    e_sz.pack(side="left", padx=5)
    e_rt = ctk.CTkEntry(f_step, width=50)
    e_rt.insert(0, str(tsl_cfg.get("STEP_R_RATIO", 0.8)))
    e_rt.pack(side="right", padx=5)
    ctk.CTkLabel(f_step, text="Size(R):").pack(side="left")
    ctk.CTkLabel(f_step, text="Lock(0-1):").pack(side="right", padx=5)

    # ================= TAB 2: ADVANCED =================
    _add_popup_hint(
        tab_adv,
        "- Swing/PSAR dùng group được chọn để bám cấu trúc giá.\n"
        "- CASH trail khóa lãi theo USD/Percent/Point; One-Time chỉ khóa một lần.\n"
        "- ANTI CASH giữ tên cũ nhưng có thêm MAE/MFE theo từng ticket.\n"
        "- MAE = âm sâu nhất của ticket; MFE = lời cao nhất của ticket.\n"
        "- Hard Stop là cầu dao lỗ; MFE Giveback chống trả lại lợi nhuận.",
        padx=15,
        pady=(10, 5),
        wraplength=400,
    )
    f_swing_man = sec(tab_adv, "4. MANUAL SWING (Bám nến)")
    f_swing_man.pack(fill="x", padx=15)
    cbo_swing_grp = ctk.CTkOptionMenu(
        f_swing_man, values=["G0", "G1", "G2", "G3", "DYNAMIC-G1/G2"], width=100
    )
    cbo_swing_grp.set(tsl_cfg.get("SWING_GROUP", "G2"))
    cbo_swing_grp.pack(side="right")
    ctk.CTkLabel(f_swing_man, text="Group Theo Dõi:").pack(side="left")

    f_cash = sec(tab_adv, "5. BE HARD CASH (Thang cuốn USD/Point/%)")
    f_cash.pack(fill="x", padx=15)

    f_cash_r1 = ctk.CTkFrame(f_cash, fg_color="transparent")
    f_cash_r1.pack(fill="x")
    f_cash_r2 = ctk.CTkFrame(f_cash, fg_color="transparent")
    f_cash_r2.pack(fill="x", pady=(5, 0))
    f_cash_r3 = ctk.CTkFrame(f_cash, fg_color="transparent")
    f_cash_r3.pack(fill="x", pady=(5, 0))

    cbo_cash_type = ctk.CTkOptionMenu(
        f_cash_r1, values=["USD", "PERCENT", "POINT"], width=80
    )
    cbo_cash_type.set(tsl_cfg.get("BE_CASH_TYPE", "USD"))
    cbo_cash_type.pack(side="left", padx=5)

    ctk.CTkLabel(f_cash_r1, text="Trig:").pack(side="left", padx=2)
    e_cash_trig = ctk.CTkEntry(f_cash_r1, width=50)
    e_cash_trig.insert(0, str(tsl_cfg.get("BE_TRIGGER", 10.0)))
    e_cash_trig.pack(side="left", padx=2)

    ctk.CTkLabel(f_cash_r1, text="Step:").pack(side="left", padx=2)
    e_cash_val = ctk.CTkEntry(f_cash_r1, width=50)
    e_cash_val.insert(0, str(tsl_cfg.get("BE_VALUE", 20.0)))
    e_cash_val.pack(side="left", padx=2)

    cbo_cash_strat = ctk.CTkOptionMenu(
        f_cash_r1,
        values=["TRAILING (Gap)", "LOCK (Tight)", "SOFT LOCK (Buffer)"],
        width=145,
    )
    cbo_cash_strat.set(tsl_cfg.get("BE_CASH_STRAT", "TRAILING (Gap)"))
    cbo_cash_strat.pack(side="left", padx=5)

    var_cash_fee_protect = ctk.BooleanVar(
        value=tsl_cfg.get("BE_CASH_FEE_PROTECT", True)
    )
    ctk.CTkCheckBox(
        f_cash_r2, text="Fee Protect", variable=var_cash_fee_protect, width=60
    ).pack(side="left", padx=5)

    var_be_one_time = ctk.BooleanVar(value=tsl_cfg.get("ONE_TIME_BE", False))
    ctk.CTkCheckBox(
        f_cash_r2, text="One-Time (Chỉ khóa mốc 1)", variable=var_be_one_time, width=60
    ).pack(side="left", padx=5)

    ctk.CTkLabel(f_cash_r3, text="Buffer:").pack(side="left", padx=2)
    cbo_cash_buffer_type = ctk.CTkOptionMenu(
        f_cash_r3, values=["USD", "PERCENT", "POINT", "ATR"], width=90
    )
    cbo_cash_buffer_type.set(tsl_cfg.get("BE_CASH_SOFT_BUFFER_TYPE", "USD"))
    cbo_cash_buffer_type.pack(side="left", padx=2)

    e_cash_buffer = ctk.CTkEntry(f_cash_r3, width=55)
    e_cash_buffer.insert(0, str(tsl_cfg.get("BE_CASH_SOFT_BUFFER", 3.0)))
    e_cash_buffer.pack(side="left", padx=2)

    ctk.CTkLabel(f_cash_r3, text="Min Lock:").pack(side="left", padx=(10, 2))
    e_cash_min_lock = ctk.CTkEntry(f_cash_r3, width=55)
    e_cash_min_lock.insert(0, str(tsl_cfg.get("BE_CASH_MIN_LOCK", 0.0)))
    e_cash_min_lock.pack(side="left", padx=2)

    ctk.CTkLabel(
        f_cash,
        text="SOFT LOCK: khóa = target - buffer; Min Lock là sàn khóa tối thiểu nếu kết quả còn dương.",
        text_color="#B0BEC5",
        font=("Roboto", 11, "italic"),
        wraplength=440,
    ).pack(anchor="w", padx=8, pady=(4, 0))

    f_psar = sec(tab_adv, "6. PSAR TRAILING (Đuổi chấm)")
    f_psar.pack(fill="x", padx=15)

    f_psar_row1 = ctk.CTkFrame(f_psar, fg_color="transparent")
    f_psar_row1.pack(fill="x", pady=2)
    cbo_psar_grp = ctk.CTkOptionMenu(
        f_psar_row1, values=["G0", "G1", "G2", "G3", "DYNAMIC-G1/G2"], width=80
    )
    cbo_psar_grp.set(tsl_cfg.get("PSAR_GROUP", "G2"))
    cbo_psar_grp.pack(side="right")
    ctk.CTkLabel(f_psar_row1, text="Group:").pack(side="left")

    f_psar_row2 = ctk.CTkFrame(f_psar, fg_color="transparent")
    f_psar_row2.pack(fill="x", pady=2)
    e_psar_step = ctk.CTkEntry(f_psar_row2, width=60)
    e_psar_step.insert(0, str(tsl_cfg.get("PSAR_STEP", 0.02)))
    e_psar_step.pack(side="left", padx=5)
    e_psar_max = ctk.CTkEntry(f_psar_row2, width=60)
    e_psar_max.insert(0, str(tsl_cfg.get("PSAR_MAX", 0.2)))
    e_psar_max.pack(side="right", padx=5)
    ctk.CTkLabel(f_psar_row2, text="Step:").pack(side="left")
    ctk.CTkLabel(f_psar_row2, text="Max:").pack(side="right")

    f_psar_row3 = ctk.CTkFrame(f_psar, fg_color="transparent")
    f_psar_row3.pack(fill="x", pady=2)
    e_psar_min_rr = ctk.CTkEntry(f_psar_row3, width=60)
    e_psar_min_rr.insert(0, str(tsl_cfg.get("PSAR_MIN_RR", 0.0)))
    e_psar_min_rr.pack(side="left", padx=5)
    ctk.CTkLabel(f_psar_row3, text="Min RR kích hoạt:").pack(side="left")

    f_anti = sec(tab_adv, "7. ANTI CASH")
    f_anti.pack(fill="x", padx=15)
    _add_popup_hint(
        f_anti,
        "- Hard Stop: cắt lỗ cứng theo ngưỡng đã chọn.\n"
        "- MAE Guard: chỉ cắt khi lệnh âm đủ sâu, giữ đủ lâu và MFE cao nhất vẫn thấp hơn Low MFE.\n"
        "- MFE Guard: bảo vệ lãi nổi, cắt khi lệnh trả lại quá nhiều hoặc tụt về Floor.",
        padx=8,
        pady=(4, 8),
        wraplength=820,
    )

    def anti_field(parent, row, col, label, value, width=82):
        ctk.CTkLabel(parent, text=label).grid(
            row=row, column=col, padx=(8, 4), pady=6, sticky="e"
        )
        entry = ctk.CTkEntry(parent, width=width)
        entry.insert(0, str(value))
        entry.grid(row=row, column=col + 1, padx=(0, 10), pady=6, sticky="w")
        return entry

    def anti_money_field(parent, row, col, label, value, unit):
        entry = anti_field(parent, row, col, label, value, width=74)
        unit_menu = ctk.CTkOptionMenu(parent, values=["USD", "%R", "%Equity"], width=86)
        unit_menu.set(unit or "USD")
        unit_menu.grid(row=row, column=col + 2, padx=(0, 12), pady=6, sticky="w")
        return entry, unit_menu

    f_anti_grid = ctk.CTkFrame(f_anti, fg_color="transparent")
    f_anti_grid.pack(fill="x", pady=(4, 2))
    for col in range(10):
        f_anti_grid.grid_columnconfigure(col, weight=0)

    e_anti_usd, cbo_anti_usd_unit = anti_money_field(
        f_anti_grid,
        0,
        0,
        "Hard Stop:",
        tsl_cfg.get("ANTI_CASH_USD", 10.0),
        tsl_cfg.get("ANTI_CASH_HARD_STOP_UNIT", "USD"),
    )

    e_anti_time = anti_field(
        f_anti_grid, 0, 3, "Time Cut (s):", tsl_cfg.get("ANTI_CASH_TIME", 60), width=86
    )

    var_anti_time_en = ctk.BooleanVar(
        value=tsl_cfg.get("ANTI_CASH_TIME_ENABLE", True)
    )
    ctk.CTkCheckBox(
        f_anti_grid, text="Dùng Time Cut", variable=var_anti_time_en, width=130
    ).grid(row=0, column=5, padx=(6, 10), pady=6, sticky="w")

    var_anti_mae_en = ctk.BooleanVar(value=tsl_cfg.get("ANTI_CASH_MAE_ENABLE", True))
    ctk.CTkCheckBox(f_anti_grid, text="MAE Guard", variable=var_anti_mae_en, width=120).grid(row=1, column=0, columnspan=2, padx=(8, 10), pady=6, sticky="w")
    e_anti_mae_loss, cbo_anti_mae_loss_unit = anti_money_field(
        f_anti_grid,
        1,
        2,
        "Max Loss:",
        tsl_cfg.get("ANTI_CASH_MAE_MAX_LOSS_USD", 25.0),
        tsl_cfg.get("ANTI_CASH_MAE_MAX_LOSS_UNIT", "USD"),
    )
    e_anti_mae_hold = anti_field(
        f_anti_grid, 1, 5, "Hold(s):", tsl_cfg.get("ANTI_CASH_MAE_MIN_HOLD_SEC", 300), width=86
    )
    e_anti_mae_low_mfe, cbo_anti_mae_low_mfe_unit = anti_money_field(
        f_anti_grid,
        1,
        7,
        "Low MFE:",
        tsl_cfg.get("ANTI_CASH_MAE_LOW_MFE_USD", 5.0),
        tsl_cfg.get("ANTI_CASH_MAE_LOW_MFE_UNIT", "USD"),
    )

    var_anti_mfe_en = ctk.BooleanVar(value=tsl_cfg.get("ANTI_CASH_MFE_ENABLE", True))
    ctk.CTkCheckBox(f_anti_grid, text="MFE Guard", variable=var_anti_mfe_en, width=120).grid(row=2, column=0, columnspan=2, padx=(8, 10), pady=6, sticky="w")
    e_anti_mfe_trig, cbo_anti_mfe_trig_unit = anti_money_field(
        f_anti_grid,
        2,
        2,
        "Trigger:",
        tsl_cfg.get("ANTI_CASH_MFE_TRIGGER_USD", 30.0),
        tsl_cfg.get("ANTI_CASH_MFE_TRIGGER_UNIT", "USD"),
    )
    e_anti_mfe_giveback, cbo_anti_mfe_giveback_unit = anti_money_field(
        f_anti_grid,
        2,
        5,
        "Giveback:",
        tsl_cfg.get("ANTI_CASH_MFE_GIVEBACK_USD", 20.0),
        tsl_cfg.get("ANTI_CASH_MFE_GIVEBACK_UNIT", "USD"),
    )
    e_anti_mfe_floor, cbo_anti_mfe_floor_unit = anti_money_field(
        f_anti_grid,
        2,
        7,
        "Floor:",
        tsl_cfg.get("ANTI_CASH_MFE_FLOOR_USD", 0.0),
        tsl_cfg.get("ANTI_CASH_MFE_FLOOR_UNIT", "USD"),
    )

    e_anti_reentry = anti_field(
        f_anti_grid, 3, 0, "Re-entry Lock(s):", tsl_cfg.get("ANTI_CASH_REENTRY_LOCK_SEC", 900), width=86
    )
    ctk.CTkLabel(
        f_anti_grid,
        text="sau khi ANTI CASH cắt cùng chiều",
        text_color="#BDBDBD",
    ).grid(row=3, column=2, columnspan=4, padx=(0, 10), pady=6, sticky="w")

    def save():
        try:
            output_tsl = {
                "BE_CASH_TYPE": cbo_cash_type.get(),
                "BE_TRIGGER": float(e_cash_trig.get()),
                "BE_VALUE": float(e_cash_val.get()),
                "BE_CASH_STRAT": cbo_cash_strat.get(),
                "BE_CASH_FEE_PROTECT": var_cash_fee_protect.get(),
                "BE_CASH_SOFT_BUFFER_TYPE": cbo_cash_buffer_type.get(),
                "BE_CASH_SOFT_BUFFER": float(e_cash_buffer.get()),
                "BE_CASH_MIN_LOCK": float(e_cash_min_lock.get()),
                "BE_MODE": cbo_be.get(),
                "BE_OFFSET_RR": float(e_be_rr.get()),
                "ONE_TIME_BE": var_be_one_time.get(),
                "PNL_LEVELS": sorted(
                    [
                        [float(e1.get()), float(e2.get())]
                        for r, e1, e2 in pnl_entries
                        if e1.get()
                    ],
                    key=lambda x: x[0],
                ),
                "STEP_R_SIZE": float(e_sz.get()),
                "STEP_R_RATIO": float(e_rt.get()),
                "SWING_GROUP": cbo_swing_grp.get(),
                "PSAR_GROUP": cbo_psar_grp.get(),
                "PSAR_STEP": float(e_psar_step.get()),
                "PSAR_MAX": float(e_psar_max.get()),
                "PSAR_MIN_RR": float(e_psar_min_rr.get()),
                "ANTI_CASH_USD": float(e_anti_usd.get()),
                "ANTI_CASH_HARD_STOP_UNIT": cbo_anti_usd_unit.get(),
                "ANTI_CASH_TIME": int(e_anti_time.get()),
                "ANTI_CASH_TIME_ENABLE": var_anti_time_en.get(),
                "ANTI_CASH_MAE_ENABLE": var_anti_mae_en.get(),
                "ANTI_CASH_MAE_MAX_LOSS_USD": float(e_anti_mae_loss.get()),
                "ANTI_CASH_MAE_MAX_LOSS_UNIT": cbo_anti_mae_loss_unit.get(),
                "ANTI_CASH_MAE_MIN_HOLD_SEC": int(e_anti_mae_hold.get()),
                "ANTI_CASH_MAE_LOW_MFE_USD": float(e_anti_mae_low_mfe.get()),
                "ANTI_CASH_MAE_LOW_MFE_UNIT": cbo_anti_mae_low_mfe_unit.get(),
                "ANTI_CASH_MFE_ENABLE": var_anti_mfe_en.get(),
                "ANTI_CASH_MFE_TRIGGER_USD": float(e_anti_mfe_trig.get()),
                "ANTI_CASH_MFE_TRIGGER_UNIT": cbo_anti_mfe_trig_unit.get(),
                "ANTI_CASH_MFE_GIVEBACK_USD": float(e_anti_mfe_giveback.get()),
                "ANTI_CASH_MFE_GIVEBACK_UNIT": cbo_anti_mfe_giveback_unit.get(),
                "ANTI_CASH_MFE_FLOOR_USD": float(e_anti_mfe_floor.get()),
                "ANTI_CASH_MFE_FLOOR_UNIT": cbo_anti_mfe_floor_unit.get(),
                "ANTI_CASH_REENTRY_LOCK_SEC": int(e_anti_reentry.get()),
            }
            
            if override_symbol:
                from core.storage_manager import load_symbol_overrides, save_symbol_overrides
                overrides = load_symbol_overrides()
                if override_symbol not in overrides:
                    overrides[override_symbol] = {}
                if "tsl" not in overrides[override_symbol]:
                    overrides[override_symbol]["tsl"] = {}
                overrides[override_symbol]["tsl"]["TSL_CONFIG"] = output_tsl
                save_symbol_overrides(overrides)
                app.log_message(f"✅ TSL Override Saved for {override_symbol}.", target="bot")
                top.destroy()
                return

            config.TSL_CONFIG.update(output_tsl)
            app.save_settings()
            app.log_message("✅ TSL Saved.", target="bot")
            top.destroy()
        except:
            messagebox.showerror("Lỗi", "Cấu hình sai!", parent=top)

    ctk.CTkButton(
        top,
        text="LƯU TSL LOGIC",
        fg_color=COL_GREEN,
        height=48,
        font=("Roboto", 14, "bold"),
        command=save,
    ).pack(pady=(8, 16), fill="x", padx=70)

    if override_symbol:
        def reset_tsl_override():
            from core.storage_manager import load_symbol_overrides, save_symbol_overrides
            overrides = load_symbol_overrides()
            if override_symbol in overrides and "tsl" in overrides[override_symbol]:
                del overrides[override_symbol]["tsl"]
                save_symbol_overrides(overrides)
                app.log_message(f"✅ TSL Override Reset for {override_symbol}.", target="bot")
                top.destroy()
                
        ctk.CTkButton(
            top,
            text="🗑️ RESET (VỀ MẶC ĐỊNH)",
            fg_color="#D50000",
            hover_color="#B71C1C",
            height=40,
            font=FONT_BOLD,
            command=reset_tsl_override,
        ).pack(pady=(0, 15), fill="x", padx=40)
        
    if not override_symbol:
        def build_overwrite_tab():
            f = ctk.CTkScrollableFrame(tab_ow)
            f.pack(fill="both", expand=True, padx=5, pady=5)
            
            ctk.CTkLabel(f, text="CẤU HÌNH GHI ĐÈ (PER-SYMBOL OVERRIDE)", font=("Roboto", 14, "bold")).pack(pady=10)
            _add_popup_hint(
                f,
                "- Symbol có override sẽ dùng TSL riêng thay cho Global.\n"
                "- Reset override = xóa TSL con, quay về TSL mẹ.\n"
                "- Override chỉ áp dụng cho symbol được chọn.",
                padx=10,
                pady=(0, 10),
                wraplength=400,
            )
            
            grid_frame = ctk.CTkFrame(f, fg_color="transparent")
            grid_frame.pack(pady=10)
            
            from core.storage_manager import get_brain_settings_for_symbol
            from core.storage_manager import load_symbol_overrides
            
            brain = get_brain_settings_for_symbol()
            symbols = getattr(config, "COIN_LIST", [])
            overrides = load_symbol_overrides()
    
            row, col = 0, 0
            for sym in symbols:
                has_override = sym in overrides and "tsl" in overrides[sym]
                color = "#00C853" if has_override else "#424242"
                btn = ctk.CTkButton(
                    grid_frame,
                    text=f"{sym} {'(Có)' if has_override else ''}",
                    fg_color=color,
                    command=lambda s=sym: open_tsl_popup(app, s)
                )
                btn.grid(row=row, column=col, padx=5, pady=5)
                col += 1
                if col > 3:
                    col = 0
                    row += 1
        build_overwrite_tab()


# ==============================================================================
# 4. POPUP EDIT ORDER (FULL FEATURES: MATH SL, PRESET TP, DCA/PCA, TACTIC TOGGLES)
# ==============================================================================
def open_edit_popup(app, ticket):
    pos = next(
        (p for p in app.connector.get_all_open_positions() if p.ticket == ticket), None
    )
    if not pos:
        return
    top = ctk.CTkToplevel(app)
    top.title(f"Sửa lệnh #{ticket}")
    top.geometry("450x760")
    top.attributes("-topmost", True)
    # top.transient(app)

    is_buy = pos.type == 0
    bal = (
        app.connector.get_account_info()["balance"]
        if app.connector.get_account_info()
        else 1000.0
    )

    ctk.CTkLabel(top, text="NEW SL:", font=FONT_BOLD).pack(pady=(10, 2))
    e_sl = ctk.CTkEntry(top, justify="center")
    e_sl.insert(0, str(pos.sl))
    e_sl.pack()
    lbl_h_sl = ctk.CTkLabel(
        top, text="~ -$0.00", text_color="gray", font=("Roboto", 11)
    )
    lbl_h_sl.pack(pady=(0, 5))

    ctk.CTkLabel(top, text="NEW TP:", font=FONT_BOLD).pack(pady=(5, 2))
    e_tp = ctk.CTkEntry(top, justify="center")
    e_tp.insert(0, str(pos.tp))
    e_tp.pack()
    lbl_h_tp = ctk.CTkLabel(
        top, text="~ +$0.00", text_color="gray", font=("Roboto", 11)
    )
    lbl_h_tp.pack(pady=(0, 5))

    # Khung chứa Live Tactic Preview
    f_tactic_preview = ctk.CTkFrame(top, fg_color="#1a1a1a", corner_radius=6)
    f_tactic_preview.pack(fill="x", padx=20, pady=5)
    lbl_tactic_preview = ctk.CTkLabel(
        f_tactic_preview,
        text="TSL Preview",
        text_color="#29B6F6",
        font=("Consolas", 12),
    )
    lbl_tactic_preview.pack(pady=5)

    cur_t = app.trade_mgr.get_trade_tactic(ticket)
    states = {
        "BE_C": "BE_CASH" in cur_t,
        "PSAR": "PSAR_TRAIL" in cur_t,
        "BE": "BE" in cur_t and "BE_CASH" not in cur_t,
        "PNL": "PNL" in cur_t,
        "STEP": "STEP_R" in cur_t,
        "SWING": "SWING" in cur_t,
        "REV_C": "REV_C" in cur_t,  # [FIX] Nút Close on Reverse
        "ANTI_CASH": "ANTI_CASH" in cur_t,  # [NEW]
    }

    def live_edit(*args):
        try:
            nsl, ntp = float(e_sl.get() or 0), float(e_tp.get() or 0)
            if nsl > 0:
                dist = abs(pos.price_open - nsl)
                loss = dist * pos.volume * 1.0  # Simple Contract Size
                lbl_h_sl.configure(
                    text=f"~ -${loss:.2f} ({loss / bal * 100:.2f}%)",
                    text_color="#EF5350",
                )
            if ntp > 0:
                p_dist = abs(pos.price_open - ntp)
                prof = p_dist * pos.volume * 1.0
                lbl_h_tp.configure(text=f"~ +${prof:.2f}", text_color="#66BB6A")
            else:
                lbl_h_tp.configure(text="~ Thả rông (Vô cực)", text_color="#29B6F6")

            # Cập nhật Live Trigger Price Preview
            if nsl > 0:
                r_dist = abs(pos.price_open - nsl)
                if r_dist > 0:
                    preview_txts = []
                    if states["BE"]:
                        trig_r = config.TSL_CONFIG.get("BE_OFFSET_RR", 0.8)
                        trig_p = (
                            pos.price_open + (trig_r * r_dist)
                            if is_buy
                            else pos.price_open - (trig_r * r_dist)
                        )
                        preview_txts.append(f"BE @ {trig_p:.2f}")
                    if states["STEP"]:
                        sz = config.TSL_CONFIG.get("STEP_R_SIZE", 1.0)
                        trig_p = (
                            pos.price_open + (sz * r_dist)
                            if is_buy
                            else pos.price_open - (sz * r_dist)
                        )
                        preview_txts.append(f"Step 1 @ {trig_p:.2f}")
                    if states["PNL"] and config.TSL_CONFIG.get("PNL_LEVELS"):
                        lvl = config.TSL_CONFIG["PNL_LEVELS"][0]
                        preview_txts.append(f"PNL @ Lãi {lvl[0]}%")
                    if states["SWING"]:
                        preview_txts.append("SWING (Đuổi theo nến H1/M15)")
                    if states["BE_C"]:
                        preview_txts.append(
                            f"CASH TRAIL Bậc thang (Step: {config.TSL_CONFIG.get('BE_VALUE', 5)})"
                        )
                    if states["PSAR"]:
                        preview_txts.append("PSAR TRAIL")
                    if states["REV_C"]:
                        preview_txts.append("Close on Reverse")
                    if states["ANTI_CASH"]:
                        preview_txts.append("Anti-Cash")

                    if preview_txts:
                        lbl_tactic_preview.configure(
                            text="Dự kiến Trigger TSL:\n" + " | ".join(preview_txts)
                        )
                    else:
                        lbl_tactic_preview.configure(text="TSL: OFF")
        except:
            pass

    e_sl.bind("<KeyRelease>", live_edit)
    e_tp.bind("<KeyRelease>", live_edit)

    # [UPGRADED] Math SL với dropdown chọn Group
    f_math = ctk.CTkFrame(top, fg_color="#1a1a1a", corner_radius=6)
    f_math.pack(fill="x", padx=20, pady=(5, 0))

    ctk.CTkLabel(
        f_math, text="TREND/RANGE Group:", font=("Roboto", 11), text_color="gray"
    ).pack(side="left", padx=(8, 4))
    var_sl_group = ctk.StringVar(value="G2")
    cbo_sl_group = ctk.CTkOptionMenu(
        f_math,
        values=["G0", "G1", "G2", "G3", "DYNAMIC-G1/G2"],
        variable=var_sl_group,
        width=130,
        height=26,
        fg_color="#2b2b2b",
        button_color="#1565C0",
        command=lambda _: do_math(),
    )
    cbo_sl_group.pack(side="left", padx=4)

    def do_math():
        ctx = app.latest_market_context.get(pos.symbol, {})
        group = var_sl_group.get()

        # Xử lý DYNAMIC: tự chọn group dựa trên Market Mode
        if "DYNAMIC" in group:
            mode = ctx.get("market_mode", "ANY")
            group = "G1" if mode in ["TREND", "BREAKOUT"] else "G2"
            var_sl_group.set(f"→{group}")  # Hiển thị group thực tế đã chọn

        val = ctx.get(f"swing_low_{group}" if is_buy else f"swing_high_{group}")
        atr_val = ctx.get(f"atr_{group}")

        if val and str(val) != "--" and atr_val:
            brain = app.trade_mgr._get_brain_settings()
            mult = float(
                brain.get("risk_tsl", {}).get(
                    "sl_atr_multiplier", getattr(config, "sl_atr_multiplier", 0.2)
                )
            )
            calc_sl = (
                float(val) - (float(atr_val) * mult)
                if is_buy
                else float(val) + (float(atr_val) * mult)
            )
            e_sl.delete(0, "end")
            e_sl.insert(0, f"{calc_sl:.5f}")
            do_tp()  # Tự động cập nhật TP theo SL mới
            live_edit()
        else:
            messagebox.showwarning(
                "Không có dữ liệu",
                f"Không tìm thấy Swing/ATR của {group} cho {pos.symbol}.\nThử chọn Group khác.",
                parent=top
            )

    ctk.CTkButton(
        f_math,
        text="Lấy Math SL",
        height=26,
        fg_color="#1565C0",
        hover_color="#0D47A1",
        font=("Roboto", 12, "bold"),
        command=do_math,
    ).pack(side="left", padx=8, pady=4)

    f_ast = ctk.CTkFrame(top, fg_color="transparent")
    f_ast.pack(pady=(6, 0))

    def do_tp():
        try:
            rr = config.PRESETS.get(app.cbo_preset.get(), {}).get("TP_RR_RATIO", 1.5)
            tp = pos.price_open + (
                abs(pos.price_open - float(e_sl.get())) * rr
                if is_buy
                else -abs(pos.price_open - float(e_sl.get())) * rr
            )
            e_tp.delete(0, "end")
            e_tp.insert(0, f"{tp:.5f}")
            live_edit()
        except:
            pass

    def do_clear_tp():
        e_tp.delete(0, "end")
        e_tp.insert(0, "0.0")
        live_edit()

    def do_swing_tp():
        ctx = app.latest_market_context.get(pos.symbol, {})
        group = var_sl_group.get()
        if "DYNAMIC" in group:
            mode = ctx.get("market_mode", "ANY")
            group = "G1" if mode in ["TREND", "BREAKOUT"] else "G2"
        
        val = ctx.get(f"swing_high_{group}" if is_buy else f"swing_low_{group}")
        atr_val = ctx.get(f"atr_{group}")
        
        if val and str(val) != "--" and atr_val:
            brain = app.trade_mgr._get_brain_settings()
            mult = float(brain.get("risk_tsl", {}).get("sl_atr_multiplier", 0.2))
            calc_tp = float(val) - (float(atr_val) * mult) if is_buy else float(val) + (float(atr_val) * mult)
            e_tp.delete(0, "end")
            e_tp.insert(0, f"{calc_tp:.5f}")
            live_edit()
        else:
            messagebox.showwarning("Lỗi", "Không có dữ liệu Swing TP", parent=top)

    ctk.CTkButton(
        f_ast, text="Lấy Preset TP", width=105, fg_color="#2E7D32", command=do_tp
    ).pack(side="left", padx=2)

    ctk.CTkButton(
        f_ast, text="Lấy Swing TP", width=105, fg_color="#66BB6A", command=do_swing_tp
    ).pack(side="left", padx=2)

    ctk.CTkButton(
        f_ast, text="Bỏ TP (Vô cực)", width=105, fg_color="#455A64", command=do_clear_tp
    ).pack(side="right", padx=2)

    f_chk = ctk.CTkFrame(top, fg_color="transparent")
    f_chk.pack()
    chk_dca, chk_pca = (
        ctk.CTkCheckBox(f_chk, text="Auto DCA", font=("Roboto", 11)),
        ctk.CTkCheckBox(f_chk, text="Auto PCA", font=("Roboto", 11)),
    )
    chk_dca.pack(side="left", padx=10)
    chk_pca.pack(side="left")

    if "AUTO_DCA" in cur_t:
        chk_dca.select()
    if "AUTO_PCA" in cur_t:
        chk_pca.select()

    f_t = ctk.CTkFrame(top, fg_color="transparent")
    f_t.pack(pady=10)
    btns = {}

    def tog(k):
        states[k] = not states[k]
        btns[k].configure(fg_color=COL_BLUE_ACCENT if states[k] else COL_GRAY_BTN)
        live_edit()  # Cập nhật lại Preview ngay khi toggle

    for k in states:
        display_name = "A_CASH" if k == "ANTI_CASH" else k
        btns[k] = ctk.CTkButton(
            f_t,
            text=display_name,
            width=52,
            fg_color=COL_BLUE_ACCENT if states[k] else COL_GRAY_BTN,
            command=lambda x=k: tog(x),
        )
        btns[k].pack(side="left", padx=2)

    live_edit()  # Lần gọi đầu tiên khi mở popup

    def save_e():
        try:
            app.connector.modify_position(ticket, float(e_sl.get()), float(e_tp.get()))
            act = []
            for k, v in states.items():
                if v:
                    if k == "STEP":
                        act.append("STEP_R")
                    elif k == "BE_C":
                        act.append("BE_CASH")
                    elif k == "PSAR":
                        act.append("PSAR_TRAIL")
                    else:
                        act.append(k)
            final_t = "+".join(act) if act else "OFF"
            if chk_dca.get():
                final_t += "+AUTO_DCA"
            if chk_pca.get():
                final_t += "+AUTO_PCA"
            app.trade_mgr.update_trade_tactic(ticket, final_t)
            top.destroy()
        except Exception as e:
            messagebox.showerror("Lỗi", str(e), parent=top)

    ctk.CTkButton(
        top,
        text="CẬP NHẬT LỆNH",
        height=45,
        fg_color="#2e7d32",
        font=FONT_BOLD,
        command=save_e,
    ).pack(pady=20, fill="x", padx=40)


def show_history_popup(app):
    top = ctk.CTkToplevel(app)
    top.title("Lịch sử Giao dịch (Nhóm theo Phiên)")
    top.geometry("900x550")
    top.attributes("-topmost", True)
    top.focus_force()

    # [NEW V5] Mở rộng số cột để hiển thị thêm Entry, SL, TP, Fee
    cols = (
        "Time",
        "Ticket",
        "Symbol",
        "Type",
        "Vol",
        "Entry",
        "SL",
        "TP",
        "Fee",
        "PnL ($)",
        "MAE",
        "MFE",
        "Trigger",
        "Reason",
    )
    tr = ttk.Treeview(top, columns=cols, show="tree headings")

    xscrollbar = ttk.Scrollbar(top, orient="horizontal", command=tr.xview)
    xscrollbar.pack(side="bottom", fill="x")
    tr.configure(xscrollcommand=xscrollbar.set)

    tr.pack(fill="both", expand=True)

    # Cột Tree (chứa Session Name)
    tr.column("#0", width=160, anchor="w")
    tr.heading("#0", text="Session")

    widths = [140, 90, 80, 80, 60, 80, 80, 80, 60, 80, 80, 80, 170, 120]
    for c, w in zip(cols, widths):
        tr.heading(c, text=c)
        tr.column(c, width=w, anchor="center")

    from core.storage_manager import MASTER_LOG_FILE
    csv_path = MASTER_LOG_FILE


    def load_data():
        if not tr.winfo_exists():
            return
        for i in tr.get_children():
            tr.delete(i)

        if not os.path.exists(csv_path):
            return

        sessions = {}
        try:
            with open(csv_path, mode="r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader, None)
                if not header:
                    return

                raw_records = list(reader)
                records_by_ticket = {}
                for row in raw_records:
                    if len(row) < 14:
                        continue
                    records_by_ticket[row[1]] = row
                records = list(records_by_ticket.values())
                for row in records:
                    if len(row) < 14:
                        continue  # Format mới có 14 cột
                    # row format: [Time, Ticket, Symbol, Type, Vol, Entry, SL, TP, Fee, PnL, Reason, Market Mode, Trigger, Session_ID]
                    session_id = row[13]

                    if session_id not in sessions:
                        sessions[session_id] = []
                    sessions[session_id].append(row)

            # Hiển thị Session mới nhất lên trên
            sorted_sessions = sorted(sessions.keys(), reverse=True)

            for sid in sorted_sessions:
                group_rows = sessions[sid]

                # Tính toán Thống kê Session
                wins = 0
                total_trades = 0
                buy_count = 0
                sell_count = 0
                total_pnl = 0.0
                total_fee = 0.0

                for r in group_rows:
                    if len(r) >= 14:
                        pnl_val = (
                            float(r[9])
                            if r[9].replace(".", "", 1).replace("-", "", 1).isdigit()
                            else 0.0
                        )
                        fee_val = (
                            float(r[8])
                            if r[8].replace(".", "", 1).replace("-", "", 1).isdigit()
                            else 0.0
                        )
                        total_pnl += pnl_val
                        total_fee += fee_val

                        if pnl_val > 0:
                            wins += 1
                        total_trades += 1

                        if r[3] == "BUY":
                            buy_count += 1
                        elif r[3] == "SELL":
                            sell_count += 1

                winrate = (wins / total_trades * 100) if total_trades > 0 else 0

                # Thêm Node Cha (Session)
                node_text = f"Phiên: {sid}" if sid != "LEGACY" else "Phiên Cũ (Legacy)"

                # Hiển thị tóm tắt trên node cha
                type_str = f"B:{buy_count} | S:{sell_count}"
                win_str = f"W: {winrate:.1f}%"
                fee_str = f"${total_fee:.2f}"
                pnl_str = f"${total_pnl:.2f}"

                parent_id = tr.insert(
                    "",
                    "end",
                    text=node_text,
                    values=(
                        "",
                        "",
                        "",
                        type_str,
                        win_str,
                        "",
                        "",
                        "",
                        fee_str,
                        pnl_str,
                        "",
                        "",
                        "",
                        "",
                    ),
                )

                # Sắp xếp các lệnh trong phiên từ mới -> cũ
                for row in reversed(group_rows):
                    if len(row) >= 14:
                        tr.insert(
                            parent_id,
                            "end",
                            text="",
                            values=(
                                row[0],
                                row[1],
                                row[2],
                                row[3],
                                row[4],
                                row[5],
                                row[6],
                                row[7],
                                row[8],
                                row[9],
                                row[14] if len(row) > 14 else "",
                                row[15] if len(row) > 15 else "",
                                row[12] if len(row) > 12 else "",
                                row[10],
                            ),
                        )

                # Tự động mở rộng phiên mới nhất
                if sid == sorted_sessions[0]:
                    tr.item(parent_id, open=True)

        except Exception as e:
            pass

    load_data()

    # Thêm Context Menu để xóa Session
    def on_right_click(event):
        row_id = tr.identify_row(event.y)
        if not row_id:
            return

        tr.selection_set(row_id)

        # Kiểm tra xem có phải là Node cha (Session) không
        parent_node = tr.parent(row_id)
        if parent_node == "":  # Đây là node cha
            session_text = tr.item(row_id, "text")
            session_id = session_text.replace("Phiên: ", "").replace(
                "Phiên Cũ (Legacy)", "LEGACY"
            )

            menu = tk.Menu(top, tearoff=0, font=("Roboto", 11))
            menu.add_command(
                label=f"🗑 Xóa Log Phiên [{session_id}]",
                command=lambda: delete_session(session_id),
            )
            menu.post(event.x_root, event.y_root)

    def delete_session(session_id):
        if messagebox.askyesno(
            "Cảnh báo",
            f"Bạn có chắc muốn XÓA VĨNH VIỄN toàn bộ nhật ký của Phiên [{session_id}] không?",
            parent=top
        ):
            from core.storage_manager import delete_session_log

            delete_session_log(session_id)
            app.log_message(
                f"🗑 Đã dọn dẹp log của phiên {session_id}.", target="manual"
            )
            load_data()  # Reload lại Treeview

    tr.bind("<Button-3>", on_right_click)


def open_minibrain_popup(app, title, mb_cfg, on_save_callback):
    """
    [NEW V5.1] Popup cài đặt Mini-Brain 1-Group độc lập cho DCA/PCA
    """
    from tkinter import messagebox
    import customtkinter as ctk
    import config as _cfg

    top = ctk.CTkToplevel()
    top.title(title)
    top.geometry("700x520")
    top.attributes("-topmost", True)
    top.lift()
    top.grab_set()
    top.focus_force()

    f_top = ctk.CTkFrame(top)
    f_top.pack(fill="x", padx=10, pady=10)

    var_active = ctk.BooleanVar(value=mb_cfg.get("active", False))
    ctk.CTkCheckBox(f_top, text="Bật Mini-Brain", variable=var_active, font=("Roboto", 13, "bold")).pack(side="left", padx=10)

    ctk.CTkLabel(f_top, text="Timeframe:").pack(side="left", padx=(20, 5))
    cbo_tf = ctk.CTkComboBox(f_top, values=["1m", "5m", "15m", "30m", "1h", "4h"], width=80)
    cbo_tf.set(mb_cfg.get("timeframe", "15m"))
    cbo_tf.pack(side="left", padx=5)

    f_rules = ctk.CTkFrame(top)
    f_rules.pack(fill="x", padx=10, pady=5)

    ctk.CTkLabel(f_rules, text="Max Opposite (Phiếu ngược tối đa):").pack(side="left", padx=10, pady=5)
    e_max_opp = ctk.CTkEntry(f_rules, width=60, justify="center")
    e_max_opp.insert(0, str(mb_cfg.get("max_opposite", 0)))
    e_max_opp.pack(side="left", padx=5)

    ctk.CTkLabel(f_rules, text="Max None (Phiếu trắng tối đa):").pack(side="left", padx=20, pady=5)
    e_max_none = ctk.CTkEntry(f_rules, width=60, justify="center")
    e_max_none.insert(0, str(mb_cfg.get("max_none", 0)))
    e_max_none.pack(side="left", padx=5)

    f_inds = ctk.CTkFrame(top)
    f_inds.pack(fill="both", expand=True, padx=10, pady=10)
    ctk.CTkLabel(f_inds, text="CHỌN CHỈ BÁO", font=("Roboto", 12, "bold")).pack(pady=5)

    inds_cfg = mb_cfg.get("indicators", {})
    vars_dict = {}

    # Dùng SANDBOX_CONFIG["indicators"] làm nguồn danh sách indicator (không dùng INDICATOR_DEFINITIONS không tồn tại)
    all_indicators = _cfg.SANDBOX_CONFIG.get("indicators", {})
    LABEL_MAP = {
        "adx": "ADX", "ema": "EMA", "swing_point": "Swing Point", "atr": "ATR",
        "pivot_points": "Pivot Points", "ema_cross": "EMA Cross", "volume": "Volume",
        "supertrend": "SuperTrend", "psar": "PSAR", "bollinger_bands": "Bollinger Bands",
        "fibonacci": "Fibonacci", "rsi": "RSI", "stochastic": "Stochastic",
        "macd": "MACD", "multi_candle": "Multi-Candle", "candle": "Candle",
        "simple_breakout": "Simple Breakout",
    }

    grid_f = ctk.CTkFrame(f_inds, fg_color="transparent")
    grid_f.pack(fill="both", expand=True, padx=5, pady=5)

    r, c = 0, 0
    for key in all_indicators.keys():
        is_on = inds_cfg.get(key, {}).get("active", False)
        var = ctk.BooleanVar(value=is_on)
        vars_dict[key] = var
        label = LABEL_MAP.get(key, key.upper())
        ctk.CTkCheckBox(grid_f, text=label, variable=var).grid(row=r, column=c, sticky="w", padx=10, pady=5)
        c += 1
        if c > 2:
            c = 0
            r += 1

    def save_mb():
        try:
            new_cfg = {
                "active": var_active.get(),
                "timeframe": cbo_tf.get(),
                "max_opposite": int(e_max_opp.get()),
                "max_none": int(e_max_none.get()),
                "indicators": {}
            }
            for k, v in vars_dict.items():
                if v.get():
                    # Chỉ lưu trạng thái active, không lưu cứng params để Mini-Brain tự mượn params từ Sandbox
                    new_cfg["indicators"][k] = {"active": True}
            on_save_callback(new_cfg)
            top.destroy()
        except ValueError as e:
            messagebox.showerror("Lỗi", f"Vui lòng nhập số hợp lệ: {e}", parent=top)

    ctk.CTkButton(top, text="LƯU MINI-BRAIN", fg_color="#FBC02D", text_color="#212121",
                  font=("Roboto", 13, "bold"), command=save_mb).pack(pady=10)
