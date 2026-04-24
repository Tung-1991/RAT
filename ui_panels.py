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
    
    # 1. TOP HEADER (Equity & Info) - TỐI ƯU KHÔNG GIAN CỘT (V8.4.1 FIX)
    f_top = ctk.CTkFrame(parent, fg_color="#1a1a1a", corner_radius=8)
    f_top.pack(fill="x", pady=(5, 5), padx=5)
    f_top.columnconfigure(0, weight=1)
    f_top.columnconfigure(1, weight=1)

    # Cột trái: Equity & Today PnL
    app.lbl_equity = ctk.CTkLabel(f_top, text="$----", font=FONT_EQUITY, text_color=COL_GREEN)
    app.lbl_equity.grid(row=0, column=0, sticky="w", padx=10, pady=(5, 0))

    f_pnl = ctk.CTkFrame(f_top, fg_color="transparent")
    f_pnl.grid(row=1, column=0, sticky="w", padx=5, pady=(0, 5))
    app.lbl_stats = ctk.CTkLabel(f_pnl, text="Today: $0.00", font=FONT_PNL, text_color="white")
    app.lbl_stats.pack(side="left", padx=5)
    ctk.CTkButton(f_pnl, text="⟳", width=30, height=20, fg_color="#333", hover_color="#444", command=app.reset_daily_stats).pack(side="left", padx=5)

    # Cột phải: ID/Server & Brain Status
    app.lbl_acc_info = ctk.CTkLabel(f_top, text="ID: --- | Server: ---", font=("Roboto", 10), text_color="gray")
    app.lbl_acc_info.grid(row=0, column=1, sticky="e", padx=10, pady=(10, 0))

    app.lbl_brain_status = ctk.CTkLabel(f_top, text="🧠 BRAIN: CHỜ KẾT NỐI...", font=("Roboto", 11, "bold"), text_color="#FF8F00")
    app.lbl_brain_status.grid(row=1, column=1, sticky="e", padx=10, pady=(0, 10))

    # 2. SETTINGS PANEL (Coin, Mode, Tactic)
    f_set = ctk.CTkFrame(parent, fg_color="transparent")
    f_set.pack(fill="x", padx=5, pady=5)
    f_set.columnconfigure(1, weight=1)

    # --- DÒNG 1: COIN & CẤU HÌNH BOT & SANDBOX ---
    ctk.CTkLabel(f_set, text="COIN:", font=FONT_SECTION, text_color="gray").grid(row=0, column=0, sticky="w")
    f_coin_row = ctk.CTkFrame(f_set, fg_color="transparent")
    f_coin_row.grid(row=0, column=1, sticky="ew", padx=5)
    
    app.cbo_symbol = ctk.CTkOptionMenu(f_coin_row, values=config.COIN_LIST, font=FONT_BOLD, width=100, command=app.on_symbol_change)
    if config.DEFAULT_SYMBOL in config.COIN_LIST:
        app.cbo_symbol.set(config.DEFAULT_SYMBOL)
    elif len(config.COIN_LIST) > 0:
        app.cbo_symbol.set(config.COIN_LIST[0])
    app.cbo_symbol.pack(side="left")
    
    f_bot_controls = ctk.CTkFrame(f_coin_row, fg_color="transparent")
    f_bot_controls.pack(side="left", padx=10)
    
    app.ind_auto_light = ctk.CTkFrame(f_bot_controls, width=14, height=14, corner_radius=7, fg_color=COL_RED)
    app.ind_auto_light.pack(side="left", padx=(0, 6))
    
    ctk.CTkButton(f_bot_controls, text="⚙ BOT", width=40, height=24, fg_color="#4A148C", hover_color="#6A1B9A", command=app.open_bot_setting_popup).pack(side="left", padx=(0, 5))

    app.btn_strategy = ctk.CTkButton(
        f_bot_controls, 
        text="🧩 SANDBOX", 
        width=60,
        height=24,
        font=("Roboto", 11, "bold"), 
        fg_color="#1f538d",      
        hover_color="#14375e", 
        command=app.open_strategy_sandbox
    )
    app.btn_strategy.pack(side="left")

    app.chk_force = ctk.CTkCheckBox(f_coin_row, text="F", variable=app.var_bypass_checklist, font=("Roboto", 11, "bold"), text_color=COL_WARN, width=50, checkbox_width=18, checkbox_height=18)
    app.chk_force.pack(side="right", padx=0)

    # --- DÒNG 2: MODE ---
    ctk.CTkLabel(f_set, text="MODE:", font=FONT_SECTION, text_color="gray").grid(row=1, column=0, sticky="w", pady=5)
    f_mode_row = ctk.CTkFrame(f_set, fg_color="transparent")
    f_mode_row.grid(row=1, column=1, sticky="ew", padx=5)
    
    app.cbo_preset = ctk.CTkOptionMenu(f_mode_row, values=list(config.PRESETS.keys()), font=FONT_MAIN, width=100)
    app.cbo_preset.set(config.DEFAULT_PRESET)
    app.cbo_preset.pack(side="left", fill="x", expand=True)
    ctk.CTkButton(f_mode_row, text="⚙", width=30, height=28, fg_color="#444", hover_color="#666", command=app.open_preset_config_popup).pack(side="left", padx=(2,0))
    app.cbo_account_type = ctk.CTkOptionMenu(f_mode_row, values=list(config.ACCOUNT_TYPES_CONFIG.keys()), font=FONT_MAIN, width=80)
    app.cbo_account_type.set(config.DEFAULT_ACCOUNT_TYPE)
    app.cbo_account_type.pack(side="right", fill="x", padx=(5,0))

    # --- DÒNG 3: TACTIC ---
    ctk.CTkLabel(f_set, text="TACTIC:", font=FONT_SECTION, text_color="gray").grid(row=2, column=0, sticky="w", pady=5)
    f_tsl_row = ctk.CTkFrame(f_set, fg_color="transparent")
    f_tsl_row.grid(row=2, column=1, sticky="ew", padx=5)

    app.btn_tactic_be = ctk.CTkButton(f_tsl_row, text="BE", width=32, command=lambda: app.toggle_tactic("BE"))
    app.btn_tactic_be.pack(side="left", padx=1)
    app.btn_tactic_pnl = ctk.CTkButton(f_tsl_row, text="PNL", width=32, command=lambda: app.toggle_tactic("PNL"))
    app.btn_tactic_pnl.pack(side="left", padx=1)
    app.btn_tactic_step = ctk.CTkButton(f_tsl_row, text="STEP", width=38, command=lambda: app.toggle_tactic("STEP_R"))
    app.btn_tactic_step.pack(side="left", padx=1)
    app.btn_tactic_swing = ctk.CTkButton(f_tsl_row, text="SWING", width=42, command=lambda: app.toggle_tactic("SWING"))
    app.btn_tactic_swing.pack(side="left", padx=1)
    
    app.btn_tactic_dca = ctk.CTkButton(f_tsl_row, text="DCA", width=35, command=lambda: app.toggle_tactic("AUTO_DCA"))
    app.btn_tactic_dca.pack(side="left", padx=1)
    app.btn_tactic_pca = ctk.CTkButton(f_tsl_row, text="PCA", width=35, command=lambda: app.toggle_tactic("AUTO_PCA"))
    app.btn_tactic_pca.pack(side="left", padx=1)
    
    f_btn_settings = ctk.CTkFrame(f_tsl_row, fg_color="transparent")
    f_btn_settings.pack(side="right", padx=(0,0))
    ctk.CTkButton(f_btn_settings, text="⚙ TSL", width=38, height=24, fg_color="#424242", hover_color="#616161", command=app.open_tsl_popup).pack(side="right")
    
    app.update_tactic_buttons_ui()

    # 3. MANUAL INPUT PANEL
    f_input = ctk.CTkFrame(parent, fg_color="transparent")
    f_input.pack(fill="x", padx=5, pady=(15,0))
    f_input.grid_columnconfigure((0,1,2), weight=1)

    def make_inp(p, t, v, c):
        f = ctk.CTkFrame(p, fg_color="#2b2b2b", corner_radius=6)
        f.grid(row=0, column=c, padx=3, sticky="ew")
        ctk.CTkLabel(f, text=t, font=("Roboto", 10, "bold"), text_color="#aaa").pack(pady=(2,0))
        ctk.CTkEntry(f, textvariable=v, font=("Consolas", 14, "bold"), height=30, justify="center", fg_color="transparent", border_width=0).pack(fill="x")

    make_inp(f_input, "VOL (Lot)", app.var_manual_lot, 0)
    make_inp(f_input, "TP (Price)", app.var_manual_tp, 1)
    make_inp(f_input, "SL (Price)", app.var_manual_sl, 2)

    # --- PHẦN ĐÃ FIX: MULTI-TF CONTEXT PREVIEW (V8.4.1) ---
    f_context = ctk.CTkFrame(parent, fg_color="#1E1E1E", corner_radius=6) 
    f_context.pack(fill="x", padx=5, pady=(5, 5))
    
    # Dòng 1: Chế độ (Mode) & Xu hướng (Trend)
    app.lbl_market_mode = ctk.CTkLabel(f_context, text="Mode: -- | Trend: --", 
                                      font=("Roboto", 13, "bold"), text_color="#29B6F6", anchor="w")
    app.lbl_market_mode.pack(fill="x", padx=10, pady=(5, 0))

    # Dòng 2: Khung chứa Dropdown chọn G và Thông số H/L/ATR
    f_context_bottom = ctk.CTkFrame(f_context, fg_color="transparent")
    f_context_bottom.pack(fill="x", padx=5, pady=(2, 5))

    app.var_dashboard_tf = tk.StringVar(value="G1")
    app.cbo_dashboard_tf = ctk.CTkOptionMenu(f_context_bottom, values=["G0", "G1", "G2", "G3"], 
                                            variable=app.var_dashboard_tf, width=60, height=24,
                                            font=("Roboto", 11, "bold"))
    app.cbo_dashboard_tf.pack(side="left", padx=5)

    # Label DUY NHẤT để hiển thị Swing/ATR (Xóa các bản trùng lặp cũ)
