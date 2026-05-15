# -*- coding: utf-8 -*-
# FILE: ui_panels.py
# V8.4.1: UPDATED UI PANELS - OPTIMIZED TOP HEADER & CONTEXT PREVIEW (KAISER EDITION)

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import config

# --- HẰNG SỐ UI ---
FONT_MAIN = ("Roboto", 13)
FONT_BOLD = ("Roboto", 13, "bold")
FONT_EQUITY = ("Roboto", 36, "bold")
FONT_PNL = ("Roboto", 18, "bold")
FONT_SECTION = ("Roboto", 12, "bold")
FONT_BIG_VAL = ("Consolas", 20, "bold")
FONT_PRICE = ("Roboto", 32, "bold")
FONT_FEE = ("Roboto", 13, "bold")

COL_GREEN = "#00C853"
COL_RED = "#D50000"
COL_BLUE_ACCENT = "#1565C0"
COL_WARN = "#FFAB00"
COL_BOT_TAG = "#E040FB"


def setup_left_panel(app, parent):
    """Xây dựng toàn bộ thanh điều khiển bên trái"""

    # 1. TOP HEADER (Equity & Info) - REWORKED LAYOUT
    f_top = ctk.CTkFrame(parent, fg_color="#1a1a1a", corner_radius=8)
    f_top.pack(fill="x", pady=(5, 5), padx=5)

    # Khung trên: Equity & ID/Server
    f_top_1 = ctk.CTkFrame(f_top, fg_color="transparent")
    f_top_1.pack(fill="x", padx=5, pady=(5, 0))

    app.lbl_equity = ctk.CTkLabel(
        f_top_1, text="$----", font=FONT_EQUITY, text_color=COL_GREEN
    )
    app.lbl_equity.pack(side="left", padx=5)

    app.lbl_acc_info = ctk.CTkLabel(
        f_top_1,
        text="ID: --- \nServer: ---",
        font=("Roboto", 10),
        text_color="gray",
        justify="right",
    )
    app.lbl_acc_info.pack(side="right", padx=5, anchor="e")

    # Khung dưới: PNL & Brain Status
    f_top_2 = ctk.CTkFrame(f_top, fg_color="transparent")
    f_top_2.pack(fill="x", padx=5, pady=(0, 5))

    f_pnl = ctk.CTkFrame(f_top_2, fg_color="transparent")
    f_pnl.pack(side="left")

    app.lbl_stats = ctk.CTkLabel(
        f_pnl, text="PNL: $0.00", font=FONT_PNL, text_color="white"
    )
    app.lbl_stats.pack(side="left", padx=5)

    ctk.CTkButton(
        f_pnl,
        text="⟳",
        width=25,
        height=20,
        fg_color="#333",
        hover_color="#444",
        command=app.reset_daily_stats,
    ).pack(side="left", padx=2)

    app.lbl_fee_today = ctk.CTkLabel(
        f_pnl, text="FEE: -$0.00", font=FONT_FEE, text_color="gray"
    )
    app.lbl_fee_today.pack(side="left", padx=(8, 0))

    app.lbl_brain_status = ctk.CTkLabel(
        f_top_2,
        text="🧠 BRAIN: CHỜ...",
        font=("Roboto", 11, "bold"),
        text_color="#FF8F00",
    )
    app.lbl_brain_status.pack(side="right", padx=5)

    # 2. SETTINGS PANEL (Coin, Mode, Tactic)
    f_set = ctk.CTkFrame(parent, fg_color="transparent")
    f_set.pack(fill="x", padx=5, pady=5)
    f_set.columnconfigure(0, minsize=74)
    f_set.columnconfigure(1, weight=1)

    # --- DÒNG 1: COIN & CẤU HÌNH BOT & SANDBOX ---
    ctk.CTkLabel(f_set, text="COIN:", font=FONT_SECTION, text_color="#D7DCE2").grid(
        row=0, column=0, sticky="e", padx=(0, 8)
    )
    f_coin_row = ctk.CTkFrame(f_set, fg_color="transparent")
    f_coin_row.grid(row=0, column=1, sticky="ew", padx=5)

    app.cbo_symbol = ctk.CTkOptionMenu(
        f_coin_row,
        values=config.COIN_LIST,
        font=FONT_BOLD,
        width=100,
        command=app.on_symbol_change,
    )
    if config.DEFAULT_SYMBOL in config.COIN_LIST:
        app.cbo_symbol.set(config.DEFAULT_SYMBOL)
    elif len(config.COIN_LIST) > 0:
        app.cbo_symbol.set(config.COIN_LIST[0])
    app.cbo_symbol.pack(side="left")

    f_bot_controls = ctk.CTkFrame(f_coin_row, fg_color="transparent")
    f_bot_controls.pack(side="left", padx=10)

    app.ind_auto_light = ctk.CTkFrame(
        f_bot_controls, width=14, height=14, corner_radius=7, fg_color=COL_RED
    )
    app.ind_auto_light.pack(side="left", padx=(0, 6))

    ctk.CTkButton(
        f_bot_controls,
        text="⚙ BOT",
        width=40,
        height=24,
        fg_color="#4A148C",
        hover_color="#6A1B9A",
        command=app.open_bot_setting_popup,
    ).pack(side="left", padx=(0, 5))

    app.btn_strategy = ctk.CTkButton(
        f_bot_controls,
        text="🧩 SANDBOX",
        width=60,
        height=24,
        font=("Roboto", 11, "bold"),
        fg_color="#1f538d",
        hover_color="#14375e",
        command=app.open_strategy_sandbox,
    )
    app.btn_strategy.pack(side="left")

    app.chk_force = ctk.CTkCheckBox(
        f_coin_row,
        text="F",
        variable=app.var_bypass_checklist,
        font=("Roboto", 11, "bold"),
        text_color=COL_WARN,
        width=50,
        checkbox_width=18,
        checkbox_height=18,
    )
    app.chk_force.pack(side="right", padx=0)

    # --- DÒNG 2: MODE ---
    ctk.CTkLabel(f_set, text="MODE:", font=FONT_SECTION, text_color="#D7DCE2").grid(
        row=1, column=0, sticky="e", padx=(0, 8), pady=5
    )
    f_mode_row = ctk.CTkFrame(f_set, fg_color="transparent")
    f_mode_row.grid(row=1, column=1, sticky="ew", padx=5)

    app.cbo_preset = ctk.CTkOptionMenu(
        f_mode_row, values=list(config.PRESETS.keys()), font=FONT_MAIN, width=100
    )
    app.cbo_preset.set(config.DEFAULT_PRESET)
    app.cbo_preset.pack(side="left", fill="x", expand=True)
    ctk.CTkButton(
        f_mode_row,
        text="⚙",
        width=30,
        height=28,
        fg_color="#444",
        hover_color="#666",
        command=app.open_preset_config_popup,
    ).pack(side="left", padx=(2, 0))
    app.cbo_account_type = ctk.CTkOptionMenu(
        f_mode_row,
        values=list(config.ACCOUNT_TYPES_CONFIG.keys()),
        font=FONT_MAIN,
        width=80,
    )
    app.cbo_account_type.set(config.DEFAULT_ACCOUNT_TYPE)
    app.cbo_account_type.pack(side="right", fill="x", padx=(5, 0))


    # --- DÒNG 2: TACTIC ---
    ctk.CTkLabel(f_set, text="TSL:", font=FONT_SECTION, text_color="#D7DCE2").grid(
        row=2, column=0, sticky="e", padx=(0, 8), pady=2
    )
    f_tsl_row = ctk.CTkFrame(f_set, fg_color="transparent")
    f_tsl_row.grid(row=2, column=1, sticky="ew", padx=5)

    app.btn_tactic_be = ctk.CTkButton(
        f_tsl_row, text="BE", width=32, command=lambda: app.toggle_tactic("BE")
    )
    app.btn_tactic_be.pack(side="left", padx=1)
    app.btn_tactic_pnl = ctk.CTkButton(
        f_tsl_row, text="PNL", width=28, command=lambda: app.toggle_tactic("PNL")
    )
    app.btn_tactic_pnl.pack(side="left", padx=1)
    app.btn_tactic_step = ctk.CTkButton(
        f_tsl_row, text="STEP", width=32, command=lambda: app.toggle_tactic("STEP_R")
    )
    app.btn_tactic_step.pack(side="left", padx=1)
    app.btn_tactic_swing = ctk.CTkButton(
        f_tsl_row, text="SWING", width=38, command=lambda: app.toggle_tactic("SWING")
    )
    app.btn_tactic_swing.pack(side="left", padx=1)
    
    # [FIX V4.4] Thêm nút CASH và PSAR lên Pannel
    app.btn_tactic_cash = ctk.CTkButton(
        f_tsl_row, text="CASH", width=38, command=lambda: app.toggle_tactic("BE_CASH")
    )
    app.btn_tactic_cash.pack(side="left", padx=1)
    app.btn_tactic_psar = ctk.CTkButton(
        f_tsl_row, text="PSAR", width=38, command=lambda: app.toggle_tactic("PSAR_TRAIL")
    )
    app.btn_tactic_psar.pack(side="left", padx=1)

    # [NEW V4.4] RECOVERY & SAFELOCK Section
    ctk.CTkLabel(f_set, text="DEF:", font=FONT_SECTION, text_color="#D7DCE2").grid(
        row=4, column=0, sticky="e", padx=(0, 8), pady=2
    )
    f_extra = ctk.CTkFrame(f_set, fg_color="transparent")
    f_extra.grid(row=4, column=1, sticky="ew", padx=5)
    
    app.btn_tactic_dca = ctk.CTkButton(
        f_extra, text="DCA", width=36, command=lambda: app.toggle_tactic("AUTO_DCA")
    )
    app.btn_tactic_dca.pack(side="left", padx=1)
    
    app.btn_tactic_pca = ctk.CTkButton(
        f_extra, text="PCA", width=36, command=lambda: app.toggle_tactic("AUTO_PCA")
    )
    app.btn_tactic_pca.pack(side="left", padx=1)
    
    app.btn_tactic_rev_c = ctk.CTkButton(
        f_extra, text="REV", width=34, command=lambda: app.toggle_tactic("REV_C")
    )
    app.btn_tactic_rev_c.pack(side="left", padx=1)
    
    app.btn_tactic_anti_cash = ctk.CTkButton(
        f_extra, text="A.CUT", width=38, command=lambda: app.toggle_tactic("ANTI_CASH")
    )
    app.btn_tactic_anti_cash.pack(side="left", padx=1)

    try:
        from grid.grid_storage import load_grid_settings
        _grid_on = bool(load_grid_settings().get("ENABLED", False))
    except Exception:
        _grid_on = False
    f_ad_cluster = ctk.CTkFrame(f_extra, fg_color="transparent")
    f_ad_cluster.pack(side="left", padx=(4, 1))
    f_ad_status = ctk.CTkFrame(f_ad_cluster, fg_color="transparent")
    f_ad_status.pack(side="left", padx=(0, 2))
    
    f_grid_state = ctk.CTkFrame(f_ad_status, fg_color="transparent")
    f_grid_state.pack(anchor="w", pady=0)
    app.ind_ad_grid_light = ctk.CTkFrame(
        f_grid_state,
        width=8,
        height=8,
        corner_radius=4,
        fg_color=COL_GREEN if _grid_on else COL_RED,
    )
    app.ind_ad_grid_light.pack(side="left", padx=(0, 2))
    ctk.CTkLabel(
        f_grid_state,
        text="GRID",
        font=("Roboto", 8, "bold"),
        height=10,
        text_color="#00B8D4" if _grid_on else "gray",
    ).pack(side="left")
    
    f_hedge_state = ctk.CTkFrame(f_ad_status, fg_color="transparent")
    f_hedge_state.pack(anchor="w", pady=0)
    app.ind_ad_hedge_light = ctk.CTkFrame(
        f_hedge_state,
        width=8,
        height=8,
        corner_radius=4,
        fg_color=COL_RED,
    )
    app.ind_ad_hedge_light.pack(side="left", padx=(0, 2))
    ctk.CTkLabel(
        f_hedge_state,
        text="HEDGE",
        font=("Roboto", 8, "bold"),
        height=10,
        text_color="gray",
    ).pack(side="left")

    ctk.CTkButton(
        f_ad_cluster,
        text="⚙ AD",
        width=34,
        height=28,
        font=("Roboto", 11, "bold"),
        fg_color="#00838F",
        hover_color="#006064",
        command=app.open_advanced_tools_popup,
    ).pack(side="left", padx=(0, 1))

    ctk.CTkLabel(f_set, text="E/E:", font=FONT_SECTION, text_color="#D7DCE2").grid(
        row=3, column=0, sticky="e", padx=(0, 8), pady=2
    )
    f_entry = ctk.CTkFrame(f_set, fg_color="transparent")
    f_entry.grid(row=3, column=1, sticky="ew", padx=5)

    app.btn_entry_r = ctk.CTkButton(
        f_entry,
        text="R",
        width=34,
        command=lambda: app.toggle_entry_exit_tactic("FALLBACK_R"),
    )
    app.btn_entry_r.pack(side="left", padx=1)
    app.btn_entry_swing = ctk.CTkButton(
        f_entry,
        text="SWING",
        width=48,
        command=lambda: app.toggle_entry_exit_tactic("SWING_REJECTION"),
    )
    app.btn_entry_swing.pack(side="left", padx=1)
    app.btn_entry_fib = ctk.CTkButton(
        f_entry,
        text="FIB",
        width=34,
        command=lambda: app.toggle_entry_exit_tactic("FIB_RETRACE"),
    )
    app.btn_entry_fib.pack(side="left", padx=1)
    app.btn_entry_pullback = ctk.CTkButton(
        f_entry,
        text="PULL",
        width=42,
        command=lambda: app.toggle_entry_exit_tactic("PULLBACK_ZONE"),
    )
    app.btn_entry_pullback.pack(side="left", padx=1)

    ctk.CTkButton(
        f_entry,
        text="\u2699 E/E",
        width=54,
        height=28,
        fg_color="#424242",
        hover_color="#616161",
        command=app.open_entry_exit_popup,
    ).pack(side="left", padx=(6, 1))

    f_btn_settings = ctk.CTkFrame(f_tsl_row, fg_color="transparent")
    f_btn_settings.pack(side="right", padx=(0, 0))
    ctk.CTkButton(
        f_btn_settings,
        text="⚙ TSL",
        width=38,
        height=24,
        fg_color="#424242",
        hover_color="#616161",
        command=app.open_tsl_popup,
    ).pack(side="right")

    app.update_tactic_buttons_ui()
    app.update_entry_exit_buttons_ui()

    # 3. MANUAL INPUT PANEL
    f_input = ctk.CTkFrame(parent, fg_color="transparent")
    f_input.pack(fill="x", padx=5, pady=(5, 0))
    f_input.grid_columnconfigure((0, 1, 2), weight=1)

    def make_inp(p, t, v, c):
        f = ctk.CTkFrame(p, fg_color="#2b2b2b", corner_radius=6)
        f.grid(row=0, column=c, padx=3, sticky="ew")
        ctk.CTkLabel(f, text=t, font=("Roboto", 10, "bold"), text_color="#aaa").pack(
            pady=(2, 0)
        )
        ctk.CTkEntry(
            f,
            textvariable=v,
            font=("Consolas", 14, "bold"),
            height=30,
            justify="center",
            fg_color="transparent",
            border_width=0,
        ).pack(fill="x")

    make_inp(f_input, "VOL (Lot)", app.var_manual_lot, 0)
    make_inp(f_input, "TP (Price)", app.var_manual_tp, 1)
    make_inp(f_input, "SL (Price)", app.var_manual_sl, 2)

    # --- PHẦN ĐÃ FIX: MULTI-TF CONTEXT PREVIEW (V8.4.1) ---
    f_context = ctk.CTkFrame(parent, fg_color="#1E1E1E", corner_radius=6)
    f_context.pack(fill="x", padx=5, pady=(5, 5))

    # Dòng 1: Chế độ (Mode) & Xu hướng (Trend)
    app.lbl_market_mode = ctk.CTkLabel(
        f_context,
        text="Mode: -- | Trend: --",
        font=("Roboto", 13, "bold"),
        text_color="#29B6F6",
        anchor="w",
    )
    app.lbl_market_mode.pack(fill="x", padx=10, pady=(5, 0))

    # Dòng 2: Khung chứa Dropdown chọn G và Thông số H/L/ATR
    f_context_bottom = ctk.CTkFrame(f_context, fg_color="transparent")
    f_context_bottom.pack(fill="x", padx=5, pady=(2, 5))

    app.var_dashboard_tf = tk.StringVar(value="G1")
    app.cbo_dashboard_tf = ctk.CTkOptionMenu(
        f_context_bottom,
        values=["G0", "G1", "G2", "G3"],
        variable=app.var_dashboard_tf,
        width=60,
        height=24,
        font=("Roboto", 11, "bold"),
    )
    app.cbo_dashboard_tf.pack(side="left", padx=5)

    # Label DUY NHẤT để hiển thị Swing/ATR (Xóa các bản trùng lặp cũ)
    # Label DUY NHẤT để hiển thị Swing/ATR
    app.lbl_market_context = ctk.CTkLabel(
        f_context_bottom,
        text="H: -- | L: -- | ATR: --",
        font=("Consolas", 14, "bold"),
        text_color="#78909C",
        anchor="w",
    )
    app.lbl_market_context.pack(side="left", fill="x", expand=True, padx=5)

    # 4. LIVE DASHBOARD
    f_dashboard = ctk.CTkFrame(
        parent, fg_color="#252526", corner_radius=8, border_width=1, border_color="#333"
    )
    f_dashboard.pack(fill="x", padx=5, pady=(5, 10))

    f_head_db = ctk.CTkFrame(f_dashboard, fg_color="transparent")
    f_head_db.pack(fill="x", padx=10, pady=(5, 0))
    app.lbl_prev_lot = ctk.CTkLabel(
        f_head_db, text="LOT: 0.00", font=FONT_BOLD, text_color="#FFD700"
    )
    app.lbl_prev_lot.pack(side="left")
    app.lbl_fee_info = ctk.CTkLabel(
        f_head_db, text="Cost: $0.00", font=FONT_FEE, text_color="#FFD700"
    )
    app.lbl_fee_info.pack(side="right")
    f_price_row = ctk.CTkFrame(f_dashboard, fg_color="transparent")
    f_price_row.pack(fill="x", padx=8, pady=(5, 5))
    f_price_row.grid_columnconfigure(0, minsize=106)
    f_price_row.grid_columnconfigure(1, weight=1)
    f_price_row.grid_columnconfigure(2, minsize=106)

    app.frame_trade_mode = ctk.CTkFrame(f_price_row, fg_color="#424242", corner_radius=6)
    app.frame_trade_mode.grid(row=0, column=0, sticky="w", padx=(0, 8))
    app.btn_mode_normal = ctk.CTkButton(
        app.frame_trade_mode,
        text="NORMAL",
        width=96,
        height=24,
        font=("Roboto", 10, "bold"),
        fg_color="#00838F",
        hover_color="#006064",
        command=lambda: app.on_manual_trade_mode_change("NORMAL"),
    )
    app.btn_mode_normal.pack(fill="x", padx=4, pady=(4, 1))
    app.btn_mode_grid = ctk.CTkButton(
        app.frame_trade_mode,
        text="GRID",
        width=96,
        height=24,
        font=("Roboto", 10, "bold"),
        fg_color="#424242",
        hover_color="#616161",
        command=lambda: app.on_manual_trade_mode_change("GRID"),
    )
    app.btn_mode_grid.pack(fill="x", padx=4, pady=(1, 4))

    app.lbl_dashboard_price = ctk.CTkLabel(
        f_price_row, text="----.--", font=FONT_PRICE, text_color="white"
    )
    app.lbl_dashboard_price.grid(row=0, column=1, sticky="ew")

    app.frame_direction = ctk.CTkFrame(f_price_row, fg_color="#424242", corner_radius=6)
    app.frame_direction.grid(row=0, column=2, sticky="e", padx=(8, 0))
    app.btn_dir_buy = ctk.CTkButton(
        app.frame_direction,
        text="BUY",
        width=96,
        height=24,
        font=("Roboto", 10, "bold"),
        fg_color=COL_GREEN,
        hover_color="#009624",
        command=lambda: app.on_direction_change("BUY"),
    )
    app.btn_dir_buy.pack(fill="x", padx=4, pady=(4, 1))
    app.btn_dir_sell = ctk.CTkButton(
        app.frame_direction,
        text="SELL",
        width=96,
        height=24,
        font=("Roboto", 10, "bold"),
        fg_color="#424242",
        hover_color="#616161",
        command=lambda: app.on_direction_change("SELL"),
    )
    app.btn_dir_sell.pack(fill="x", padx=4, pady=(1, 4))

    ctk.CTkFrame(f_dashboard, height=1, fg_color="#444").pack(fill="x", padx=5)
    f_grid_db = ctk.CTkFrame(f_dashboard, fg_color="transparent")
    f_grid_db.pack(fill="x", padx=5, pady=5)
    f_grid_db.columnconfigure((0, 1), weight=1)

    f_rew = ctk.CTkFrame(f_grid_db, fg_color="transparent")
    f_rew.grid(row=0, column=0, sticky="nsew", padx=2)
    app.lbl_head_tp = ctk.CTkLabel(
        f_rew, text="TARGET (TP)", font=("Roboto", 10), text_color=COL_GREEN
    )
    app.lbl_head_tp.pack()
    app.lbl_prev_tp = ctk.CTkLabel(
        f_rew, text="---", font=("Consolas", 14), text_color=COL_GREEN
    )
    app.lbl_prev_tp.pack()
    app.lbl_prev_rew = ctk.CTkLabel(
        f_rew, text="+$0.0", font=FONT_BIG_VAL, text_color=COL_GREEN
    )
    app.lbl_prev_rew.pack()

    f_risk = ctk.CTkFrame(f_grid_db, fg_color="transparent")
    f_risk.grid(row=0, column=1, sticky="nsew", padx=2)
    app.lbl_head_sl = ctk.CTkLabel(
        f_risk, text="STOPLOSS (SL)", font=("Roboto", 10), text_color=COL_RED
    )
    app.lbl_head_sl.pack()
    app.lbl_prev_sl = ctk.CTkLabel(
        f_risk, text="---", font=("Consolas", 14), text_color=COL_RED
    )
    app.lbl_prev_sl.pack()
    app.lbl_prev_risk = ctk.CTkLabel(
        f_risk, text="-$0.0", font=FONT_BIG_VAL, text_color=COL_RED
    )
    app.lbl_prev_risk.pack()

    ctk.CTkFrame(f_dashboard, height=1, fg_color="#444").pack(
        fill="x", padx=10, pady=(5, 0)
    )
    app.lbl_tsl_preview = ctk.CTkLabel(
        f_dashboard, text="TSL: OFF", font=("Roboto", 13), text_color="#2196F3"
    )
    app.lbl_tsl_preview.pack(pady=(5, 5))
    app.lbl_entry_exit_preview = ctk.CTkLabel(
        f_dashboard, text="E/E: OFF", font=("Roboto", 12, "bold"), text_color="#00B8D4"
    )
    app.lbl_entry_exit_preview.pack(pady=(0, 5))

    # 5. EXECUTION CONTROLS
    app.seg_grid_mode = ctk.CTkSegmentedButton(
        parent,
        values=["NEUTRAL", "LONG", "SHORT"],
        font=("Roboto", 13, "bold"),
        command=app.on_grid_mode_change,
        height=32,
        selected_color="#00838F",
        selected_hover_color="#006064",
    )
    app.seg_grid_mode.set(app.var_grid_manual_mode.get())

    app.chk_grid_bypass = ctk.CTkCheckBox(
        parent,
        text="Bypass GRID Signal",
        variable=app.var_grid_bypass_signal,
        font=("Roboto", 11, "bold"),
        text_color="#00B8D4",
        checkbox_width=18,
        checkbox_height=18,
    )

    app.btn_action = ctk.CTkButton(
        parent,
        text="EXECUTE BUY",
        font=("Roboto", 16, "bold"),
        height=45,
        fg_color=COL_GREEN,
        hover_color="#009624",
        command=app.on_click_trade,
    )
    app.btn_action.pack(fill="x", padx=10, pady=(0, 10))
    app.on_manual_trade_mode_change(app.var_manual_trade_mode.get())

    # 6. SYSTEM HEALTH
    f_sys = ctk.CTkFrame(parent, fg_color="#1a1a1a")
    f_sys.pack(fill="x", padx=5, pady=(5, 20))
    ctk.CTkLabel(
        f_sys, text=" SYSTEM HEALTH", font=("Roboto", 11, "bold"), text_color="gray"
    ).pack(anchor="w", padx=5, pady=(5, 0))

    app.check_labels = {}
    checks = ["Mạng/Spread", "Daily Loss", "Số Lệnh Thua", "Số Lệnh", "Trạng thái"]
    for name in checks:
        l = ctk.CTkLabel(
            f_sys, text=f"• {name}", font=("Roboto", 12), text_color="gray", anchor="w"
        )
        l.pack(fill="x", padx=10)
        app.check_labels[name] = l


