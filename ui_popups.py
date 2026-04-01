# -*- coding: utf-8 -*-
# FILE: ui_popups.py
# V6.3: DIALOGS & SETTINGS - ADDED INDEPENDENT BOT TSL (KAISER EDITION)

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import config

# --- BẢNG MÀU & FONT CHUẨN ---
FONT_BOLD = ("Roboto", 13, "bold")
COL_GREEN = "#00C853"
COL_RED = "#D50000"
COL_BLUE_ACCENT = "#1565C0"
COL_GRAY_BTN = "#424242"
COL_WARN = "#FFAB00"
COL_BOT_TAG = "#E040FB"

# ==============================================================================
# 1. POPUP CẤU HÌNH BỘ NÃO BOT (GRID LAYOUT & SAFETY GUARD)
# ==============================================================================
def open_bot_setting_popup(app):
    top = ctk.CTkToplevel(app)
    top.title("Cấu hình Bộ não & Chiến thuật Bot")
    top.geometry("850x850") 
    top.attributes("-topmost", True)
    
    tabview = ctk.CTkTabview(top)
    tabview.pack(fill="both", expand=True, padx=15, pady=15)
    
    tabview.add("CORE ENGINE")
    tabview.add("INDICATORS")
    tabview.add("MANUAL ASSIST")
    
    # ----------------------------------------------------------------------
    # TAB: CORE ENGINE
    # ----------------------------------------------------------------------
    tab_core_parent = tabview.tab("CORE ENGINE")
    tab_core = ctk.CTkScrollableFrame(tab_core_parent, fg_color="transparent")
    tab_core.pack(fill="both", expand=True)
    
    f_auto = ctk.CTkFrame(tab_core, fg_color="transparent")
    f_auto.pack(fill="x", pady=10)
    ctk.CTkLabel(f_auto, text="Tự động bóp cò khi Brain có tín hiệu:", text_color="gray").pack()
    sw_auto = ctk.CTkSwitch(
        f_auto, 
        text="AUTO-TRADING DAEMON", 
        variable=app.var_auto_trade, 
        font=("Roboto", 14, "bold"), 
        progress_color=COL_GREEN, 
        fg_color=COL_RED, 
        command=app.on_auto_trade_toggle
    )
    sw_auto.pack(pady=5)

    ctk.CTkFrame(tab_core, height=2, fg_color="#333").pack(fill="x", padx=30, pady=5)
    
    # Risk Management
    ctk.CTkLabel(tab_core, text="BOT RISK MANAGEMENT (TP = 0.0, Thuần TSL)", font=FONT_BOLD, text_color=COL_BOT_TAG).pack(pady=5)
    f_bot_risk = ctk.CTkFrame(tab_core, fg_color="transparent")
    f_bot_risk.pack(fill="x", padx=30)
    
    ctk.CTkLabel(f_bot_risk, text="Rủi ro / Lệnh (% Cắt lỗ tài khoản):").pack(side="left")
    e_bot_risk = ctk.CTkEntry(f_bot_risk, width=80, justify="center")
    e_bot_risk.insert(0, str(getattr(config, "BOT_RISK_PERCENT", 0.3)))
    e_bot_risk.pack(side="right")

    ctk.CTkFrame(tab_core, height=2, fg_color="#333").pack(fill="x", padx=30, pady=10)

    # --- BOT TSL TACTIC (ĐỘC LẬP) ---
    ctk.CTkLabel(tab_core, text="BOT TSL TACTIC (ĐỘC LẬP VỚI MANUAL)", font=FONT_BOLD, text_color="#29B6F6").pack(pady=(5, 5))
    f_bot_tsl = ctk.CTkFrame(tab_core, fg_color="#2b2b2b", corner_radius=8)
    f_bot_tsl.pack(fill="x", padx=15, pady=5)

    current_bot_tsl = getattr(config, "BOT_DEFAULT_TSL", "BE+STEP_R+SWING")
    app.var_bot_tsl_be = tk.BooleanVar(value="BE" in current_bot_tsl)
    app.var_bot_tsl_pnl = tk.BooleanVar(value="PNL" in current_bot_tsl)
    app.var_bot_tsl_step = tk.BooleanVar(value="STEP_R" in current_bot_tsl)
    app.var_bot_tsl_swing = tk.BooleanVar(value="SWING" in current_bot_tsl)

    ctk.CTkCheckBox(f_bot_tsl, text="BE", variable=app.var_bot_tsl_be).pack(side="left", expand=True, pady=10)
    ctk.CTkCheckBox(f_bot_tsl, text="PNL", variable=app.var_bot_tsl_pnl).pack(side="left", expand=True, pady=10)
    ctk.CTkCheckBox(f_bot_tsl, text="STEP_R", variable=app.var_bot_tsl_step).pack(side="left", expand=True, pady=10)
    ctk.CTkCheckBox(f_bot_tsl, text="SWING", variable=app.var_bot_tsl_swing).pack(side="left", expand=True, pady=10)

    ctk.CTkFrame(tab_core, height=2, fg_color="#333").pack(fill="x", padx=30, pady=10)

    # --- HÀNG RÀO BẢO VỆ & ENGINE (SAFETY GUARD) ---
    ctk.CTkLabel(tab_core, text="HÀNG RÀO BẢO VỆ & DỮ LIỆU (SAFETY GUARD)", font=FONT_BOLD, text_color="#FFB300").pack(pady=(5, 5))
    f_safety = ctk.CTkFrame(tab_core, fg_color="#2b2b2b", corner_radius=8)
    f_safety.pack(fill="x", padx=15, pady=5)
    f_safety.columnconfigure((0, 2), weight=1)

    # Row 0
    ctk.CTkLabel(f_safety, text="Max Loss/Ngày (%):").grid(row=0, column=0, sticky="w", padx=10, pady=8)
    e_max_loss = ctk.CTkEntry(f_safety, width=70, justify="center")
    e_max_loss.insert(0, str(getattr(config, "MAX_DAILY_LOSS_PERCENT", 2.5)))
    e_max_loss.grid(row=0, column=1, sticky="w", padx=10, pady=8)

    ctk.CTkLabel(f_safety, text="Max Lệnh Chạy Cùng Lúc:").grid(row=0, column=2, sticky="w", padx=10, pady=8)
    e_max_open = ctk.CTkEntry(f_safety, width=70, justify="center")
    e_max_open.insert(0, str(getattr(config, "MAX_OPEN_POSITIONS", 3)))
    e_max_open.grid(row=0, column=3, sticky="w", padx=10, pady=8)

    # Row 1
    ctk.CTkLabel(f_safety, text="Tổng Lệnh/Ngày:").grid(row=1, column=0, sticky="w", padx=10, pady=8)
    e_max_trades = ctk.CTkEntry(f_safety, width=70, justify="center")
    e_max_trades.insert(0, str(getattr(config, "MAX_TRADES_PER_DAY", 30)))
    e_max_trades.grid(row=1, column=1, sticky="w", padx=10, pady=8)

    ctk.CTkLabel(f_safety, text="Max Lệnh Thua (Streak):").grid(row=1, column=2, sticky="w", padx=10, pady=8)
    e_max_streak = ctk.CTkEntry(f_safety, width=70, justify="center")
    e_max_streak.insert(0, str(getattr(config, "MAX_LOSING_STREAK", 3)))
    e_max_streak.grid(row=1, column=3, sticky="w", padx=10, pady=8)

    # Row 2
    ctk.CTkLabel(f_safety, text="Chế độ tính Loss:").grid(row=2, column=0, sticky="w", padx=10, pady=8)
    cbo_loss_mode = ctk.CTkOptionMenu(f_safety, values=["TOTAL", "STREAK"], width=90)
    cbo_loss_mode.set(str(getattr(config, "LOSS_COUNT_MODE", "TOTAL")))
    cbo_loss_mode.grid(row=2, column=1, sticky="w", padx=10, pady=8)

    ctk.CTkLabel(f_safety, text="Cooldown (Phút):").grid(row=2, column=2, sticky="w", padx=10, pady=8)
    e_cooldown = ctk.CTkEntry(f_safety, width=70, justify="center")
    e_cooldown.insert(0, str(getattr(config, "COOLDOWN_MINUTES", 1)))
    e_cooldown.grid(row=2, column=3, sticky="w", padx=10, pady=8)

    # Row 3
    ctk.CTkLabel(f_safety, text="Số nến H1 (Quét):").grid(row=3, column=0, sticky="w", padx=10, pady=8)
    e_num_h1 = ctk.CTkEntry(f_safety, width=70, justify="center")
    e_num_h1.insert(0, str(getattr(config, "NUM_H1_BARS", 70)))
    e_num_h1.grid(row=3, column=1, sticky="w", padx=10, pady=8)

    ctk.CTkLabel(f_safety, text="Số nến M15 (Quét):").grid(row=3, column=2, sticky="w", padx=10, pady=8)
    e_num_m15 = ctk.CTkEntry(f_safety, width=70, justify="center")
    e_num_m15.insert(0, str(getattr(config, "NUM_M15_BARS", 70)))
    e_num_m15.grid(row=3, column=3, sticky="w", padx=10, pady=8)

    ctk.CTkFrame(tab_core, height=2, fg_color="#333").pack(fill="x", padx=30, pady=10)

    # --- WATCHLIST COIN ---
    ctk.CTkLabel(tab_core, text="WATCHLIST - BOT CHỈ QUÉT CÁC COIN SAU:", font=FONT_BOLD, text_color="#2196F3").pack(pady=(5, 5))
    f_coins = ctk.CTkFrame(tab_core, fg_color="transparent")
    f_coins.pack(fill="x", padx=30, pady=(0, 10))
    
    app.bot_coin_vars = {}
    allowed_list = getattr(config, "BOT_ACTIVE_SYMBOLS", config.COIN_LIST)
    
    f_coins.columnconfigure((0, 1), weight=1)
    for i, coin in enumerate(config.COIN_LIST):
        var = tk.BooleanVar(value=(coin in allowed_list))
        app.bot_coin_vars[coin] = var
        chk = ctk.CTkCheckBox(f_coins, text=coin, variable=var, font=("Consolas", 13))
        chk.grid(row=i//2, column=i%2, sticky="w", pady=5, padx=10)

    # ----------------------------------------------------------------------
    # TAB: INDICATORS
    # ----------------------------------------------------------------------
    tab_ind = tabview.tab("INDICATORS")
    inner_tabview = ctk.CTkTabview(tab_ind)
    inner_tabview.pack(fill="both", expand=True, padx=5, pady=5)
    
    def add_setting_row(parent, row_idx, label, w_type, attr, desc, options=None):
        lbl = ctk.CTkLabel(parent, text=label, font=FONT_BOLD, anchor="w")
        lbl.grid(row=row_idx, column=0, sticky="ew", padx=(10, 20), pady=8)
        
        widget_obj = None; var_obj = None
        if w_type == "switch":
            var_obj = tk.BooleanVar(value=getattr(config, attr, True))
            widget_obj = ctk.CTkSwitch(parent, text="", variable=var_obj, progress_color=COL_BLUE_ACCENT)
        elif w_type == "entry":
            widget_obj = ctk.CTkEntry(parent, width=100, justify="center")
            widget_obj.insert(0, str(getattr(config, attr, 0)))
        elif w_type == "option":
            widget_obj = ctk.CTkOptionMenu(parent, values=options, width=120)
            widget_obj.set(str(getattr(config, attr, "")))
            
        widget_obj.grid(row=row_idx, column=1, sticky="w", padx=10, pady=8)
        
        desc_lbl = ctk.CTkLabel(parent, text=desc, font=("Roboto", 11, "italic"), text_color="gray", anchor="w")
        desc_lbl.grid(row=row_idx, column=2, sticky="ew", padx=(20, 10), pady=8)
        
        ctk.CTkFrame(parent, height=1, fg_color="#2b2b2b").grid(row=row_idx, column=0, columnspan=3, sticky="sew", padx=10)
        return var_obj if w_type == "switch" else widget_obj

    def setup_grid_columns(parent):
        parent.grid_columnconfigure(0, weight=1, minsize=200) 
        parent.grid_columnconfigure(1, weight=0, minsize=140) 
        parent.grid_columnconfigure(2, weight=2, minsize=300) 

    tab_trend = inner_tabview.add("H1 Trend")
    scroll_trend = ctk.CTkScrollableFrame(tab_trend, fg_color="transparent")
    scroll_trend.pack(fill="both", expand=True)
    setup_grid_columns(scroll_trend)

    v_ema_trend = add_setting_row(scroll_trend, 0, "Bật Lọc EMA", "switch", "USE_EMA_TREND_FILTER", "Lọc nhiễu bằng đường EMA khung H1.")
    e_ema_trend_p = add_setting_row(scroll_trend, 1, "TREND_EMA_PERIOD", "entry", "TREND_EMA_PERIOD", "Chu kỳ đường EMA tham chiếu.")
    v_st_trend = add_setting_row(scroll_trend, 2, "Bật Lọc Supertrend", "switch", "USE_SUPERTREND_FILTER", "Sử dụng dải Supertrend làm bộ lọc.")
    e_st_atr_p = add_setting_row(scroll_trend, 3, "ST_ATR_PERIOD", "entry", "ST_ATR_PERIOD", "Chu kỳ đo độ giật ATR cấu thành Supertrend.")
    e_st_mult = add_setting_row(scroll_trend, 4, "ST_MULTIPLIER", "entry", "ST_MULTIPLIER", "Khoảng rộng của dải Supertrend.")
    v_adx = add_setting_row(scroll_trend, 5, "Bật Lọc ADX", "switch", "USE_ADX_FILTER", "Kiểm tra độ mạnh của trend.")
    e_adx_p = add_setting_row(scroll_trend, 6, "ADX_PERIOD", "entry", "ADX_PERIOD", "Chu kỳ chuẩn hóa sức mạnh trend.")
    e_di_p = add_setting_row(scroll_trend, 7, "DI_PERIOD", "entry", "DI_PERIOD", "Chu kỳ đường chỉ báo hướng +DI/-DI.")
    e_adx_min = add_setting_row(scroll_trend, 8, "ADX_MIN_LEVEL", "entry", "ADX_MIN_LEVEL", "Ngưỡng sức mạnh tối thiểu.")
    v_adx_grey = add_setting_row(scroll_trend, 9, "Bật Vùng Xám ADX", "switch", "USE_ADX_GREY_ZONE", "Áp dụng luật riêng (Pullback/Breakout).")

    tab_entry = inner_tabview.add("M15 Entry")
    scroll_entry = ctk.CTkScrollableFrame(tab_entry, fg_color="transparent")
    scroll_entry.pack(fill="both", expand=True)
    setup_grid_columns(scroll_entry)

    c_entry_mode = add_setting_row(scroll_entry, 0, "ENTRY_LOGIC_MODE", "option", "ENTRY_LOGIC_MODE", "Cách bóp cò M15.", ["DYNAMIC", "BREAKOUT", "PULLBACK"])
    e_ema_entry_p = add_setting_row(scroll_entry, 1, "ENTRY_EMA_PERIOD", "entry", "ENTRY_EMA_PERIOD", "Đường EMA đóng vai trò cản động tại M15.")
    v_candle = add_setting_row(scroll_entry, 2, "Bật Lọc Thân nến", "switch", "USE_CANDLE_FILTER", "Nến breakout phải có xung lực lớn.")
    e_body_pct = add_setting_row(scroll_entry, 3, "min_body_percent", "entry", "min_body_percent", "Tỷ lệ thân nến tối thiểu.")
    v_vol = add_setting_row(scroll_entry, 4, "Bật Lọc Volume", "switch", "USE_VOLUME_FILTER", "Kiểm tra volume đột biến.")
    e_vol_period = add_setting_row(scroll_entry, 5, "volume_ma_period", "entry", "volume_ma_period", "Chu kỳ trung bình Volume.")

    tab_sl_atr = inner_tabview.add("Math SL/ATR")
    scroll_sl_atr = ctk.CTkScrollableFrame(tab_sl_atr, fg_color="transparent")
    scroll_sl_atr.pack(fill="both", expand=True)
    setup_grid_columns(scroll_sl_atr)

    e_swing_p = add_setting_row(scroll_sl_atr, 0, "swing_period", "entry", "swing_period", "Số nến quá khứ để quét đỉnh/đáy.")
    e_atr_p = add_setting_row(scroll_sl_atr, 1, "atr_period", "entry", "atr_period", "Chu kỳ đo độ biến động ATR.")
    e_sl_atr_m = add_setting_row(scroll_sl_atr, 2, "sl_atr_multiplier", "entry", "sl_atr_multiplier", "Khoảng đệm Math SL ban đầu.")
    c_tsl_logic = add_setting_row(scroll_sl_atr, 3, "TSL_LOGIC_MODE", "option", "TSL_LOGIC_MODE", "Chế độ bám đuôi TSL Swing.", ["STATIC", "DYNAMIC", "AGGRESSIVE"])
    e_trail_buf = add_setting_row(scroll_sl_atr, 4, "trail_atr_buffer", "entry", "trail_atr_buffer", "Khoảng giãn đệm khi dời TSL Swing.")

    def save_all_bot_settings():
        try:
            config.BOT_RISK_PERCENT = float(e_bot_risk.get())
            
            # Lưu TSL Độc Lập cho Bot
            active_bot_tsl = []
            if app.var_bot_tsl_be.get(): active_bot_tsl.append("BE")
            if app.var_bot_tsl_pnl.get(): active_bot_tsl.append("PNL")
            if app.var_bot_tsl_step.get(): active_bot_tsl.append("STEP_R")
            if app.var_bot_tsl_swing.get(): active_bot_tsl.append("SWING")
            config.BOT_DEFAULT_TSL = "+".join(active_bot_tsl) if active_bot_tsl else "OFF"
            
            config.MAX_DAILY_LOSS_PERCENT = float(e_max_loss.get())
            config.MAX_OPEN_POSITIONS = int(e_max_open.get())
            config.MAX_TRADES_PER_DAY = int(e_max_trades.get())
            config.MAX_LOSING_STREAK = int(e_max_streak.get())
            config.LOSS_COUNT_MODE = cbo_loss_mode.get()
            config.COOLDOWN_MINUTES = int(e_cooldown.get())
            config.NUM_H1_BARS = int(e_num_h1.get())
            config.NUM_M15_BARS = int(e_num_m15.get())
            
            selected_coins = [coin for coin, var in app.bot_coin_vars.items() if var.get()]
            if not selected_coins:
                messagebox.showwarning("Cảnh báo", "Bạn chưa chọn đồng coin nào cho Bot. Bot sẽ ngủ đông!")
            config.BOT_ACTIVE_SYMBOLS = selected_coins
            
            config.USE_EMA_TREND_FILTER = v_ema_trend.get()
            config.TREND_EMA_PERIOD = int(e_ema_trend_p.get())
            config.USE_SUPERTREND_FILTER = v_st_trend.get()
            config.ST_ATR_PERIOD = int(e_st_atr_p.get())
            config.ST_MULTIPLIER = float(e_st_mult.get())
            config.USE_ADX_FILTER = v_adx.get()
            config.ADX_PERIOD = int(e_adx_p.get())
            config.DI_PERIOD = int(e_di_p.get())
            config.ADX_MIN_LEVEL = float(e_adx_min.get())
            config.USE_ADX_GREY_ZONE = v_adx_grey.get()
            
            config.ENTRY_LOGIC_MODE = c_entry_mode.get()
            config.ENTRY_EMA_PERIOD = int(e_ema_entry_p.get())
            config.USE_CANDLE_FILTER = v_candle.get()
            config.min_body_percent = float(e_body_pct.get())
            config.USE_VOLUME_FILTER = v_vol.get()
            config.volume_ma_period = int(e_vol_period.get())
            
            config.swing_period = int(e_swing_p.get())
            config.atr_period = int(e_atr_p.get())
            config.sl_atr_multiplier = float(e_sl_atr_m.get())
            config.TSL_LOGIC_MODE = c_tsl_logic.get()
            config.trail_atr_buffer = float(e_trail_buf.get())
            
            app._save_brain_live_config()
            app.log_message(f"✅ Đã lưu cấu hình BOT. TSL Bot: {config.BOT_DEFAULT_TSL}")
            top.destroy()
        except ValueError:
            messagebox.showerror("Lỗi dữ liệu", "Vui lòng kiểm tra lại. Cấm nhập chữ vào ô số!")

    ctk.CTkButton(top, text="LƯU CẤU HÌNH BOT & ĐỒNG BỘ", fg_color=COL_BLUE_ACCENT, height=45, font=("Roboto", 14, "bold"), command=save_all_bot_settings).pack(pady=10, fill="x", padx=40)

    # ----------------------------------------------------------------------
    # TAB: MANUAL ASSIST
    # ----------------------------------------------------------------------
    tab_ast = tabview.tab("MANUAL ASSIST")
    ctk.CTkLabel(tab_ast, text="Tùy chọn Hỗ trợ Giao dịch Tay (Manual):", text_color="gray").pack(pady=(20,10))
    ctk.CTkCheckBox(tab_ast, text="Tự lấy SL theo Math SL (Swing/ATR)", variable=app.var_assist_math_sl).pack(anchor="w", padx=50, pady=10)
    ctk.CTkCheckBox(tab_ast, text="Tự tính TP theo Preset (Dành cho bấm tay)", variable=app.var_assist_preset_tp).pack(anchor="w", padx=50, pady=10)
    ctk.CTkCheckBox(tab_ast, text="Kích hoạt Auto DCA (Trung bình giá)", variable=app.var_assist_dca).pack(anchor="w", padx=50, pady=10)
    ctk.CTkCheckBox(tab_ast, text="Kích hoạt Auto PCA (Nhồi lệnh trend)", variable=app.var_assist_pca).pack(anchor="w", padx=50, pady=10)


# ==============================================================================
# 2. CÁC POPUP CẤU HÌNH KHÁC (PRESET, TSL, EDIT, HISTORY)
# ==============================================================================
def open_preset_config_popup(app):
    p_name = app.cbo_preset.get()
    data = config.PRESETS.get(p_name, {})
    
    top = ctk.CTkToplevel(app)
    top.title(f"Cấu hình Preset: {p_name}")
    top.geometry("400x450") 
    top.attributes("-topmost", True)
    
    acc = app.connector.get_account_info()
    current_equity = acc['equity'] if acc else 1000.0 
    sym = app.cbo_symbol.get()
    tick = app.connector.get_market_status(sym) 
    current_price = tick.get("ask", 1000.0) if isinstance(tick, dict) else 1000.0 
    
    ctk.CTkLabel(top, text=f"PRESET: {p_name}", font=FONT_BOLD).pack(pady=10)
    
    ctk.CTkLabel(top, text="Rủi ro / Lệnh (% Balance)").pack()
    e_risk = ctk.CTkEntry(top, justify="center"); e_risk.insert(0, str(data.get("RISK_PERCENT", config.RISK_PER_TRADE_PERCENT))); e_risk.pack()
    lbl_hint_risk = ctk.CTkLabel(top, text="~ -$0.00", text_color="gray", font=("Roboto", 11)); lbl_hint_risk.pack(pady=(0, 5))

    ctk.CTkLabel(top, text="Khoảng cách SL (% Giá)").pack()
    e_sl = ctk.CTkEntry(top, justify="center"); e_sl.insert(0, str(data.get("SL_PERCENT", 0.5))); e_sl.pack()
    lbl_hint_sl = ctk.CTkLabel(top, text="~ Price: 0.00", text_color="gray", font=("Roboto", 11)); lbl_hint_sl.pack(pady=(0, 5))
    
    ctk.CTkLabel(top, text="Tỷ lệ TP (Reward/Risk)").pack()
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
        app.save_settings()
        top.destroy()
        app.log_message(f"Đã cập nhật Preset {p_name}")

    ctk.CTkButton(top, text="LƯU PRESET", command=save, fg_color=COL_GREEN).pack(pady=20, fill="x", padx=30)


def open_tsl_popup(app):
    top = ctk.CTkToplevel(app); top.title("Cấu hình TSL Logic"); top.geometry("420x580"); top.attributes("-topmost", True)
    
    acc = app.connector.get_account_info()
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

    f3 = sec("2. KHÓA LÃI PNL (Levels)")
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

    f4 = sec("3. STEP R (Nuôi Lệnh Từng Bước)")
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
            app.save_settings(); top.destroy(); app.log_message("✅ Đã cập nhật cấu hình TSL Logic.")
        except Exception:
            messagebox.showerror("Lỗi", "Cấu hình không hợp lệ.")

    ctk.CTkButton(top, text="LƯU CẤU HÌNH TSL", height=35, font=("Roboto", 13, "bold"), command=save_cfg, fg_color=COL_GREEN).pack(pady=15, fill="x", padx=40)


def open_edit_popup(app, ticket):
    positions = app.connector.get_all_open_positions()
    pos = next((p for p in positions if p.ticket == ticket), None)
    if not pos: return
    
    top = ctk.CTkToplevel(app)
    top.title(f"Chỉnh sửa lệnh #{ticket}")
    top.geometry("400x600")
    top.attributes("-topmost", True)
    
    acc = app.connector.get_account_info()
    balance = acc['balance'] if acc else 1000.0
    
    sym_info = app.connector.get_market_status(pos.symbol) 
    c_size = sym_info.get("contract_size", 1.0) if isinstance(sym_info, dict) else 1.0
    
    is_buy = pos.type == 0 
    
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
                    lbl_hint_sl.configure(text=f"~ +${abs(loss_usd):.2f} (Đã khóa lãi)", text_color="#66BB6A")
                else:
                    lbl_hint_sl.configure(text=f"~ -${loss_usd:.2f} ({loss_usd/balance*100:.2f}%)", text_color="#EF5350")
            else: lbl_hint_sl.configure(text="~ Không có SL", text_color="gray")

            if new_tp > 0:
                prof_dist = new_tp - pos.price_open if is_buy else pos.price_open - new_tp
                prof_usd = prof_dist * pos.volume * c_size
                if prof_usd > 0:
                    lbl_hint_tp.configure(text=f"~ +${prof_usd:.2f} ({prof_usd/balance*100:.2f}%)", text_color="#66BB6A")
                else:
                    lbl_hint_tp.configure(text="TP Không hợp lệ", text_color="#EF5350")
            else: lbl_hint_tp.configure(text="~ Không có TP", text_color="gray")
        except ValueError:
             pass

    ent_sl.bind("<KeyRelease>", update_edit_previews)
    ent_tp.bind("<KeyRelease>", update_edit_previews)
    update_edit_previews()

    ctk.CTkFrame(top, height=2, fg_color="#333").pack(fill="x", padx=30, pady=10)
    ctk.CTkLabel(top, text="ỦY QUYỀN (BOT ASSIGNMENT):", font=FONT_BOLD, text_color="#90CAF9").pack(pady=(0, 10))
    
    f_bot_actions = ctk.CTkFrame(top, fg_color="transparent")
    f_bot_actions.pack(fill="x", padx=20)
    
    def apply_math_sl():
        sl_val = app.latest_market_context.get("swing_low") if is_buy else app.latest_market_context.get("swing_high")
        atr_val = app.latest_market_context.get("atr")
        if sl_val and atr_val and str(sl_val) != "--" and str(atr_val) != "--":
            sl_mult = getattr(config, "sl_atr_multiplier", 0.2)
            calc_sl = float(sl_val) - (float(atr_val) * sl_mult) if is_buy else float(sl_val) + (float(atr_val) * sl_mult)
            ent_sl.delete(0, 'end'); ent_sl.insert(0, f"{calc_sl:.2f}")
            update_edit_previews()
        else:
            messagebox.showwarning("Thiếu Data", "Chưa có dữ liệu Swing/ATR từ Daemon.")

    def apply_preset_tp():
        try:
            curr_sl = float(ent_sl.get())
            if curr_sl <= 0: raise ValueError
            params = config.PRESETS.get(app.cbo_preset.get(), config.PRESETS["SCALPING"])
            rr = params.get("TP_RR_RATIO", 1.5)
            dist = abs(pos.price_open - curr_sl)
            calc_tp = pos.price_open + (dist * rr) if is_buy else pos.price_open - (dist * rr)
            ent_tp.delete(0, 'end'); ent_tp.insert(0, f"{calc_tp:.2f}")
            update_edit_previews()
        except:
            messagebox.showwarning("Lỗi", "Hãy xác định SL (hoặc Math SL) trước khi tính TP.")

    ctk.CTkButton(f_bot_actions, text="Lấy Math SL", width=140, fg_color="#1565C0", command=apply_math_sl).pack(side="left", padx=5)
    ctk.CTkButton(f_bot_actions, text="Lấy Preset TP", width=140, fg_color="#2E7D32", command=apply_preset_tp).pack(side="right", padx=5)
    
    f_chk = ctk.CTkFrame(top, fg_color="transparent")
    f_chk.pack(pady=10)
    chk_dca = ctk.CTkCheckBox(f_chk, text="Cho phép Auto DCA", font=("Roboto", 11), text_color="gray"); chk_dca.pack(side="left", padx=10)
    chk_pca = ctk.CTkCheckBox(f_chk, text="Cho phép Auto PCA", font=("Roboto", 11), text_color="gray"); chk_pca.pack(side="left")

    ctk.CTkLabel(top, text="GHI ĐÈ CHIẾN THUẬT CHO LỆNH NÀY:", font=FONT_BOLD, text_color="#FFB300").pack(pady=(10, 5))
    f_btns = ctk.CTkFrame(top, fg_color="transparent")
    f_btns.pack()
    
    cur_tstr = app.trade_mgr.get_trade_tactic(ticket)
    p_states = {"BE": "BE" in cur_tstr, "PNL": "PNL" in cur_tstr, "STEP_R": "STEP_R" in cur_tstr, "SWING": "SWING" in cur_tstr}
    
    if "AUTO_DCA" in cur_tstr: chk_dca.select()
    if "AUTO_PCA" in cur_tstr: chk_pca.select()
    
    lbl_tactic_preview = ctk.CTkLabel(top, text="Trạng thái: Đang tải...", font=("Roboto", 12), text_color="gray")
    lbl_tactic_preview.pack(pady=(2, 5))

    def live_update_tactic_status():
        if not lbl_tactic_preview.winfo_exists(): return
        if "Chưa lưu" not in lbl_tactic_preview.cget("text"):
            new_stt = app.tsl_states_map.get(ticket, "Monitoring...")
            lbl_tactic_preview.configure(text=f"Status: {new_stt}")
        top.after(500, live_update_tactic_status) 
        
    live_update_tactic_status()

    def update_pbtns():
        b_be.configure(fg_color=COL_BLUE_ACCENT if p_states["BE"] else COL_GRAY_BTN)
        b_pnl.configure(fg_color=COL_BLUE_ACCENT if p_states["PNL"] else COL_GRAY_BTN)
        b_step.configure(fg_color=COL_BLUE_ACCENT if p_states["STEP_R"] else COL_GRAY_BTN)
        b_swing.configure(fg_color=COL_BLUE_ACCENT if p_states["SWING"] else COL_GRAY_BTN)

    def tog(k):
        p_states[k] = not p_states[k]
        update_pbtns()
        lbl_tactic_preview.configure(text="Status: * Tactic thay đổi, chưa lưu *", text_color=COL_WARN)

    b_be = ctk.CTkButton(f_btns, text="BE", width=45, command=lambda: tog("BE")); b_be.pack(side="left", padx=2)
    b_pnl = ctk.CTkButton(f_btns, text="PNL", width=45, command=lambda: tog("PNL")); b_pnl.pack(side="left", padx=2)
    b_step = ctk.CTkButton(f_btns, text="STEP", width=45, command=lambda: tog("STEP_R")); b_step.pack(side="left", padx=2)
    b_swing = ctk.CTkButton(f_btns, text="SWING", width=45, command=lambda: tog("SWING")); b_swing.pack(side="left", padx=2)
    update_pbtns()

    def save():
        try:
            sl_val, tp_val = float(ent_sl.get()), float(ent_tp.get())
        except ValueError:
            messagebox.showerror("Lỗi", "Vui lòng nhập số hợp lệ.")
            return

        try:
            app.connector.modify_position(ticket, sl_val, tp_val)
            act = [k for k,v in p_states.items() if v]
            new_t = "+".join(act) if act else "OFF"
            if chk_dca.get(): new_t += "+AUTO_DCA"
            if chk_pca.get(): new_t += "+AUTO_PCA"
            
            # Hàm này sẽ gọi vào core/trade_manager.py
            app.trade_mgr.update_trade_tactic(ticket, new_t)
            
            ent_sl.unbind("<KeyRelease>"); ent_tp.unbind("<KeyRelease>")
            top.destroy()
            app.log_message(f"Đã cập nhật lệnh #{ticket} [{new_t}]")
        except Exception as e:
            app.log_message(f"Lỗi khi update lệnh: {e}", error=True)

    ctk.CTkButton(top, text="CẬP NHẬT LỆNH", height=40, fg_color="#2e7d32", command=save).pack(pady=15, fill="x", padx=30)

def show_history_popup(app):
    top = ctk.CTkToplevel(app); top.title("Lịch sử hôm nay"); top.geometry("700x450")
    tr = ttk.Treeview(top, columns=("Time", "Sym", "Type", "PnL", "Reason"), show="headings"); tr.pack(fill="both", expand=True)
    for c in tr["columns"]: tr.heading(c, text=c)
    for h in app.trade_mgr.state.get("daily_history", []): 
        tr.insert("", "end", values=(h['time'], h['symbol'], h['type'], f"${h['profit']:.2f}", h.get('reason','')))