# Label DUY NHẤT để hiển thị Swing/ATR
    app.lbl_market_context = ctk.CTkLabel(f_context_bottom, text="H: -- | L: -- | ATR: --", 
                                         font=("Consolas", 14, "bold"), text_color="#78909C", anchor="w")
    app.lbl_market_context.pack(side="left", fill="x", expand=True, padx=5)

    # 4. LIVE DASHBOARD
    f_dashboard = ctk.CTkFrame(parent, fg_color="#252526", corner_radius=8, border_width=1, border_color="#333")
    f_dashboard.pack(fill="x", padx=5, pady=(5, 10))
    
    f_head_db = ctk.CTkFrame(f_dashboard, fg_color="transparent")
    f_head_db.pack(fill="x", padx=10, pady=(5,0))
    app.lbl_prev_lot = ctk.CTkLabel(f_head_db, text="LOT: 0.00", font=FONT_BOLD, text_color="#FFD700")
    app.lbl_prev_lot.pack(side="left")
    app.lbl_fee_info = ctk.CTkLabel(f_head_db, text="Cost: $0.00", font=FONT_FEE, text_color="#FFD700")
    app.lbl_fee_info.pack(side="right")
    app.lbl_dashboard_price = ctk.CTkLabel(f_dashboard, text="----.--", font=FONT_PRICE, text_color="white")
    app.lbl_dashboard_price.pack(pady=(5, 5))

    ctk.CTkFrame(f_dashboard, height=1, fg_color="#444").pack(fill="x", padx=5)
    f_grid_db = ctk.CTkFrame(f_dashboard, fg_color="transparent")
    f_grid_db.pack(fill="x", padx=5, pady=5)
    f_grid_db.columnconfigure((0,1), weight=1)

    f_rew = ctk.CTkFrame(f_grid_db, fg_color="transparent")
    f_rew.grid(row=0, column=0, sticky="nsew", padx=2)
    app.lbl_head_tp = ctk.CTkLabel(f_rew, text="TARGET (TP)", font=("Roboto", 10), text_color=COL_GREEN)
    app.lbl_head_tp.pack()
    app.lbl_prev_tp = ctk.CTkLabel(f_rew, text="---", font=("Consolas", 14), text_color=COL_GREEN)
    app.lbl_prev_tp.pack()
    app.lbl_prev_rew = ctk.CTkLabel(f_rew, text="+$0.0", font=FONT_BIG_VAL, text_color=COL_GREEN)
    app.lbl_prev_rew.pack()

    f_risk = ctk.CTkFrame(f_grid_db, fg_color="transparent")
    f_risk.grid(row=0, column=1, sticky="nsew", padx=2)
    app.lbl_head_sl = ctk.CTkLabel(f_risk, text="STOPLOSS (SL)", font=("Roboto", 10), text_color=COL_RED)
    app.lbl_head_sl.pack()
    app.lbl_prev_sl = ctk.CTkLabel(f_risk, text="---", font=("Consolas", 14), text_color=COL_RED)
    app.lbl_prev_sl.pack()
    app.lbl_prev_risk = ctk.CTkLabel(f_risk, text="-$0.0", font=FONT_BIG_VAL, text_color=COL_RED)
    app.lbl_prev_risk.pack()

    ctk.CTkFrame(f_dashboard, height=1, fg_color="#444").pack(fill="x", padx=10, pady=(5,0))
    app.lbl_tsl_preview = ctk.CTkLabel(f_dashboard, text="TSL: OFF", font=("Roboto", 13), text_color="#2196F3")
    app.lbl_tsl_preview.pack(pady=(5,5))

    # 5. EXECUTION CONTROLS
    app.seg_direction = ctk.CTkSegmentedButton(parent, values=["BUY", "SELL"], font=("Roboto", 14, "bold"), command=app.on_direction_change, height=32, selected_color=COL_GREEN, selected_hover_color="#009624")
    app.seg_direction.set("BUY")
    app.seg_direction.pack(fill="x", padx=10, pady=(5, 5))

    app.btn_action = ctk.CTkButton(parent, text="EXECUTE BUY", font=("Roboto", 16, "bold"), height=45, fg_color=COL_GREEN, hover_color="#009624", command=app.on_click_trade)
    app.btn_action.pack(fill="x", padx=10, pady=(0, 10))

    # 6. SYSTEM HEALTH
    f_sys = ctk.CTkFrame(parent, fg_color="#1a1a1a")
    f_sys.pack(fill="x", padx=5, pady=(5, 20))
    ctk.CTkLabel(f_sys, text=" SYSTEM HEALTH", font=("Roboto", 11, "bold"), text_color="gray").pack(anchor="w", padx=5, pady=(5,0))
    
    app.check_labels = {}
    checks = ["Mạng/Spread", "Daily Loss", "Số Lệnh Thua", "Số Lệnh", "Trạng thái"]
    for name in checks:
        l = ctk.CTkLabel(f_sys, text=f"• {name}", font=("Roboto", 12), text_color="gray", anchor="w")
        l.pack(fill="x", padx=10)
        app.check_labels[name] = l