def setup_right_panel(app, parent):
    """Xây dựng khung theo dõi lệnh (Treeview) và Log (Text)"""

    # 1. HEADER ROW
    f_head = ctk.CTkFrame(parent, fg_color="transparent", height=30)
    f_head.pack(fill="x", pady=(0, 5))
    ctk.CTkLabel(
        f_head, text="DANH SÁCH LỆNH ĐANG CHẠY", font=("Roboto", 16, "bold")
    ).pack(side="left")

    ctk.CTkButton(
        f_head,
        text="Lịch sử",
        width=80,
        height=24,
        command=app.show_history_popup,
        fg_color="#444",
    ).pack(side="right")
    ctk.CTkButton(
        f_head,
        text="Đóng hết",
        width=70,
        height=24,
        fg_color="#D50000",
        hover_color="#B71C1C",
        command=app.close_all_trades,
    ).pack(side="right", padx=5)
    ctk.CTkButton(
        f_head,
        text="Đóng mục chọn",
        width=110,
        height=24,
        fg_color="#FF8F00",
        hover_color="#FF6F00",
        command=app.close_selected_trades,
    ).pack(side="right", padx=5)

    # 2. TREEVIEW CONTAINER
    f_tree_container = ctk.CTkFrame(parent, fg_color="#2b2b2b")
    f_tree_container.pack(fill="both", expand=True)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        "Treeview",
        background="#2b2b2b",
        foreground="white",
        fieldbackground="#2b2b2b",
        rowheight=50,
        font=("Consolas", 18),
    )
    style.configure(
        "Treeview.Heading",
        background="#1f1f1f",
        foreground="#e0e0e0",
        font=("Roboto", 20, "bold"),
        relief="flat",
    )
    style.map("Treeview", background=[("selected", "#3949ab")])

    cols = (
        "Ticket",
        "Time",
        "Order",
        "Targets",
        "CostInfo",
        "RR",
        "PnL_MAE_MFE",
        "Status",
        "X",
    )
    app.tree = ttk.Treeview(
        f_tree_container,
        columns=cols,
        show="headings",
        style="Treeview",
        selectmode="extended",
    )

    app.tree.tag_configure("buy_row", background="#234d20", foreground="#e0e0e0")
    app.tree.tag_configure("sell_row", background="#5c1a1b", foreground="#e0e0e0")
    app.tree.tag_configure("grid_row", background="#153942", foreground="#E0F7FA")

    headers = [
        "Ticket",
        "Thời gian",
        "Thông tin Lệnh",
        "Chốt lời/Lỗ (SL|TP)",
        "Chi phí/Phí qua đêm",
        "Rủi ro/Kỳ vọng (%)",
        "Lợi nhuận",
        "Trạng thái",
        "✖",
    ]
    widths = [190, 190, 560, 360, 390, 500, 470, 620, 55]
    anchors = [
        "center",
        "center",
        "w",
        "center",
        "center",
        "center",
        "center",
        "w",
        "center",
    ]

    for c, h, w, a in zip(cols, headers, widths, anchors):
        if c == "PnL_MAE_MFE":
            h = "PnL / MAE / MFE"
        app.tree.heading(c, text=h)
        app.tree.column(c, width=w, anchor=a, minwidth=w, stretch=False)

    sb = ttk.Scrollbar(f_tree_container, orient="vertical", command=app.tree.yview)
    sb_x = ttk.Scrollbar(f_tree_container, orient="horizontal", command=app.tree.xview)
    app.tree.configure(yscrollcommand=sb.set, xscrollcommand=sb_x.set)

    app.tree.grid(row=0, column=0, sticky="nsew")
    sb.grid(row=0, column=1, sticky="ns")
    sb_x.grid(row=1, column=0, sticky="ew")
    f_tree_container.grid_rowconfigure(0, weight=1)
    f_tree_container.grid_columnconfigure(0, weight=1)

    app.tree.bind("<ButtonRelease-1>", app.on_tree_click)
    app.tree.bind("<Button-3>", app.on_tree_right_click)

    # 3. LOGGING CONSOLE (2 TAB: MANUAL & BOT)
    f_log = ctk.CTkFrame(parent, height=350, fg_color="#1e1e1e")
    f_log.pack(fill="x", pady=(10, 0))
    f_log.pack_propagate(False)

    f_log_head = ctk.CTkFrame(f_log, fg_color="transparent", height=25)
    f_log_head.pack(fill="x", padx=5, pady=2)
    ctk.CTkLabel(
        f_log_head,
        text="HỆ THỐNG GHI NHẬT KÝ (LOG)",
        font=("Roboto", 12, "bold"),
        text_color="#aaa",
    ).pack(side="left")
    ctk.CTkCheckBox(
        f_log_head,
        text="Xác nhận đóng lệnh",
        variable=app.var_confirm_close,
        font=("Roboto", 11),
        checkbox_width=16,
        checkbox_height=16,
    ).pack(side="right")

    # Tabview chứa 2 tab Log
    log_tabview = ctk.CTkTabview(
        f_log,
        height=300,
        fg_color="#121212",
        segmented_button_fg_color="#2b2b2b",
        segmented_button_selected_color="#1565C0",
        segmented_button_unselected_color="#333333",
    )
    log_tabview.pack(fill="both", expand=True, padx=5, pady=(0, 5))

    def _clear_active_log():
        """Xóa log ở tab đang được chọn"""
        active_tab = log_tabview.get()
        if "Bot-Log" in active_tab:
            widget = app.txt_log_bot_log
        elif "GRID-Log" in active_tab:  # [FIX] GRID-Log phải check trước GRID
            widget = app.txt_log_grid_log
        elif "Bot" in active_tab:  # [FIX] Bot phải check trước khi dùng GRID
            widget = app.txt_log_bot
        elif "GRID" in active_tab:
            widget = app.txt_log_grid
        else:
            widget = app.txt_log_manual
            
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.configure(state="disabled")

    ctk.CTkButton(
        f_log_head,
        text="🗑 Clear",
        width=70,
        height=22,
        fg_color="#444",
        hover_color="#c62828",
        font=("Roboto", 11),
        command=_clear_active_log,
    ).pack(side="right", padx=(0, 8))

    tab_manual = log_tabview.add("📋 Manual")
    tab_bot = log_tabview.add("🤖 Bot")
    tab_bot_log = log_tabview.add("🤖 Bot-Log")

    tab_grid = log_tabview.add("GRID")
    tab_grid_log = log_tabview.add("GRID-Log")

    # --- Tab Manual ---
    app.txt_log_manual = tk.Text(
        tab_manual,
        font=("Consolas", 18),
        bg="#121212",
        fg="#e0e0e0",
        bd=0,
        highlightthickness=0,
        state="disabled",
        wrap="none",
    )
    sb_manual_x = ttk.Scrollbar(tab_manual, orient="horizontal", command=app.txt_log_manual.xview)
    app.txt_log_manual.configure(xscrollcommand=sb_manual_x.set)
    sb_manual_x.pack(fill="x", side="bottom")
    app.txt_log_manual.pack(fill="both", expand=True)
    app.txt_log_manual.tag_config("INFO", foreground="#b0bec5")
    app.txt_log_manual.tag_config("SUCCESS", foreground=COL_GREEN)
    app.txt_log_manual.tag_config("ERROR", foreground=COL_RED)
    app.txt_log_manual.tag_config("WARN", foreground=COL_WARN)
    app.txt_log_manual.tag_config("BLUE", foreground="#29B6F6")

    # --- Tab Bot ---
    app.txt_log_bot = tk.Text(
        tab_bot,
        font=("Consolas", 18),
        bg="#121212",
        fg="#e0e0e0",
        bd=0,
        highlightthickness=0,
        state="disabled",
        wrap="none",
    )
    sb_bot_x = ttk.Scrollbar(tab_bot, orient="horizontal", command=app.txt_log_bot.xview)
    app.txt_log_bot.configure(xscrollcommand=sb_bot_x.set)
    sb_bot_x.pack(fill="x", side="bottom")
    app.txt_log_bot.pack(fill="both", expand=True)
    app.txt_log_bot.tag_config("INFO", foreground="#b0bec5")
    app.txt_log_bot.tag_config("SUCCESS", foreground=COL_GREEN)
    app.txt_log_bot.tag_config("ERROR", foreground=COL_RED)
    app.txt_log_bot.tag_config("WARN", foreground=COL_WARN)
    app.txt_log_bot.tag_config("BLUE", foreground="#29B6F6")

    # --- Tab Bot-Log ---
    app.txt_log_bot_log = tk.Text(
        tab_bot_log,
        font=("Consolas", 18),
        bg="#121212",
        fg="#e0e0e0",
        bd=0,
        highlightthickness=0,
        state="disabled",
        wrap="none",
    )
    sb_bot_log_x = ttk.Scrollbar(tab_bot_log, orient="horizontal", command=app.txt_log_bot_log.xview)
    app.txt_log_bot_log.configure(xscrollcommand=sb_bot_log_x.set)
    sb_bot_log_x.pack(fill="x", side="bottom")
    app.txt_log_bot_log.pack(fill="both", expand=True)
    app.txt_log_bot_log.tag_config("INFO", foreground="#b0bec5")
    app.txt_log_bot_log.tag_config("SUCCESS", foreground=COL_GREEN)
    app.txt_log_bot_log.tag_config("ERROR", foreground=COL_RED)
    app.txt_log_bot_log.tag_config("WARN", foreground=COL_WARN)
    app.txt_log_bot_log.tag_config("BLUE", foreground="#29B6F6")

    # Giữ backward compat: txt_log trỏ vào manual (cho các module cũ)
    # --- Tab GRID ---
    app.txt_log_grid = tk.Text(
        tab_grid,
        font=("Consolas", 18),
        bg="#081416",
        fg="#E0F7FA",
        bd=0,
        highlightthickness=0,
        state="disabled",
        wrap="none",
    )
    sb_grid_x = ttk.Scrollbar(tab_grid, orient="horizontal", command=app.txt_log_grid.xview)
    app.txt_log_grid.configure(xscrollcommand=sb_grid_x.set)
    sb_grid_x.pack(fill="x", side="bottom")
    app.txt_log_grid.pack(fill="both", expand=True)
    app.txt_log_grid.tag_config("INFO", foreground="#B2EBF2")
    app.txt_log_grid.tag_config("SUCCESS", foreground="#00E5FF")
    app.txt_log_grid.tag_config("ERROR", foreground=COL_RED)
    app.txt_log_grid.tag_config("WARN", foreground=COL_WARN)
    app.txt_log_grid.tag_config("BLUE", foreground="#29B6F6")

    # --- Tab GRID Log ---
    app.txt_log_grid_log = tk.Text(
        tab_grid_log,
        font=("Consolas", 18),
        bg="#081416",
        fg="#B2EBF2",
        bd=0,
        highlightthickness=0,
        state="disabled",
        wrap="none",
    )
    sb_grid_log_x = ttk.Scrollbar(tab_grid_log, orient="horizontal", command=app.txt_log_grid_log.xview)
    app.txt_log_grid_log.configure(xscrollcommand=sb_grid_log_x.set)
    sb_grid_log_x.pack(fill="x", side="bottom")
    app.txt_log_grid_log.pack(fill="both", expand=True)
    app.txt_log_grid_log.tag_config("INFO", foreground="#B2EBF2")
    app.txt_log_grid_log.tag_config("SUCCESS", foreground="#00E5FF")
    app.txt_log_grid_log.tag_config("ERROR", foreground=COL_RED)
    app.txt_log_grid_log.tag_config("WARN", foreground=COL_WARN)
    app.txt_log_grid_log.tag_config("BLUE", foreground="#29B6F6")

    app.txt_log = app.txt_log_manual
