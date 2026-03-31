# -*- coding: utf-8 -*-
# FILE: main.py
# V4.3: NESTED INDICATOR TABS & AUTO-TRADE STATUS LIGHT

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, Menu
import threading
import time
import sys
import json
import os
from datetime import datetime
import MetaTrader5 as mt5

import config
from core.exness_connector import ExnessConnector
from core.checklist_manager import ChecklistManager
from core.trade_manager import TradeManager
from core.storage_manager import load_state, save_state
from core.signal_listener import SignalListener

TSL_SETTINGS_FILE = "data/tsl_settings.json"
PRESETS_FILE = "data/presets_config.json"
BRAIN_SETTINGS_FILE = "data/brain_settings.json"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

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
COL_GRAY_BTN = "#424242"
COL_WARN = "#FFAB00"

class BotUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PRO SCALPING V4.3 - MASTER UI")
        self.geometry("1650x950")
        
        # --- BIẾN TRẠNG THÁI ---
        self.var_auto_trade = tk.BooleanVar(value=False)
        self.var_assist_math_sl = tk.BooleanVar(value=False)
        self.var_assist_preset_tp = tk.BooleanVar(value=False)
        self.var_assist_dca = tk.BooleanVar(value=False)
        self.var_assist_pca = tk.BooleanVar(value=False)
        
        self.var_strict_mode = tk.BooleanVar(value=config.STRICT_MODE_DEFAULT)
        self.var_confirm_close = tk.BooleanVar(value=True)
        self.var_account_type = tk.StringVar(value=config.DEFAULT_ACCOUNT_TYPE)
        
        self.var_manual_lot = tk.StringVar(value="")
        self.var_manual_tp = tk.StringVar(value="")
        self.var_manual_sl = tk.StringVar(value="")
        self.var_bypass_checklist = tk.BooleanVar(value=config.MANUAL_CONFIG["BYPASS_CHECKLIST"])
        self.var_direction = tk.StringVar(value="BUY") 
        
        self.tactic_states = {"BE": True, "PNL": False, "STEP_R": True}
        self.running = True
        self.tsl_states_map = {} 
        self.last_price_val = 0.0
        
        self.latest_market_context = {} 
        
        self.load_settings()

        self.connector = ExnessConnector()
        self.connector.connect()
        self.checklist_mgr = ChecklistManager(self.connector)
        self.trade_mgr = TradeManager(self.connector, self.checklist_mgr, log_callback=self.log_message)

        self.grid_columnconfigure(0, weight=0, minsize=420)
        self.grid_columnconfigure(1, weight=1) 
        self.grid_rowconfigure(0, weight=1)

        self.frm_left = ctk.CTkScrollableFrame(self, width=400, corner_radius=0, label_text="")
        self.frm_left.grid(row=0, column=0, sticky="nswe")
        self.frm_left.grid_columnconfigure(0, weight=1)
        self.setup_left_panel(self.frm_left)

        self.frm_right = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frm_right.grid(row=0, column=1, sticky="nswe", padx=10, pady=10)
        self.setup_right_panel(self.frm_right)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.thread = threading.Thread(target=self.bg_update_loop, daemon=True)
        self.thread.start()
        
        # --- SIGNAL LISTENER ---
        self.signal_listener = SignalListener(
            trade_manager=self.trade_mgr,
            get_auto_trade_cb=lambda: self.var_auto_trade.get(),
            get_preset_cb=lambda: self.cbo_preset.get(),
            get_tsl_mode_cb=self.get_current_tactic_string,
            ui_heartbeat_cb=self.update_brain_heartbeat,
            log_cb=self.log_message
        )
        self.signal_listener.start()
        
        self.log_message("System V4.3 Initialized. UI Master Ready.")

    def on_closing(self):
        self.running = False
        if hasattr(self, 'signal_listener'):
            self.signal_listener.stop()
        self.log_message("Hệ thống đang dừng...")
        try: mt5.shutdown()
        except: pass
        self.destroy()
        sys.exit(0)

    def setup_left_panel(self, parent):
        # 1. KHỐI EQUITY & STATUS
        f_top = ctk.CTkFrame(parent, fg_color="#1a1a1a", corner_radius=8)
        f_top.pack(fill="x", pady=(5, 10), padx=5)
        self.lbl_equity = ctk.CTkLabel(f_top, text="$----", font=FONT_EQUITY, text_color=COL_GREEN)
        self.lbl_equity.pack(pady=(15, 0))
        
        f_pnl = ctk.CTkFrame(f_top, fg_color="transparent")
        f_pnl.pack(pady=(0, 5))
        self.lbl_stats = ctk.CTkLabel(f_pnl, text="Today: $0.00", font=FONT_PNL, text_color="white")
        self.lbl_stats.pack(side="left", padx=5)
        ctk.CTkButton(f_pnl, text="⟳", width=30, height=20, fg_color="#333", hover_color="#444", command=self.reset_daily_stats).pack(side="left", padx=5)

        self.lbl_acc_info = ctk.CTkLabel(f_top, text="ID: --- | Server: ---", font=("Roboto", 10), text_color="gray")
        self.lbl_acc_info.pack(pady=(0, 5))
        
        self.lbl_brain_status = ctk.CTkLabel(f_top, text="🧠 BRAIN: WAITING DAEMON...", font=("Roboto", 11, "bold"), text_color="#FF8F00")
        self.lbl_brain_status.pack(pady=(0, 10))

        # 2. KHỐI CONFIG & TACTIC
        f_set = ctk.CTkFrame(parent, fg_color="transparent")
        f_set.pack(fill="x", padx=5, pady=5)
        f_set.columnconfigure(1, weight=1)

        ctk.CTkLabel(f_set, text="COIN:", font=FONT_SECTION, text_color="gray").grid(row=0, column=0, sticky="w")
        f_coin_row = ctk.CTkFrame(f_set, fg_color="transparent")
        f_coin_row.grid(row=0, column=1, sticky="ew", padx=5)
        self.cbo_symbol = ctk.CTkOptionMenu(f_coin_row, values=config.COIN_LIST, font=FONT_BOLD, width=120, command=self.on_symbol_change)
        self.cbo_symbol.set(config.DEFAULT_SYMBOL)
        self.cbo_symbol.pack(side="left")
        self.chk_force = ctk.CTkCheckBox(f_coin_row, text="Force", variable=self.var_bypass_checklist, font=("Roboto", 11, "bold"), text_color=COL_WARN, width=60, checkbox_width=18, checkbox_height=18)
        self.chk_force.pack(side="right", padx=5)

        ctk.CTkLabel(f_set, text="MODE:", font=FONT_SECTION, text_color="gray").grid(row=1, column=0, sticky="w", pady=5)
        f_mode_row = ctk.CTkFrame(f_set, fg_color="transparent")
        f_mode_row.grid(row=1, column=1, sticky="ew", padx=5)
        self.cbo_preset = ctk.CTkOptionMenu(f_mode_row, values=list(config.PRESETS.keys()), font=FONT_MAIN, width=100)
        self.cbo_preset.set(config.DEFAULT_PRESET)
        self.cbo_preset.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(f_mode_row, text="⚙", width=30, fg_color="#444", hover_color="#666", command=self.open_preset_config_popup).pack(side="left", padx=(2,0))
        self.cbo_account_type = ctk.CTkOptionMenu(f_mode_row, values=list(config.ACCOUNT_TYPES_CONFIG.keys()), font=FONT_MAIN, width=80)
        self.cbo_account_type.set(config.DEFAULT_ACCOUNT_TYPE)
        self.cbo_account_type.pack(side="right", fill="x", padx=(5,0))

        ctk.CTkLabel(f_set, text="TACTIC:", font=FONT_SECTION, text_color="gray").grid(row=2, column=0, sticky="w", pady=5)
        f_tsl_row = ctk.CTkFrame(f_set, fg_color="transparent")
        f_tsl_row.grid(row=2, column=1, sticky="ew", padx=5)

        self.btn_tactic_be = ctk.CTkButton(f_tsl_row, text="BE", width=40, command=lambda: self.toggle_tactic("BE"))
        self.btn_tactic_be.pack(side="left", padx=1)
        self.btn_tactic_pnl = ctk.CTkButton(f_tsl_row, text="PNL", width=40, command=lambda: self.toggle_tactic("PNL"))
        self.btn_tactic_pnl.pack(side="left", padx=1)
        self.btn_tactic_step = ctk.CTkButton(f_tsl_row, text="STEP", width=45, command=lambda: self.toggle_tactic("STEP_R"))
        self.btn_tactic_step.pack(side="left", padx=1)
        
        # [V4.3] Đèn trạng thái & Nút Settings
        f_btn_settings = ctk.CTkFrame(f_tsl_row, fg_color="transparent")
        f_btn_settings.pack(side="right", padx=(5,0))
        
        self.lbl_auto_light = ctk.CTkLabel(f_btn_settings, text="🔴", font=("Roboto", 14))
        self.lbl_auto_light.pack(side="left", padx=(0, 4))
        
        ctk.CTkButton(f_btn_settings, text="⚙ TSL", width=45, fg_color="#424242", hover_color="#616161", command=self.open_tsl_popup).pack(side="left", padx=2)
        ctk.CTkButton(f_btn_settings, text="⚙ BOT", width=45, fg_color="#4A148C", hover_color="#6A1B9A", command=self.open_bot_setting_popup).pack(side="left")
        
        self.update_tactic_buttons_ui()

        # 3. MANUAL INPUT & CONTEXT PREVIEW
        f_input = ctk.CTkFrame(parent, fg_color="transparent")
        f_input.pack(fill="x", padx=5, pady=(5,0))
        f_input.grid_columnconfigure((0,1,2), weight=1)

        def make_inp(p, t, v, c):
            f = ctk.CTkFrame(p, fg_color="#2b2b2b", corner_radius=6)
            f.grid(row=0, column=c, padx=3, sticky="ew")
            ctk.CTkLabel(f, text=t, font=("Roboto", 10, "bold"), text_color="#aaa").pack(pady=(2,0))
            ctk.CTkEntry(f, textvariable=v, font=("Consolas", 14, "bold"), height=30, justify="center", fg_color="transparent", border_width=0).pack(fill="x")

        make_inp(f_input, "VOL (Lot)", self.var_manual_lot, 0)
        make_inp(f_input, "TP (Price)", self.var_manual_tp, 1)
        make_inp(f_input, "SL (Price)", self.var_manual_sl, 2)

        self.lbl_market_context = ctk.CTkLabel(parent, text="Trend: -- | SHigh: -- | SLow: -- | ATR: --", font=("Roboto", 11, "italic"), text_color="#78909C")
        self.lbl_market_context.pack(pady=(2, 5))

        # 4. DASHBOARD PREVIEW
        f_dashboard = ctk.CTkFrame(parent, fg_color="#252526", corner_radius=8, border_width=1, border_color="#333")
        f_dashboard.pack(fill="x", padx=5, pady=(5, 10))
        
        f_head_db = ctk.CTkFrame(f_dashboard, fg_color="transparent")
        f_head_db.pack(fill="x", padx=10, pady=(5,0))
        self.lbl_prev_lot = ctk.CTkLabel(f_head_db, text="LOT: 0.00", font=FONT_BOLD, text_color="#FFD700")
        self.lbl_prev_lot.pack(side="left")
        self.lbl_fee_info = ctk.CTkLabel(f_head_db, text="Cost: $0.00", font=FONT_FEE, text_color="#FFD700")
        self.lbl_fee_info.pack(side="right")
        self.lbl_dashboard_price = ctk.CTkLabel(f_dashboard, text="----.--", font=FONT_PRICE, text_color="white")
        self.lbl_dashboard_price.pack(pady=(5, 5))

        ctk.CTkFrame(f_dashboard, height=1, fg_color="#444").pack(fill="x", padx=5)
        f_grid_db = ctk.CTkFrame(f_dashboard, fg_color="transparent")
        f_grid_db.pack(fill="x", padx=5, pady=5)
        f_grid_db.columnconfigure((0,1), weight=1)

        f_rew = ctk.CTkFrame(f_grid_db, fg_color="transparent")
        f_rew.grid(row=0, column=0, sticky="nsew", padx=2)
        self.lbl_head_tp = ctk.CTkLabel(f_rew, text="TARGET (TP)", font=("Roboto", 10), text_color=COL_GREEN)
        self.lbl_head_tp.pack()
        self.lbl_prev_tp = ctk.CTkLabel(f_rew, text="---", font=("Consolas", 14), text_color=COL_GREEN)
        self.lbl_prev_tp.pack()
        self.lbl_prev_rew = ctk.CTkLabel(f_rew, text="+$0.0", font=FONT_BIG_VAL, text_color=COL_GREEN)
        self.lbl_prev_rew.pack()

        f_risk = ctk.CTkFrame(f_grid_db, fg_color="transparent")
        f_risk.grid(row=0, column=1, sticky="nsew", padx=2)
        self.lbl_head_sl = ctk.CTkLabel(f_risk, text="STOPLOSS (SL)", font=("Roboto", 10), text_color=COL_RED)
        self.lbl_head_sl.pack()
        self.lbl_prev_sl = ctk.CTkLabel(f_risk, text="---", font=("Consolas", 14), text_color=COL_RED)
        self.lbl_prev_sl.pack()
        self.lbl_prev_risk = ctk.CTkLabel(f_risk, text="-$0.0", font=FONT_BIG_VAL, text_color=COL_RED)
        self.lbl_prev_risk.pack()

        ctk.CTkFrame(f_dashboard, height=1, fg_color="#444").pack(fill="x", padx=10, pady=(5,0))
        self.lbl_tsl_preview = ctk.CTkLabel(f_dashboard, text="TSL: OFF", font=("Roboto", 13), text_color="#2196F3")
        self.lbl_tsl_preview.pack(pady=(5,5))

        self.seg_direction = ctk.CTkSegmentedButton(parent, values=["BUY", "SELL"], font=("Roboto", 14, "bold"), command=self.on_direction_change, height=32, selected_color=COL_GREEN, selected_hover_color="#009624")
        self.seg_direction.set("BUY")
        self.seg_direction.pack(fill="x", padx=10, pady=(5, 5))

        self.btn_action = ctk.CTkButton(parent, text="EXECUTE BUY", font=("Roboto", 16, "bold"), height=45, fg_color=COL_GREEN, hover_color="#009624", command=self.on_click_trade)
        self.btn_action.pack(fill="x", padx=10, pady=(0, 10))

        # 5. SYSTEM HEALTH
        f_sys = ctk.CTkFrame(parent, fg_color="#1a1a1a")
        f_sys.pack(fill="x", padx=5, pady=(5, 20))
        ctk.CTkLabel(f_sys, text=" SYSTEM HEALTH", font=("Roboto", 11, "bold"), text_color="gray").pack(anchor="w", padx=5, pady=(5,0))
        
        self.check_labels = {}
        checks = ["Mạng/Spread", "Daily Loss", "Số Lệnh Thua", "Số Lệnh", "Trạng thái"]
        for name in checks:
            l = ctk.CTkLabel(f_sys, text=f"• {name}", font=("Roboto", 12), text_color="gray", anchor="w")
            l.pack(fill="x", padx=10)
            self.check_labels[name] = l

    def setup_right_panel(self, parent):
        f_head = ctk.CTkFrame(parent, fg_color="transparent", height=30)
        f_head.pack(fill="x", pady=(0, 5))
        ctk.CTkLabel(f_head, text="RUNNING TRADES (Realtime)", font=("Roboto", 16, "bold")).pack(side="left")
        
        ctk.CTkButton(f_head, text="History", width=80, height=24, command=self.show_history_popup, fg_color="#444").pack(side="right")
        ctk.CTkButton(f_head, text="Close All", width=70, height=24, fg_color="#D50000", hover_color="#B71C1C", command=self.close_all_trades).pack(side="right", padx=5)
        ctk.CTkButton(f_head, text="Close Selected", width=100, height=24, fg_color="#FF8F00", hover_color="#FF6F00", command=self.close_selected_trades).pack(side="right", padx=5)

        f_tree_container = ctk.CTkFrame(parent, fg_color="#2b2b2b")
        f_tree_container.pack(fill="both", expand=True)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#2b2b2b", foreground="white", fieldbackground="#2b2b2b", rowheight=35, font=("Consolas", 11)) 
        style.configure("Treeview.Heading", background="#1f1f1f", foreground="#e0e0e0", font=("Roboto", 10, "bold"), relief="flat")
        style.map("Treeview", background=[('selected', '#3949ab')])

        cols = ("Ticket", "Time", "Order", "Targets", "CostInfo", "RR", "PnL", "Status", "X")
        self.tree = ttk.Treeview(f_tree_container, columns=cols, show="headings", style="Treeview", selectmode="extended") 
        
        headers = ["Ticket", "Time", "Order Info (@Entry)", "Targets (SL | TP)", "Cost | Swap", "Risk | Reward (%)", "PnL", "Status", "✖"]
        widths = [95, 100, 240, 180, 200, 295, 90, 220, 40]
        anchors= ["center", "center", "w", "center", "center", "center", "center", "w", "center"]

        for c, h, w, a in zip(cols, headers, widths, anchors):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor=a, minwidth=w, stretch=False)

        sb = ttk.Scrollbar(f_tree_container, orient="vertical", command=self.tree.yview)
        sb_x = ttk.Scrollbar(f_tree_container, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscroll=sb.set, xscroll=sb_x.set)
        
        self.tree.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        sb_x.grid(row=1, column=0, sticky="ew")
        f_tree_container.grid_rowconfigure(0, weight=1)
        f_tree_container.grid_columnconfigure(0, weight=1)

        self.tree.bind('<ButtonRelease-1>', self.on_tree_click)
        self.tree.bind('<Button-3>', self.on_tree_right_click)

        f_log = ctk.CTkFrame(parent, height=350, fg_color="#1e1e1e")
        f_log.pack(fill="x", pady=(10, 0))
        f_log.pack_propagate(False)

        f_log_head = ctk.CTkFrame(f_log, fg_color="transparent", height=25)
        f_log_head.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(f_log_head, text="SYSTEM LOG", font=("Roboto", 12, "bold"), text_color="#aaa").pack(side="left")
        ctk.CTkCheckBox(f_log_head, text="Safe Close", variable=self.var_confirm_close, font=("Roboto", 11), checkbox_width=16, checkbox_height=16).pack(side="right")

        self.txt_log = tk.Text(f_log, font=("Consolas", 12), bg="#121212", fg="#e0e0e0", bd=0, highlightthickness=0, state="disabled", wrap="word")
        self.txt_log.pack(fill="both", expand=True, padx=5, pady=(0,5))
        
        self.txt_log.tag_config("INFO", foreground="#b0bec5")
        self.txt_log.tag_config("SUCCESS", foreground=COL_GREEN) 
        self.txt_log.tag_config("ERROR", foreground=COL_RED)   
        self.txt_log.tag_config("WARN", foreground=COL_WARN)    
        self.txt_log.tag_config("BLUE", foreground="#29B6F6")

    # --- CALLBACK CẬP NHẬT TRẠNG THÁI & BỐI CẢNH TỪ DAEMON ---
    def update_brain_heartbeat(self, heartbeat: dict):
        status = heartbeat.get("status", "UNKNOWN")
        symbol = heartbeat.get("active_symbols", [""])[0]
        
        if "SLEEPING" in status:
            self.lbl_brain_status.configure(text=f"🧠 BRAIN: {status} ({symbol})", text_color="#2196F3")
        elif status == "HEALTHY":
            self.lbl_brain_status.configure(text=f"🧠 BRAIN: ONLINE ({symbol})", text_color=COL_GREEN)
        else:
            self.lbl_brain_status.configure(text=f"🧠 BRAIN: {status}", text_color=COL_RED)
            
        context = heartbeat.get("context", {})
        if context:
            self.latest_market_context = context
            tr = context.get("trend", "--")
            sh = context.get("swing_high", "--")
            sl = context.get("swing_low", "--")
            atr = context.get("atr", "--")
            
            if isinstance(sh, float): sh = f"{sh:.2f}"
            if isinstance(sl, float): sl = f"{sl:.2f}"
            if isinstance(atr, float): atr = f"{atr:.2f}"
            
            self.lbl_market_context.configure(text=f"Trend: {tr} | SHigh: {sh} | SLow: {sl} | ATR: {atr}")

    def on_auto_trade_toggle(self):
        if self.var_auto_trade.get():
            self.lbl_auto_light.configure(text="🟢")
            self.log_message("🟢 Auto-Trade Daemon ĐÃ BẬT. Bot sẽ tự động bắn lệnh khi có tín hiệu.")
        else:
            self.lbl_auto_light.configure(text="🔴")
            self.log_message("🔴 Auto-Trade Daemon ĐÃ TẮT. Trở về chế độ bắn tay (Manual).")

    def get_current_tactic_string(self):
        active = [k for k, v in self.tactic_states.items() if v]
        base_tactic = "+".join(active) if active else "OFF"
        if self.var_assist_dca.get(): base_tactic += "+AUTO_DCA"
        if self.var_assist_pca.get(): base_tactic += "+AUTO_PCA"
        return base_tactic

    # --- [V4.3] NÂNG CẤP POPUP TABVIEW LỒNG NHAU (NESTED) ---
    def open_bot_setting_popup(self):
        top = ctk.CTkToplevel(self)
        top.title("Bot Engine & Settings")
        top.geometry("500x650")
        top.attributes("-topmost", True)
        
        tabview = ctk.CTkTabview(top)
        tabview.pack(fill="both", expand=True, padx=15, pady=15)
        
        tabview.add("CORE ENGINE")
        tabview.add("INDICATORS")
        tabview.add("MANUAL ASSIST")
        
        # --- TAB 1: CORE ENGINE ---
        tab_core = tabview.tab("CORE ENGINE")
        ctk.CTkLabel(tab_core, text="Tự động bóp cò khi Brain có tín hiệu:", text_color="gray").pack(pady=(20,5))
        sw_auto = ctk.CTkSwitch(tab_core, text="AUTO-TRADING DAEMON", variable=self.var_auto_trade, font=("Roboto", 14, "bold"), text_color=COL_GREEN, command=self.on_auto_trade_toggle)
        sw_auto.pack(pady=10)
        
        # --- TAB 2: INDICATORS (NESTED TABVIEW) ---
        tab_ind = tabview.tab("INDICATORS")
        
        inner_tabview = ctk.CTkTabview(tab_ind)
        inner_tabview.pack(fill="both", expand=True, padx=5, pady=5)
        
        tab_trend = inner_tabview.add("Trend H1")
        tab_entry = inner_tabview.add("Entry M15")
        tab_sl = inner_tabview.add("Math SL")

        def add_switch(parent, label, default_val, desc):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=5)
            var = tk.BooleanVar(value=default_val)
            ctk.CTkSwitch(f, text=label, variable=var, font=FONT_BOLD).pack(anchor="w")
            ctk.CTkLabel(f, text=desc, font=("Roboto", 11, "italic"), text_color="gray").pack(anchor="w", padx=25)
            return var

        def add_input(parent, label, default_val, desc):
            f = ctk.CTkFrame(parent, fg_color="transparent")
            f.pack(fill="x", padx=10, pady=5)
            row = ctk.CTkFrame(f, fg_color="transparent")
            row.pack(fill="x")
            ctk.CTkLabel(row, text=label, font=FONT_BOLD).pack(side="left")
            entry = ctk.CTkEntry(row, width=80, justify="center")
            entry.insert(0, str(default_val))
            entry.pack(side="right")
            ctk.CTkLabel(f, text=desc, font=("Roboto", 11, "italic"), text_color="gray").pack(anchor="w", pady=(0,2))
            return entry

        # --- Sub-Tab: Trend H1 ---
        var_ema = add_switch(tab_trend, "Bật Lọc EMA 50", getattr(config, "USE_EMA_TREND_FILTER", True), "Dùng đường EMA 50 để xác định xu hướng dài hạn")
        var_st = add_switch(tab_trend, "Bật Lọc Supertrend", getattr(config, "USE_SUPERTREND_FILTER", True), "Dùng Supertrend để xác nhận xu hướng")
        var_adx = add_switch(tab_trend, "Bật Lọc ADX", getattr(config, "USE_ADX_FILTER", True), "Lọc nhiễu Sideways bằng sức mạnh ADX")
        var_adx_grey = add_switch(tab_trend, "Bật Vùng Xám ADX", getattr(config, "USE_ADX_GREY_ZONE", False), "Thận trọng khi ADX nằm trong khoảng 18-23")
        e_adx_min = add_input(tab_trend, "Ngưỡng ADX tối thiểu:", getattr(config, "ADX_MIN_LEVEL", 20), "Chỉ giao dịch khi ADX lớn hơn mức này")

        # --- Sub-Tab: Entry M15 ---
        var_candle = add_switch(tab_entry, "Bật Lọc Thân Nến", getattr(config, "USE_CANDLE_FILTER", True), "Yêu cầu nến Breakout phải có thân nến rõ ràng")
        e_min_body = add_input(tab_entry, "% Thân nến tối thiểu:", getattr(config, "min_body_percent", 50.0), "Tỷ lệ thân/râu nến (VD: 50%)")
        var_vol = add_switch(tab_entry, "Bật Lọc Khối Lượng (Volume)", getattr(config, "USE_VOLUME_FILTER", True), "Xác nhận Breakout bằng Volume đột biến")
        e_vol_period = add_input(tab_entry, "Chu kỳ VMA (Volume):", getattr(config, "volume_ma_period", 20), "Số nến để tính trung bình Volume")

        # --- Sub-Tab: Math SL ---
        e_swing = add_input(tab_sl, "Chu kỳ Swing Point:", getattr(config, "swing_period", 5), "Số nến (window) để tìm đỉnh/đáy gần nhất")
        e_atr = add_input(tab_sl, "Chu kỳ ATR:", getattr(config, "atr_period", 14), "Số nến để tính toán độ giật thị trường")
        e_sl_mult = add_input(tab_sl, "Hệ số đệm SL (ATR):", getattr(config, "sl_atr_multiplier", 0.2), "SL cách đỉnh/đáy = Mức đệm * Giá trị ATR")

        def save_indicators():
            try:
                # Update Variables
                config.USE_EMA_TREND_FILTER = var_ema.get()
                config.USE_SUPERTREND_FILTER = var_st.get()
                config.USE_ADX_FILTER = var_adx.get()
                config.USE_ADX_GREY_ZONE = var_adx_grey.get()
                config.ADX_MIN_LEVEL = float(e_adx_min.get())
                
                config.USE_CANDLE_FILTER = var_candle.get()
                config.min_body_percent = float(e_min_body.get())
                config.USE_VOLUME_FILTER = var_vol.get()
                config.volume_ma_period = int(e_vol_period.get())
                
                config.swing_period = int(e_swing.get())
                config.atr_period = int(e_atr.get())
                config.sl_atr_multiplier = float(e_sl_mult.get())
                
                os.makedirs("data", exist_ok=True)
                settings = {
                    "USE_EMA_TREND_FILTER": config.USE_EMA_TREND_FILTER,
                    "USE_SUPERTREND_FILTER": config.USE_SUPERTREND_FILTER,
                    "USE_ADX_FILTER": config.USE_ADX_FILTER,
                    "USE_ADX_GREY_ZONE": config.USE_ADX_GREY_ZONE,
                    "ADX_MIN_LEVEL": config.ADX_MIN_LEVEL,
                    "USE_CANDLE_FILTER": config.USE_CANDLE_FILTER,
                    "min_body_percent": config.min_body_percent,
                    "USE_VOLUME_FILTER": config.USE_VOLUME_FILTER,
                    "volume_ma_period": config.volume_ma_period,
                    "swing_period": config.swing_period,
                    "atr_period": config.atr_period,
                    "sl_atr_multiplier": config.sl_atr_multiplier
                }
                with open(BRAIN_SETTINGS_FILE, "w") as f:
                    json.dump(settings, f, indent=4)
                self.log_message("✅ Đã lưu cấu hình Indicators cho Bot Daemon.")
            except ValueError:
                messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ")

        ctk.CTkButton(tab_ind, text="SAVE INDICATORS", fg_color=COL_BLUE_ACCENT, command=save_indicators).pack(pady=10)

        # --- TAB 3: MANUAL ASSIST ---
        tab_ast = tabview.tab("MANUAL ASSIST")
        ctk.CTkLabel(tab_ast, text="Tùy chọn Ủy quyền Mặc định (khi trade tay):", text_color="gray").pack(pady=(20,10))
        
        ctk.CTkCheckBox(tab_ast, text="Auto lấy Math SL (Dựa vào Swing/ATR)", variable=self.var_assist_math_sl).pack(anchor="w", padx=50, pady=10)
        ctk.CTkCheckBox(tab_ast, text="Auto tính Preset TP (Dựa vào R:R)", variable=self.var_assist_preset_tp).pack(anchor="w", padx=50, pady=10)
        ctk.CTkCheckBox(tab_ast, text="Auto DCA (Trung bình giá xuống) - WIP", variable=self.var_assist_dca).pack(anchor="w", padx=50, pady=10)
        ctk.CTkCheckBox(tab_ast, text="Auto PCA (Nhồi thuận xu hướng) - WIP", variable=self.var_assist_pca).pack(anchor="w", padx=50, pady=10)
        
        ctk.CTkLabel(top, text="Ghi chú: Các thay đổi có hiệu lực ngay lập tức.", font=("Roboto", 11, "italic"), text_color="gray").pack(pady=(0, 10))

    # --- NÂNG CẤP POPUP EDIT LỆNH ---
    def open_edit_popup(self, ticket):
        positions = self.connector.get_all_open_positions()
        pos = next((p for p in positions if p.ticket == ticket), None)
        if not pos: return
        
        top = ctk.CTkToplevel(self)
        top.title(f"Edit #{ticket}")
        top.geometry("380x600")
        top.attributes("-topmost", True)
        
        acc = self.connector.get_account_info()
        balance = acc['balance'] if acc else 1000.0
        sym_info = mt5.symbol_info(pos.symbol)
        c_size = sym_info.trade_contract_size if sym_info else 1.0
        is_buy = pos.type == mt5.ORDER_TYPE_BUY
        
        # 1. KHỐI NHẬP TAY (GIỮ NGUYÊN CŨ)
        ctk.CTkLabel(top, text="NEW SL:", font=FONT_BOLD).pack(pady=(10, 2))
        ent_sl = ctk.CTkEntry(top, justify="center"); ent_sl.insert(0, str(pos.sl)); ent_sl.pack()
        lbl_hint_sl = ctk.CTkLabel(top, text="~ -$0.00", text_color="gray", font=("Roboto", 11))
        lbl_hint_sl.pack(pady=(0, 5))

        ctk.CTkLabel(top, text="NEW TP:", font=FONT_BOLD).pack(pady=(5, 2))
        ent_tp = ctk.CTkEntry(top, justify="center"); ent_tp.insert(0, str(pos.tp)); ent_tp.pack()
        lbl_hint_tp = ctk.CTkLabel(top, text="~ +$0.00", text_color="gray", font=("Roboto", 11))
        lbl_hint_tp.pack(pady=(0, 5))
        
        def update_edit_previews(*args):
            if not ent_sl.winfo_exists(): return
            try:
                new_sl, new_tp = float(ent_sl.get() or 0), float(ent_tp.get() or 0)
                if new_sl > 0:
                    loss_dist = pos.price_open - new_sl if is_buy else new_sl - pos.price_open
                    loss_usd = loss_dist * pos.volume * c_size
                    if loss_usd < 0:
                        lbl_hint_sl.configure(text=f"~ +${abs(loss_usd):.2f} (Lock)", text_color="#66BB6A")
                    else:
                        lbl_hint_sl.configure(text=f"~ -${loss_usd:.2f} ({loss_usd/balance*100:.2f}%)", text_color="#EF5350")
                else: lbl_hint_sl.configure(text="~ No SL", text_color="gray")

                if new_tp > 0:
                    prof_dist = new_tp - pos.price_open if is_buy else pos.price_open - new_tp
                    prof_usd = prof_dist * pos.volume * c_size
                    if prof_usd > 0:
                        lbl_hint_tp.configure(text=f"~ +${prof_usd:.2f} ({prof_usd/balance*100:.2f}%)", text_color="#66BB6A")
                    else:
                        lbl_hint_tp.configure(text="Invalid TP", text_color="#EF5350")
                else: lbl_hint_tp.configure(text="~ No TP", text_color="gray")
            except ValueError:
                 pass

        ent_sl.bind("<KeyRelease>", update_edit_previews)
        ent_tp.bind("<KeyRelease>", update_edit_previews)
        update_edit_previews()

        # 2. ĐƯỜNG KẺ NGĂN CÁCH
        ctk.CTkFrame(top, height=2, fg_color="#333").pack(fill="x", padx=30, pady=10)

        # 3. KHỐI BOT ASSIGNMENT
        ctk.CTkLabel(top, text="BOT ASSIGNMENT (Ủy quyền):", font=FONT_BOLD, text_color="#90CAF9").pack(pady=(0, 10))
        
        f_bot_actions = ctk.CTkFrame(top, fg_color="transparent")
        f_bot_actions.pack(fill="x", padx=20)
        
        def apply_math_sl():
            sl_val = self.latest_market_context.get("swing_low") if is_buy else self.latest_market_context.get("swing_high")
            atr_val = self.latest_market_context.get("atr")
            if sl_val and atr_val:
                sl_mult = getattr(config, "sl_atr_multiplier", 0.2)
                calc_sl = sl_val - (atr_val * sl_mult) if is_buy else sl_val + (atr_val * sl_mult)
                ent_sl.delete(0, 'end'); ent_sl.insert(0, f"{calc_sl:.2f}")
                update_edit_previews()
            else:
                messagebox.showwarning("Thiếu Data", "Chưa có dữ liệu Swing/ATR từ Daemon.")

        def apply_preset_tp():
            try:
                curr_sl = float(ent_sl.get())
                if curr_sl <= 0: raise ValueError
                params = config.PRESETS.get(self.cbo_preset.get(), config.PRESETS["SCALPING"])
                rr = params.get("TP_RR_RATIO", 1.5)
                dist = abs(pos.price_open - curr_sl)
                calc_tp = pos.price_open + (dist * rr) if is_buy else pos.price_open - (dist * rr)
                ent_tp.delete(0, 'end'); ent_tp.insert(0, f"{calc_tp:.2f}")
                update_edit_previews()
            except:
                messagebox.showwarning("Lỗi", "Hãy xác định SL (hoặc Math SL) trước khi tính TP.")

        ctk.CTkButton(f_bot_actions, text="Lấy Math SL", width=140, fg_color="#1565C0", command=apply_math_sl).pack(side="left", padx=5)
        ctk.CTkButton(f_bot_actions, text="Lấy Preset TP", width=140, fg_color="#2E7D32", command=apply_preset_tp).pack(side="right", padx=5)
        
        # Checkbox DCA/PCA Override
        f_chk = ctk.CTkFrame(top, fg_color="transparent")
        f_chk.pack(pady=10)
        chk_dca = ctk.CTkCheckBox(f_chk, text="Cho phép Auto DCA", font=("Roboto", 11), text_color="gray"); chk_dca.pack(side="left", padx=10)
        chk_pca = ctk.CTkCheckBox(f_chk, text="Cho phép Auto PCA", font=("Roboto", 11), text_color="gray"); chk_pca.pack(side="left")

        # 4. TACTIC OVERRIDE
        ctk.CTkLabel(top, text="TACTIC OVERRIDE:", font=FONT_BOLD, text_color="#FFB300").pack(pady=(10, 5))
        f_btns = ctk.CTkFrame(top, fg_color="transparent")
        f_btns.pack()
        
        cur_tstr = self.trade_mgr.get_trade_tactic(ticket)
        p_states = {"BE": "BE" in cur_tstr, "PNL": "PNL" in cur_tstr, "STEP_R": "STEP_R" in cur_tstr}
        
        if "AUTO_DCA" in cur_tstr: chk_dca.select()
        if "AUTO_PCA" in cur_tstr: chk_pca.select()
        
        lbl_tactic_preview = ctk.CTkLabel(top, text="Status: Loading...", font=("Roboto", 12), text_color="gray")
        lbl_tactic_preview.pack(pady=(2, 5))

        def live_update_tactic_status():
            if not lbl_tactic_preview.winfo_exists(): return
            if "Unsaved" not in lbl_tactic_preview.cget("text"):
                new_stt = self.tsl_states_map.get(ticket, "Monitoring...")
                lbl_tactic_preview.configure(text=f"Status: {new_stt}")
            top.after(500, live_update_tactic_status) 
            
        live_update_tactic_status()

        def update_pbtns():
            b_be.configure(fg_color=COL_BLUE_ACCENT if p_states["BE"] else COL_GRAY_BTN)
            b_pnl.configure(fg_color=COL_BLUE_ACCENT if p_states["PNL"] else COL_GRAY_BTN)
            b_step.configure(fg_color=COL_BLUE_ACCENT if p_states["STEP_R"] else COL_GRAY_BTN)

        def tog(k):
            p_states[k] = not p_states[k]
            update_pbtns()
            lbl_tactic_preview.configure(text="Status: * Unsaved Tactic Changes *", text_color=COL_WARN)

        b_be = ctk.CTkButton(f_btns, text="BE", width=50, command=lambda: tog("BE")); b_be.pack(side="left", padx=2)
        b_pnl = ctk.CTkButton(f_btns, text="PNL", width=50, command=lambda: tog("PNL")); b_pnl.pack(side="left", padx=2)
        b_step = ctk.CTkButton(f_btns, text="STEP", width=50, command=lambda: tog("STEP_R")); b_step.pack(side="left", padx=2)
        update_pbtns()

        # 5. LƯU LẠI
        def save():
            try:
                sl_val, tp_val = float(ent_sl.get()), float(ent_tp.get())
            except ValueError:
                messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ.")
                return

            try:
                self.connector.modify_position(ticket, sl_val, tp_val)
                act = [k for k,v in p_states.items() if v]
                new_t = "+".join(act) if act else "OFF"
                if chk_dca.get(): new_t += "+AUTO_DCA"
                if chk_pca.get(): new_t += "+AUTO_PCA"
                
                self.trade_mgr.update_trade_tactic(ticket, new_t)
                
                ent_sl.unbind("<KeyRelease>"); ent_tp.unbind("<KeyRelease>")
                top.destroy()
                self.log_message(f"Updated #{ticket} [{new_t}]")
            except Exception as e:
                self.log_message(f"Lỗi khi update lệnh: {e}", error=True)

        ctk.CTkButton(top, text="UPDATE NOW", height=40, fg_color="#2e7d32", command=save).pack(pady=15, fill="x", padx=30)

    # --- CÁC HÀM CÒN LẠI (GIỮ NGUYÊN) ---
    def close_selected_trades(self):
        selected = self.tree.selection()
        if not selected: 
            messagebox.showinfo("Info", "Vui lòng chọn ít nhất 1 lệnh (Dùng Shift/Ctrl để chọn nhiều).")
            return
        if self.var_confirm_close.get() and not messagebox.askyesno("Confirm", f"Đóng {len(selected)} lệnh đã chọn?"): return
        for item in selected:
            ticket = int(item)
            threading.Thread(target=lambda t=ticket: self.connector.close_position(
                next((p for p in self.connector.get_all_open_positions() if p.ticket==t), None)
            )).start()

    def close_all_trades(self):
        items = self.tree.get_children()
        if not items: return
        if self.var_confirm_close.get() and not messagebox.askyesno("Confirm", "KHẨN CẤP: Đóng TOÀN BỘ lệnh?"): return
        for item in items:
            ticket = int(item)
            threading.Thread(target=lambda t=ticket: self.connector.close_position(
                next((p for p in self.connector.get_all_open_positions() if p.ticket==t), None)
            )).start()

    def toggle_tactic(self, mode):
        self.tactic_states[mode] = not self.tactic_states[mode]
        self.update_tactic_buttons_ui()
        
    def update_tactic_buttons_ui(self):
        def set_btn(btn, is_active):
            btn.configure(fg_color=COL_BLUE_ACCENT if is_active else COL_GRAY_BTN)
        set_btn(self.btn_tactic_be, self.tactic_states["BE"])
        set_btn(self.btn_tactic_pnl, self.tactic_states["PNL"])
        set_btn(self.btn_tactic_step, self.tactic_states["STEP_R"])

    def log_message(self, msg, error=False):
        ts = time.strftime("%H:%M:%S")
        txt = f"[{ts}] {msg}\n"
        tag = "INFO"
        if error or "ERR" in msg or "FAIL" in msg or "PnL: -" in msg: tag = "ERROR"
        elif "SUCCESS" in msg or "Húp" in msg: tag = "SUCCESS"
        elif "WARN" in msg or "[FORCE]" in msg: tag = "WARN"
        elif "Exec" in msg or "[TSL]" in msg: tag = "BLUE"
        def _write():
            try:
                if self.txt_log.winfo_exists():
                    self.txt_log.configure(state="normal")
                    self.txt_log.insert("end", txt, tag)
                    self.txt_log.see("end")
                    self.txt_log.configure(state="disabled")
            except: pass
        self.after(0, _write)

    def get_fee_config(self, symbol):
        acc_type = self.cbo_account_type.get()
        if acc_type in ["PRO", "STANDARD"]: return 0.0
        specific_rate = config.COMMISSION_RATES.get(symbol, -1)
        if specific_rate != -1: return specific_rate
        acc_cfg = config.ACCOUNT_TYPES_CONFIG.get(acc_type, config.ACCOUNT_TYPES_CONFIG["STANDARD"])
        return acc_cfg.get("COMMISSION_PER_LOT", 0.0)

    def on_symbol_change(self, new_symbol):
        self.lbl_dashboard_price.configure(text="Loading...", text_color="gray")
        threading.Thread(target=lambda: mt5.symbol_select(new_symbol, True)).start()

    def on_direction_change(self, value):
        self.var_direction.set(value)
        sym = self.cbo_symbol.get()
        if value == "BUY": self.btn_action.configure(text=f"BUY {sym}", fg_color=COL_GREEN, hover_color="#009624")
        else: self.btn_action.configure(text=f"SELL {sym}", fg_color=COL_RED, hover_color="#B71C1C")

    def load_settings(self):
        if os.path.exists(TSL_SETTINGS_FILE):
            try:
                with open(TSL_SETTINGS_FILE, "r") as f: config.TSL_CONFIG.update(json.load(f))
            except: pass
        if os.path.exists(PRESETS_FILE):
            try:
                with open(PRESETS_FILE, "r") as f: config.PRESETS.update(json.load(f))
            except: pass
        if os.path.exists(BRAIN_SETTINGS_FILE):
            try:
                with open(BRAIN_SETTINGS_FILE, "r") as f:
                    bs = json.load(f)
                    for k, v in bs.items(): setattr(config, k, v)
            except: pass

    def save_settings(self):
        try:
            os.makedirs("data", exist_ok=True)
            with open(TSL_SETTINGS_FILE, "w") as f: json.dump(config.TSL_CONFIG, f, indent=4)
            with open(PRESETS_FILE, "w") as f: json.dump(config.PRESETS, f, indent=4)
        except: pass

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            col = self.tree.identify_column(event.x)
            row_id = self.tree.identify_row(event.y)
            if row_id and col == "#9": self.handle_close_request(int(row_id))

    def on_tree_right_click(self, event):
        row_id = self.tree.identify_row(event.y)
        selected = self.tree.selection()
        menu = Menu(self, tearoff=0)
        
        if len(selected) > 1:
            menu.add_command(label=f"❌ Close {len(selected)} Selected Trades", command=self.close_selected_trades)
        else:
            if row_id:
                self.tree.selection_set(row_id)
                ticket = int(row_id)
                menu.add_command(label=f"📝 Edit #{ticket}", command=lambda: self.open_edit_popup(ticket))
                menu.add_separator()
                menu.add_command(label="❌ Close Now", command=lambda: self.handle_close_request(ticket))
        
        menu.post(event.x_root, event.y_root)

    def open_preset_config_popup(self):
        p_name = self.cbo_preset.get()
        data = config.PRESETS.get(p_name, {})
        
        top = ctk.CTkToplevel(self)
        top.title(f"Config: {p_name}")
        top.geometry("400x450") 
        top.attributes("-topmost", True)
        
        acc = self.connector.get_account_info()
        current_equity = acc['equity'] if acc else 1000.0 
        sym = self.cbo_symbol.get()
        tick = mt5.symbol_info_tick(sym)
        current_price = tick.ask if tick else 1000.0
        
        ctk.CTkLabel(top, text=f"PRESET: {p_name}", font=FONT_BOLD).pack(pady=10)
        
        ctk.CTkLabel(top, text="Risk (% of Balance)").pack()
        e_risk = ctk.CTkEntry(top, justify="center"); e_risk.insert(0, str(data.get("RISK_PERCENT", config.RISK_PER_TRADE_PERCENT))); e_risk.pack()
        lbl_hint_risk = ctk.CTkLabel(top, text="~ -$0.00", text_color="gray", font=("Roboto", 11)); lbl_hint_risk.pack(pady=(0, 5))

        ctk.CTkLabel(top, text="SL Distance (% of Price)").pack()
        e_sl = ctk.CTkEntry(top, justify="center"); e_sl.insert(0, str(data.get("SL_PERCENT", 0.5))); e_sl.pack()
        lbl_hint_sl = ctk.CTkLabel(top, text="~ Price: 0.00", text_color="gray", font=("Roboto", 11)); lbl_hint_sl.pack(pady=(0, 5))
        
        ctk.CTkLabel(top, text="TP Multiplier (Reward/Risk)").pack()
        e_tp = ctk.CTkEntry(top, justify="center"); e_tp.insert(0, str(data.get("TP_RR_RATIO", 2.0))); e_tp.pack()
        lbl_hint_tp = ctk.CTkLabel(top, text="~ +$0.00", text_color="gray", font=("Roboto", 11)); lbl_hint_tp.pack(pady=(0, 10))
        
        def update_previews(*args):
            if not e_risk.winfo_exists(): return
            try:
                r_val, sl_val, tp_val = float(e_risk.get() or 0), float(e_sl.get() or 0), float(e_tp.get() or 0)
                risk_usd = current_equity * (r_val / 100)
                lbl_hint_risk.configure(text=f"(~ Mất ${risk_usd:.2f} nếu dính SL)", text_color="#EF5350")
                sl_dist = current_price * (sl_val / 100)
                sl_price_buy = current_price - sl_dist
                lbl_hint_sl.configure(text=f"(~ Đặt SL quanh {sl_price_buy:.2f} cho BUY | Giá: {current_price:.2f})", text_color="#B0BEC5")
                rew_usd = risk_usd * tp_val
                lbl_hint_tp.configure(text=f"(~ Lãi ${rew_usd:.2f} nếu chạm TP)", text_color="#66BB6A")
            except ValueError:
                lbl_hint_risk.configure(text="Nhập số hợp lệ..."); lbl_hint_sl.configure(text="Nhập số hợp lệ..."); lbl_hint_tp.configure(text="Nhập số hợp lệ...")

        e_risk.bind("<KeyRelease>", update_previews); e_sl.bind("<KeyRelease>", update_previews); e_tp.bind("<KeyRelease>", update_previews)
        update_previews()
        
        def save():
            try:
                r_val = float(e_risk.get())
                s_val = float(e_sl.get())
                t_val = float(e_tp.get())
            except ValueError:
                messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ.")
                return

            config.PRESETS[p_name]["RISK_PERCENT"] = r_val
            config.PRESETS[p_name]["SL_PERCENT"] = s_val
            config.PRESETS[p_name]["TP_RR_RATIO"] = t_val
            self.save_settings()
            top.destroy()
            self.log_message(f"Updated Preset {p_name}: Risk {r_val}%")

        ctk.CTkButton(top, text="SAVE", command=save, fg_color=COL_GREEN).pack(pady=20, fill="x", padx=30)

    def open_tsl_popup(self):
        top = ctk.CTkToplevel(self); top.title("TSL Config V3.5"); top.geometry("420x580"); top.attributes("-topmost", True)
        
        acc = self.connector.get_account_info()
        current_balance = acc['balance'] if acc else 1000.0

        def sec(t):
            ctk.CTkLabel(top, text=t, font=("Roboto", 12, "bold"), text_color="#03A9F4").pack(fill="x", padx=15, pady=(10, 2), anchor="w")
            return ctk.CTkFrame(top, fg_color="transparent")

        f2 = sec("1. BREAK-EVEN (BE)")
        f2.pack(fill="x", padx=15)
        r1 = ctk.CTkFrame(f2, fg_color="transparent"); r1.pack(fill="x", pady=2)
        ctk.CTkLabel(r1, text="Mode:").pack(side="left")
        cbo_be = ctk.CTkOptionMenu(r1, values=["SOFT", "SMART"], width=100); cbo_be.set(config.TSL_CONFIG.get("BE_MODE", "SOFT")); cbo_be.pack(side="right")
        
        r2 = ctk.CTkFrame(f2, fg_color="transparent"); r2.pack(fill="x", pady=2)
        ctk.CTkLabel(r2, text="Trigger(R):").pack(side="left")
        e_be_rr = ctk.CTkEntry(r2, width=50); e_be_rr.insert(0, str(config.TSL_CONFIG.get("BE_OFFSET_RR", 0.8))); e_be_rr.pack(side="left", padx=(5,10))
        e_be_pts = ctk.CTkEntry(r2, width=50); e_be_pts.insert(0, str(config.TSL_CONFIG.get("BE_OFFSET_POINTS", 0))); e_be_pts.pack(side="right")
        ctk.CTkLabel(r2, text="Offset(Pts):").pack(side="right", padx=5)
        
        lbl_be_hint = ctk.CTkLabel(f2, text="~ Lãi ...R -> Kích hoạt dời SL về Entry", text_color="gray", font=("Roboto", 11)); lbl_be_hint.pack(pady=(0, 5))

        f3 = sec("2. PNL LOCK (Levels)")
        f3.pack(fill="both", expand=True, padx=15)
        lbl_pnl_hint = ctk.CTkLabel(f3, text=f"(~ Ví dụ vốn ${current_balance:.2f}: Lãi X% -> Khóa Y%)", text_color="gray", font=("Roboto", 11)); lbl_pnl_hint.pack(pady=(0, 2))

        f_pnl_scroll = ctk.CTkScrollableFrame(f3, height=100); f_pnl_scroll.pack(fill="both", expand=True)
        pnl_entries = []
        def add_pnl_row(v1=0.0, v2=0.0):
            r = ctk.CTkFrame(f_pnl_scroll, fg_color="transparent"); r.pack(fill="x", pady=2)
            e1 = ctk.CTkEntry(r, width=60); e1.insert(0, str(v1)); e1.pack(side="left")
            ctk.CTkLabel(r, text="% Win -> Lock %", text_color="gray", font=("Roboto",11)).pack(side="left", padx=5)
            e2 = ctk.CTkEntry(r, width=60); e2.insert(0, str(v2)); e2.pack(side="right")
            pnl_entries.append((r, e1, e2))
        for lvl in config.TSL_CONFIG.get("PNL_LEVELS", []): add_pnl_row(lvl[0], lvl[1])
        
        f_pbtns = ctk.CTkFrame(f3, fg_color="transparent"); f_pbtns.pack(fill="x", pady=2)
        ctk.CTkButton(f_pbtns, text="+", width=40, command=lambda: add_pnl_row(0.0, 0.0)).pack(side="left", padx=5)
        ctk.CTkButton(f_pbtns, text="-", width=40, command=lambda: pnl_entries.pop()[0].destroy() if pnl_entries else None).pack(side="right", padx=5)

        f4 = sec("3. STEP R (Nuôi Lệnh)")
        f4.pack(fill="x", padx=15)
        r_step = ctk.CTkFrame(f4, fg_color="transparent"); r_step.pack(fill="x", pady=2)
        ctk.CTkLabel(r_step, text="Size(R):").pack(side="left")
        e_step_size = ctk.CTkEntry(r_step, width=50); e_step_size.insert(0, str(config.TSL_CONFIG.get("STEP_R_SIZE", 1.0))); e_step_size.pack(side="left", padx=(5,10))
        e_step_ratio = ctk.CTkEntry(r_step, width=50); e_step_ratio.insert(0, str(config.TSL_CONFIG.get("STEP_R_RATIO", 0.8))); e_step_ratio.pack(side="right")
        ctk.CTkLabel(r_step, text="Lock(0-1):").pack(side="right", padx=5)
        
        lbl_step_hint = ctk.CTkLabel(f4, text="~ Mỗi ...R -> Khóa ...", text_color="gray", font=("Roboto", 11)); lbl_step_hint.pack(pady=(0, 5))

        def update_tsl_previews(*args):
            if not e_be_rr.winfo_exists(): return
            try:
                be_rr, s_sz, s_rt = float(e_be_rr.get() or 0), float(e_step_size.get() or 0), float(e_step_ratio.get() or 0)
                lbl_be_hint.configure(text=f"(~ Lãi {be_rr}R -> Kích hoạt dời SL về Entry)")
                lbl_step_hint.configure(text=f"(~ Mỗi khi giá chạy {s_sz}R -> Khóa lại {s_rt * 100}% của bước đó)")
            except ValueError: pass

        e_be_rr.bind("<KeyRelease>", update_tsl_previews); e_step_size.bind("<KeyRelease>", update_tsl_previews); e_step_ratio.bind("<KeyRelease>", update_tsl_previews)
        update_tsl_previews()

        def save_cfg():
            try:
                config.TSL_CONFIG["BE_MODE"] = cbo_be.get()
                config.TSL_CONFIG["BE_OFFSET_RR"] = float(e_be_rr.get() or 0.8) 
                config.TSL_CONFIG["BE_OFFSET_POINTS"] = float(e_be_pts.get() or 0)
                config.TSL_CONFIG["PNL_LEVELS"] = sorted([[float(e1.get()), float(e2.get())] for r,e1,e2 in pnl_entries if e1.get()], key=lambda x:x[0])
                config.TSL_CONFIG["STEP_R_SIZE"] = float(e_step_size.get() or 1.0)
                config.TSL_CONFIG["STEP_R_RATIO"] = float(e_step_ratio.get() or 0.8)
                self.save_settings(); top.destroy(); self.log_message("Đã cập nhật cấu hình TSL.")
            except Exception:
                messagebox.showerror("Lỗi", "Cấu hình không hợp lệ.")

        ctk.CTkButton(top, text="SAVE CONFIG", height=35, font=("Roboto", 13, "bold"), command=save_cfg, fg_color=COL_GREEN).pack(pady=15, fill="x", padx=40)

    def reset_daily_stats(self):
        if messagebox.askyesno("Confirm", "Reset Daily Stats?"):
            self.trade_mgr.state.update({"pnl_today": 0.0, "trades_today_count": 0, "daily_loss_count": 0, "daily_history": []})
            save_state(self.trade_mgr.state)

    def handle_close_request(self, ticket):
        if self.var_confirm_close.get() and not messagebox.askyesno("Confirm", f"Close #{ticket}?"): return
        threading.Thread(target=lambda: self.connector.close_position(next((p for p in self.connector.get_all_open_positions() if p.ticket==ticket), None))).start()

    def bg_update_loop(self):
        while self.running:
            try:
                sym = self.cbo_symbol.get()
                new_map = self.trade_mgr.update_running_trades(self.cbo_account_type.get())
                self.tsl_states_map.update(new_map)
                acc = self.connector.get_account_info()
                tick = mt5.symbol_info_tick(sym)
                pos = [p for p in self.connector.get_all_open_positions() if p.magic == config.MAGIC_NUMBER]
                self.after(0, self.update_ui, acc, self.trade_mgr.state, 
                                self.checklist_mgr.run_pre_trade_checks(acc, self.trade_mgr.state, sym, self.var_strict_mode.get()), 
                                tick, self.cbo_preset.get(), sym, pos)
            except: pass
            time.sleep(config.LOOP_SLEEP_SECONDS)

    def update_ui(self, acc, state, check_res, tick, preset, sym, positions):
        d = self.seg_direction.get()
        self.var_direction.set(d)
        cur_tactic_str = self.get_current_tactic_string()

        balance = acc['balance'] if acc else 1.0
        if balance == 0: balance = 1.0

        if acc: 
            self.lbl_equity.configure(text=f"${acc['equity']:,.2f}")
            self.lbl_acc_info.configure(text=f"ID: {acc['login']} | Server: {acc['server']}")
        pnl = state['pnl_today']
        self.lbl_stats.configure(text=f"Today: ${pnl:.2f}", text_color=COL_GREEN if pnl >= 0 else COL_RED)
        
        cur_price, c_size, point = 0.0, 1.0, 0.00001
        if tick: 
            cur_price = tick.ask if d == "BUY" else tick.bid
            self.lbl_dashboard_price.configure(text=f"{cur_price:.2f}", text_color=COL_GREEN if cur_price >= self.last_price_val else COL_RED)
            self.last_price_val = cur_price
            s_info = mt5.symbol_info(sym)
            if s_info: c_size, point = s_info.trade_contract_size, s_info.point

        for item in check_res["checks"]:
            name, stt, msg = item["name"], item["status"], item["msg"]
            if name in self.check_labels:
                self.check_labels[name].configure(text=f"{'✔' if stt=='OK' else '✖'} {name}: {msg}", 
                                                    text_color=COL_GREEN if stt=="OK" else (COL_WARN if stt=="WARN" else COL_RED))

        if tick and acc:
            params = config.PRESETS.get(preset, config.PRESETS["SCALPING"])
            current_risk_pct = params.get("RISK_PERCENT", config.RISK_PER_TRADE_PERCENT)
            sl_pct_display = params.get("SL_PERCENT", 0.0)
            tp_r_display = params.get("TP_RR_RATIO", 0.0)
            
            self.lbl_head_sl.configure(text=f"STOPLOSS ({sl_pct_display}%)")
            self.lbl_head_tp.configure(text=f"TARGET ({tp_r_display}R)")
            
            try: mlot = float(self.var_manual_lot.get() or 0)
            except: mlot = 0.0
            
            f_lot = mlot if mlot > 0 else 0
            if f_lot == 0:
                risk_usd = acc['equity'] * (current_risk_pct/100)
                sl_dist = cur_price * (params["SL_PERCENT"]/100)
                if sl_dist > 0: 
                    raw_calc = round((risk_usd / (sl_dist * c_size)) / config.LOT_STEP) * config.LOT_STEP
                    f_lot = raw_calc

            if f_lot < config.MIN_LOT_SIZE:
                self.lbl_prev_lot.configure(text=f"LOT: INVALID (Min {config.MIN_LOT_SIZE})", text_color=COL_RED)
                f_lot = config.MIN_LOT_SIZE 
            else:
                f_lot = min(f_lot, config.MAX_LOT_SIZE)
                self.lbl_prev_lot.configure(text=f"{'(MANUAL)' if mlot>0 else '(AUTO)'} LOT: {f_lot:.2f}", text_color="white" if mlot==0 else "#FFD700")
            
            comm_rate = self.get_fee_config(sym)
            comm_total = comm_rate * f_lot
            spread_cost = (tick.ask - tick.bid) * f_lot * c_size
            
            acc_type = self.cbo_account_type.get()
            if acc_type in ["PRO", "STANDARD"]: self.lbl_fee_info.configure(text=f"Cost (Spr): -${spread_cost:.2f}")
            else: self.lbl_fee_info.configure(text=f"Cost (Com): -${comm_total:.2f}")

            try: msl, mtp = float(self.var_manual_sl.get() or 0), float(self.var_manual_tp.get() or 0)
            except: msl, mtp = 0, 0
            
            auto_sl_dist = cur_price * (params["SL_PERCENT"]/100)
            p_sl = msl if msl > 0 else (cur_price - auto_sl_dist if d=="BUY" else cur_price + auto_sl_dist)
            p_tp = mtp if mtp > 0 else (cur_price + abs(cur_price - p_sl) * params["TP_RR_RATIO"] if d=="BUY" else cur_price - abs(cur_price - p_sl) * params["TP_RR_RATIO"])
            
            is_valid_sl = True
            if d == "BUY" and p_sl >= cur_price: is_valid_sl = False
            if d == "SELL" and p_sl <= cur_price: is_valid_sl = False
            
            if is_valid_sl:
                self.lbl_prev_sl.configure(text=f"{p_sl:.2f}", text_color=COL_RED)
                loss_dist = abs(cur_price - p_sl) 
                loss_val = loss_dist * f_lot * c_size
                loss_pct = (loss_val / balance) * 100
                self.lbl_prev_risk.configure(text=f"-${loss_val:.2f} ({loss_pct:.2f}%)", text_color=COL_RED)
            else:
                self.lbl_prev_sl.configure(text="INVALID", text_color=COL_WARN)
                self.lbl_prev_risk.configure(text="$ ---", text_color=COL_WARN)

            is_valid_tp = True
            if d == "BUY" and p_tp <= cur_price: is_valid_tp = False
            if d == "SELL" and p_tp >= cur_price: is_valid_tp = False
            
            if is_valid_tp:
                self.lbl_prev_tp.configure(text=f"{p_tp:.2f}", text_color=COL_GREEN)
                prof_dist = abs(p_tp - cur_price)
                prof_val = prof_dist * f_lot * c_size
                prof_pct = (prof_val / balance) * 100
                self.lbl_prev_rew.configure(text=f"+${prof_val:.2f} ({prof_pct:.2f}%)", text_color=COL_GREEN)
            else:
                self.lbl_prev_tp.configure(text="INVALID", text_color=COL_WARN)
                self.lbl_prev_rew.configure(text="$ ---", text_color=COL_WARN)

            if cur_tactic_str == "OFF":
                self.lbl_tsl_preview.configure(text="TSL: OFF")
            else:
                milestones = []
                one_r_dist = abs(cur_price - p_sl)
                is_buy = (d == "BUY")
                t_cfg = config.TSL_CONFIG
                
                if "BE" in cur_tactic_str and one_r_dist > 0:
                    trig_r = t_cfg.get("BE_OFFSET_RR", 0.8)
                    trig_p = cur_price + (one_r_dist * trig_r) if is_buy else cur_price - (one_r_dist * trig_r)
                    fee_d = (comm_total + spread_cost) / (f_lot * c_size) if (f_lot * c_size) > 0 else 0
                    mode = t_cfg.get("BE_MODE", "SOFT")
                    base = cur_price - fee_d if (is_buy and mode=="SOFT") else (cur_price + fee_d if (is_buy and mode=="SMART") else cur_price)
                    if not is_buy: base = cur_price + fee_d if mode=="SOFT" else (cur_price - fee_d if mode=="SMART" else cur_price)
                    be_sl = base + (t_cfg.get("BE_OFFSET_POINTS", 0) * point) if is_buy else base - (t_cfg.get("BE_OFFSET_POINTS", 0) * point)
                    milestones.append((abs(cur_price - trig_p), f"BE | {trig_p:.2f} -> {be_sl:.2f}"))

                if "STEP_R" in cur_tactic_str and one_r_dist > 0:
                    sz, rt = t_cfg.get("STEP_R_SIZE", 1.0), t_cfg.get("STEP_R_RATIO", 0.8)
                    n_trig = cur_price + (sz * one_r_dist) if is_buy else cur_price - (sz * one_r_dist)
                    n_sl = cur_price + (sz * one_r_dist * rt) if is_buy else cur_price - (sz * one_r_dist * rt)
                    milestones.append((abs(cur_price - n_trig), f"Step 1 | {n_trig:.2f} -> {n_sl:.2f}"))

                if "PNL" in cur_tactic_str and t_cfg.get("PNL_LEVELS") and acc:
                    lvl = t_cfg["PNL_LEVELS"][0]
                    req_profit_usd = acc['balance'] * (lvl[0]/100.0)
                    trig_p = cur_price + (req_profit_usd / (f_lot * c_size)) if is_buy else cur_price - (req_profit_usd / (f_lot * c_size))
                    milestones.append((abs(cur_price - trig_p), f"PnL {lvl[0]}% | {trig_p:.2f}"))

                if milestones:
                    closest = sorted(milestones, key=lambda x: x[0])[0][1]
                    self.lbl_tsl_preview.configure(text=f"TSL: {closest}")
                else:
                    self.lbl_tsl_preview.configure(text="TSL: Monitoring...")

        existing_items = self.tree.get_children()
        current_tickets_on_chart = []
        
        for p in positions:
            ticket_str = str(p.ticket)
            current_tickets_on_chart.append(ticket_str)

            p_tick = mt5.symbol_info_tick(p.symbol)
            p_sym_info = mt5.symbol_info(p.symbol)
            p_c_size = p_sym_info.trade_contract_size if p_sym_info else 1.0
            swap_val = getattr(p, 'swap', 0.0)
            
            current_spread = (p_tick.ask - p_tick.bid) if p_tick else 0.0
            spread_cost_usd = current_spread * p.volume * p_c_size
            comm_rate = self.get_fee_config(p.symbol)
            comm_total_usd = comm_rate * p.volume
            
            acc_type = self.cbo_account_type.get()
            if acc_type in ["PRO", "STANDARD"]: fee_str = f"Spr: -${spread_cost_usd:.2f} | Sw: ${swap_val:.2f}"
            else: fee_str = f"Com: -${comm_total_usd:.2f} | Sw: ${swap_val:.2f}"
            
            time_str = datetime.fromtimestamp(p.time).strftime("%d/%m %H:%M")
            is_buy = (p.type == mt5.ORDER_TYPE_BUY)
            icon = "🟢" if is_buy else "🔴"
            side_txt = "BUY" if is_buy else "SELL"
            
            order_str = f"{icon} {side_txt} {p.volume:.2f} {p.symbol} @ {p.price_open:.2f}"
            sl_txt = f"{p.sl:.2f}" if p.sl > 0 else "---"
            tp_txt = f"{p.tp:.2f}" if p.tp > 0 else "---"
            targets_str = f"{sl_txt}  |  {tp_txt}"

            risk_usd = abs(p.price_open - p.sl) * p.volume * p_c_size if p.sl > 0 else 0
            rew_usd = abs(p.price_open - p.tp) * p.volume * p_c_size if p.tp > 0 else 0
            risk_pct = (risk_usd / balance * 100) if balance > 0 else 0
            rew_pct = (rew_usd / balance * 100) if balance > 0 else 0
            
            is_sl_in_profit = False
            if is_buy and p.sl > p.price_open: is_sl_in_profit = True
            if not is_buy and p.sl > 0 and p.sl < p.price_open: is_sl_in_profit = True
            
            if p.sl == 0: risk_str = "No SL"
            elif is_sl_in_profit: risk_str = f"+${risk_usd:.1f} ({risk_pct:.1f}%)" 
            else: risk_str = f"-${risk_usd:.1f} ({risk_pct:.1f}%)"

            rew_str = f"+${rew_usd:.1f} ({rew_pct:.1f}%)" if p.tp > 0 else "No TP"
            rr_str = f"{risk_str}  |  {rew_str}"
            stt_txt = self.tsl_states_map.get(p.ticket, "Running")

            values_data = (f"#{ticket_str}", time_str, order_str, targets_str, fee_str, rr_str, f"${p.profit:.2f}", stt_txt, "❌")

            if ticket_str in existing_items: self.tree.item(ticket_str, values=values_data)
            else: self.tree.insert("", "end", iid=ticket_str, values=values_data)

        for item in existing_items:
            if item not in current_tickets_on_chart:
                self.tree.delete(item)

    def on_click_trade(self):
        d, s, p, t = self.seg_direction.get(), self.cbo_symbol.get(), self.cbo_preset.get(), self.get_current_tactic_string()
        
        try: ml, mt, ms = float(self.var_manual_lot.get() or 0), float(self.var_manual_tp.get() or 0), float(self.var_manual_sl.get() or 0)
        except: ml = mt = ms = 0.0
        
        if ms == 0.0 and self.var_assist_math_sl.get():
            sl_val = self.latest_market_context.get("swing_low") if d == "BUY" else self.latest_market_context.get("swing_high")
            atr_val = self.latest_market_context.get("atr")
            if sl_val and atr_val:
                sl_mult = getattr(config, "sl_atr_multiplier", 0.2)
                ms = sl_val - (atr_val * sl_mult) if d == "BUY" else sl_val + (atr_val * sl_mult)
                self.log_message(f"🧠 Auto-Math SL applied: {ms:.2f}", error=False)

        self.log_message(f"Exec {d} {s} | TSL: [{t}]...")
        
        def run_trade_thread():
            result = self.trade_mgr.execute_manual_trade(d, p, s, self.var_strict_mode.get(), ml, mt, ms, self.var_bypass_checklist.get(), t)
            if "SUCCESS" not in result: self.log_message(f"❌ EXEC FAILED: {result}", error=True)

        threading.Thread(target=run_trade_thread).start()

    def show_history_popup(self):
        top = ctk.CTkToplevel(self); top.title("History"); top.geometry("700x450")
        tr = ttk.Treeview(top, columns=("Time", "Sym", "Type", "PnL", "Reason"), show="headings"); tr.pack(fill="both", expand=True)
        for c in tr["columns"]: tr.heading(c, text=c)
        for h in self.trade_mgr.state.get("daily_history", []): 
            tr.insert("", "end", values=(h['time'], h['symbol'], h['type'], f"${h['profit']:.2f}", h.get('reason','')))

if __name__ == "__main__":
    try:
        app = BotUI()
        app.mainloop()
    except KeyboardInterrupt:
        print("\n[INFO] Đang đóng ứng dụng từ Terminal...")
        sys.exit(0)