def setup_right_panel(app, parent):
    """Xây dựng khung theo dõi lệnh (Treeview) và Log (Text)"""
    
    # 1. HEADER ROW
    f_head = ctk.CTkFrame(parent, fg_color="transparent", height=30)
    f_head.pack(fill="x", pady=(0, 5))
    ctk.CTkLabel(f_head, text="DANH SÁCH LỆNH ĐANG CHẠY", font=("Roboto", 16, "bold")).pack(side="left")
    
    ctk.CTkButton(f_head, text="Lịch sử", width=80, height=24, command=app.show_history_popup, fg_color="#444").pack(side="right")
    ctk.CTkButton(f_head, text="Đóng hết", width=70, height=24, fg_color="#D50000", hover_color="#B71C1C", command=app.close_all_trades).pack(side="right", padx=5)
    ctk.CTkButton(f_head, text="Đóng mục chọn", width=110, height=24, fg_color="#FF8F00", hover_color="#FF6F00", command=app.close_selected_trades).pack(side="right", padx=5)

    # 2. TREEVIEW CONTAINER
    f_tree_container = ctk.CTkFrame(parent, fg_color="#2b2b2b")
    f_tree_container.pack(fill="both", expand=True)

    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", rowheight=50, font=("Consolas", 18)) 
    style.configure("Treeview.Heading", background="#1f1f1f", foreground="#e0e0e0", font=("Roboto", 20, "bold"), relief="flat")
    style.map("Treeview", background=[('selected', '#3949ab')])

    cols = ("Ticket", "Time", "Order", "Targets", "CostInfo", "RR", "PnL", "Status", "X")
    app.tree = ttk.Treeview(f_tree_container, columns=cols, show="headings", style="Treeview", selectmode="extended") 
    
    app.tree.tag_configure("buy_row", background="#234d20", foreground="#e0e0e0") 
    app.tree.tag_configure("sell_row", background="#5c1a1b", foreground="#e0e0e0") 

    headers = ["Ticket", "Thời gian", "Thông tin Lệnh", "Chốt lời/Lỗ (SL|TP)", "Chi phí/Phí qua đêm", "Rủi ro/Kỳ vọng (%)", "Lợi nhuận", "Trạng thái", "✖"]
    widths = [180, 180, 500, 300, 350, 450, 180, 500, 50]
    anchors= ["center", "center", "w", "center", "center", "center", "center", "w", "center"]

    for c, h, w, a in zip(cols, headers, widths, anchors):
        app.tree.heading(c, text=h)
        app.tree.column(c, width=w, anchor=a, minwidth=w, stretch=False)

    sb = ttk.Scrollbar(f_tree_container, orient="vertical", command=app.tree.yview)
    sb_x = ttk.Scrollbar(f_tree_container, orient="horizontal", command=app.tree.xview)
    app.tree.configure(yscroll=sb.set, xscroll=sb_x.set)
    
    app.tree.grid(row=0, column=0, sticky="nsew")
    sb.grid(row=0, column=1, sticky="ns")
    sb_x.grid(row=1, column=0, sticky="ew")
    f_tree_container.grid_rowconfigure(0, weight=1)
    f_tree_container.grid_columnconfigure(0, weight=1)

    app.tree.bind('<ButtonRelease-1>', app.on_tree_click)
    app.tree.bind('<Button-3>', app.on_tree_right_click)

    # 3. LOGGING CONSOLE
    f_log = ctk.CTkFrame(parent, height=350, fg_color="#1e1e1e")
    f_log.pack(fill="x", pady=(10, 0))
    f_log.pack_propagate(False)

    f_log_head = ctk.CTkFrame(f_log, fg_color="transparent", height=25)
    f_log_head.pack(fill="x", padx=5, pady=2)
    ctk.CTkLabel(f_log_head, text="HỆ THỐNG GHI NHẬT KÝ (LOG)", font=("Roboto", 12, "bold"), text_color="#aaa").pack(side="left")
    ctk.CTkCheckBox(f_log_head, text="Xác nhận đóng lệnh", variable=app.var_confirm_close, font=("Roboto", 11), checkbox_width=16, checkbox_height=16).pack(side="right")

    app.txt_log = tk.Text(f_log, font=("Consolas", 18), bg="#121212", fg="#e0e0e0", bd=0, highlightthickness=0, state="disabled", wrap="word")
    app.txt_log.pack(fill="both", expand=True, padx=5, pady=(0,5))
    
    app.txt_log.tag_config("INFO", foreground="#b0bec5") 
    app.txt_log.tag_config("SUCCESS", foreground=COL_GREEN)  
    app.txt_log.tag_config("ERROR", foreground=COL_RED)    
    app.txt_log.tag_config("WARN", foreground=COL_WARN)    
    app.txt_log.tag_config("BLUE", foreground="#29B6F6")