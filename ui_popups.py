# -*- coding: utf-8 -*-
# FILE: ui_popups.py
# V3.8: SUPREME FINAL - TRANSIENT LOCK & TACTIC PREVIEW (KAISER EDITION)

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
# 1. POPUP CẤU HÌNH LÕI (CHỈ CÒN SAFETY & WATCHLIST)
# ==============================================================================
def open_bot_setting_popup(app):
    top = ctk.CTkToplevel(app)
    top.title("Cấu hình Lõi Hệ Thống (Core Settings)")
    top.geometry("700x550") 
    top.attributes("-topmost", True)
    #top.transient(app) # Khóa Z-index, luôn nổi trên App chính
    
    tab_core = ctk.CTkScrollableFrame(top, fg_color="transparent")
    tab_core.pack(fill="both", expand=True, padx=15, pady=15)
    
    # Switch Auto Trade
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
    
    # Safety Guard (Bot & UI)
    ctk.CTkLabel(tab_core, text="HÀNG RÀO BẢO VỆ & DỮ LIỆU (SAFETY GUARD)", font=FONT_BOLD, text_color="#FFB300").pack(pady=(5, 5))
    f_safety = ctk.CTkFrame(tab_core, fg_color="#2b2b2b", corner_radius=8)
    f_safety.pack(fill="x", padx=15, pady=5)
    f_safety.columnconfigure((0, 2), weight=1)

    ctk.CTkLabel(f_safety, text="Max Loss/Ngày (%):").grid(row=0, column=0, sticky="w", padx=10, pady=8)
    e_max_loss = ctk.CTkEntry(f_safety, width=70, justify="center"); e_max_loss.insert(0, str(getattr(config, "MAX_DAILY_LOSS_PERCENT", 2.5))); e_max_loss.grid(row=0, column=1, sticky="w", padx=10, pady=8)

    ctk.CTkLabel(f_safety, text="Max Lệnh Chạy Cùng Lúc:").grid(row=0, column=2, sticky="w", padx=10, pady=8)
    e_max_open = ctk.CTkEntry(f_safety, width=70, justify="center"); e_max_open.insert(0, str(getattr(config, "MAX_OPEN_POSITIONS", 3))); e_max_open.grid(row=0, column=3, sticky="w", padx=10, pady=8)

    ctk.CTkLabel(f_safety, text="Tổng Lệnh/Ngày:").grid(row=1, column=0, sticky="w", padx=10, pady=8)
    e_max_trades = ctk.CTkEntry(f_safety, width=70, justify="center"); e_max_trades.insert(0, str(getattr(config, "MAX_TRADES_PER_DAY", 30))); e_max_trades.grid(row=1, column=1, sticky="w", padx=10, pady=8)

    ctk.CTkLabel(f_safety, text="Max Lệnh Thua (Streak):").grid(row=1, column=2, sticky="w", padx=10, pady=8)
    e_max_streak = ctk.CTkEntry(f_safety, width=70, justify="center"); e_max_streak.insert(0, str(getattr(config, "MAX_LOSING_STREAK", 3))); e_max_streak.grid(row=1, column=3, sticky="w", padx=10, pady=8)

    ctk.CTkLabel(f_safety, text="Chế độ tính Loss:").grid(row=2, column=0, sticky="w", padx=10, pady=8)
    cbo_loss_mode = ctk.CTkOptionMenu(f_safety, values=["TOTAL", "STREAK"], width=90); cbo_loss_mode.set(str(getattr(config, "LOSS_COUNT_MODE", "TOTAL"))); cbo_loss_mode.grid(row=2, column=1, sticky="w", padx=10, pady=8)

    ctk.CTkLabel(f_safety, text="Cooldown (Phút):").grid(row=2, column=2, sticky="w", padx=10, pady=8)
    e_cooldown = ctk.CTkEntry(f_safety, width=70, justify="center"); e_cooldown.insert(0, str(getattr(config, "COOLDOWN_MINUTES", 1))); e_cooldown.grid(row=2, column=3, sticky="w", padx=10, pady=8)

    ctk.CTkLabel(f_safety, text="Nến Trend (G0/G1):").grid(row=3, column=0, sticky="w", padx=10, pady=8)
    e_num_h1 = ctk.CTkEntry(f_safety, width=70, justify="center"); e_num_h1.insert(0, str(getattr(config, "NUM_H1_BARS", 70))); e_num_h1.grid(row=3, column=1, sticky="w", padx=10, pady=8)

    ctk.CTkLabel(f_safety, text="Nến Entry (G2/G3):").grid(row=3, column=2, sticky="w", padx=10, pady=8)
    e_num_m15 = ctk.CTkEntry(f_safety, width=70, justify="center"); e_num_m15.insert(0, str(getattr(config, "NUM_M15_BARS", 70))); e_num_m15.grid(row=3, column=3, sticky="w", padx=10, pady=8)
    ctk.CTkFrame(tab_core, height=2, fg_color="#333").pack(fill="x", padx=30, pady=10)

    # Watchlist
    ctk.CTkLabel(tab_core, text="WATCHLIST - BOT CHỈ QUÉT CÁC COIN SAU:", font=FONT_BOLD, text_color="#2196F3").pack(pady=(5, 5))
    f_coins = ctk.CTkFrame(tab_core, fg_color="transparent"); f_coins.pack(fill="x", padx=30, pady=(0, 10))
    app.bot_coin_vars = {}
    allowed_list = getattr(config, "BOT_ACTIVE_SYMBOLS", config.COIN_LIST)
    for i, coin in enumerate(config.COIN_LIST):
        var = tk.BooleanVar(value=(coin in allowed_list)); app.bot_coin_vars[coin] = var
        ctk.CTkCheckBox(f_coins, text=coin, variable=var, font=("Consolas", 13)).grid(row=i//2, column=i%2, sticky="w", pady=5, padx=10)

    def save():
        try:
            config.MAX_DAILY_LOSS_PERCENT, config.MAX_OPEN_POSITIONS = float(e_max_loss.get()), int(e_max_open.get())
            config.MAX_TRADES_PER_DAY, config.MAX_LOSING_STREAK = int(e_max_trades.get()), int(e_max_streak.get())
            config.LOSS_COUNT_MODE, config.COOLDOWN_MINUTES = cbo_loss_mode.get(), int(e_cooldown.get())
            config.NUM_H1_BARS, config.NUM_M15_BARS = int(e_num_h1.get()), int(e_num_m15.get())
            config.BOT_ACTIVE_SYMBOLS = [coin for coin, var in app.bot_coin_vars.items() if var.get()]
            app._save_brain_live_config() # <-- Sửa dòng này
            app.log_message("✅ Core Settings Saved.")
            top.destroy()
        except ValueError: messagebox.showerror("Lỗi", "Dữ liệu nhập sai!")

    ctk.CTkButton(top, text="LƯU CẤU HÌNH CỐT LÕI", fg_color=COL_BLUE_ACCENT, height=45, font=FONT_BOLD, command=save).pack(pady=20, fill="x", padx=40)

# ==============================================================================
# 2. POPUP PRESET (CÓ LIVE PREVIEW ĐẦY ĐỦ)
# ==============================================================================
def open_preset_config_popup(app):
    p_name = app.cbo_preset.get(); data = config.PRESETS.get(p_name, {})
    top = ctk.CTkToplevel(app); top.title(f"Preset: {p_name}"); top.geometry("400x450"); top.attributes("-topmost", True)
    #top.transient(app)
    
    acc = app.connector.get_account_info(); eq = acc['equity'] if acc else 1000.0
    tick = app.connector.get_market_status(app.cbo_symbol.get()); cp = tick.get("ask", 1000.0) if isinstance(tick, dict) else 1000.0
    
    ctk.CTkLabel(top, text=f"PRESET: {p_name}", font=FONT_BOLD).pack(pady=10)
    e_risk = ctk.CTkEntry(top, justify="center"); e_risk.insert(0, str(data.get("RISK_PERCENT", 0.3))); e_risk.pack()
    lbl_h_risk = ctk.CTkLabel(top, text="~ -$0.00", text_color="gray", font=("Roboto", 11)); lbl_h_risk.pack(pady=(0, 5))

    e_sl = ctk.CTkEntry(top, justify="center"); e_sl.insert(0, str(data.get("SL_PERCENT", 0.5))); e_sl.pack()
    lbl_h_sl = ctk.CTkLabel(top, text="~ Price: 0.00", text_color="gray", font=("Roboto", 11)); lbl_h_sl.pack(pady=(0, 5))
    
    e_tp = ctk.CTkEntry(top, justify="center"); e_tp.insert(0, str(data.get("TP_RR_RATIO", 2.0))); e_tp.pack()
    lbl_h_tp = ctk.CTkLabel(top, text="~ +$0.00", text_color="gray", font=("Roboto", 11)); lbl_h_tp.pack(pady=(0, 10))
    
    def live(*args):
        try:
            r, s, t = float(e_risk.get() or 0), float(e_sl.get() or 0), float(e_tp.get() or 0)
            risk_usd = eq * (r / 100)
            lbl_h_risk.configure(text=f"(~ Mất ${risk_usd:.2f} nếu dính SL)", text_color="#EF5350")
            lbl_h_sl.configure(text=f"(~ Đặt SL quanh {cp*(1-s/100):.2f} cho BUY)", text_color="gray")
            lbl_h_tp.configure(text=f"(~ Lãi ${risk_usd*t:.2f} nếu chạm TP)", text_color="#66BB6A")
        except ValueError: pass

    e_risk.bind("<KeyRelease>", live); e_sl.bind("<KeyRelease>", live); e_tp.bind("<KeyRelease>", live); live()
    ctk.CTkButton(top, text="LƯU PRESET", command=lambda: [config.PRESETS[p_name].update({"RISK_PERCENT":float(e_risk.get()), "SL_PERCENT":float(e_sl.get()), "TP_RR_RATIO":float(e_tp.get())}), app.save_settings(), top.destroy()], fg_color=COL_GREEN).pack(pady=20, fill="x", padx=30)

# ==============================================================================
# 3. POPUP TSL (CÓ BE SOFT/SMART, PNL LEVELS +, STEP R)
# ==============================================================================
def open_tsl_popup(app):
    top = ctk.CTkToplevel(app); top.title("TSL Logic"); top.geometry("420x600"); top.attributes("-topmost", True)
    #top.transient(app)
    
    def sec(t):
        ctk.CTkLabel(top, text=t, font=("Roboto", 12, "bold"), text_color="#03A9F4").pack(fill="x", padx=15, pady=(10, 2), anchor="w")
        return ctk.CTkFrame(top, fg_color="transparent")

    f_be = sec("1. BREAK-EVEN (BE)"); f_be.pack(fill="x", padx=15)
    cbo_be = ctk.CTkOptionMenu(f_be, values=["SOFT", "SMART"], width=100); cbo_be.set(config.TSL_CONFIG.get("BE_MODE", "SOFT")); cbo_be.pack(side="right")
    e_be_rr = ctk.CTkEntry(f_be, width=50); e_be_rr.insert(0, str(config.TSL_CONFIG.get("BE_OFFSET_RR", 0.8))); e_be_rr.pack(side="left", padx=5)
    ctk.CTkLabel(f_be, text="Trigger(R):").pack(side="left")

    f_pnl = sec("2. KHÓA LÃI PNL (LEVELS)"); f_pnl.pack(fill="both", expand=True, padx=15)
    scroll_pnl = ctk.CTkScrollableFrame(f_pnl, height=120); scroll_pnl.pack(fill="both", expand=True)
    pnl_entries = []
    def add_p(v1=0.0, v2=0.0):
        r = ctk.CTkFrame(scroll_pnl, fg_color="transparent"); r.pack(fill="x", pady=2)
        e1, e2 = ctk.CTkEntry(r, width=60), ctk.CTkEntry(r, width=60)
        e1.insert(0, str(v1)); e1.pack(side="left"); ctk.CTkLabel(r, text="% Win -> Lock %").pack(side="left", padx=5)
        e2.insert(0, str(v2)); e2.pack(side="right"); pnl_entries.append((r, e1, e2))
    for lvl in config.TSL_CONFIG.get("PNL_LEVELS", []): add_p(lvl[0], lvl[1])
    
    f_pbtns = ctk.CTkFrame(f_pnl, fg_color="transparent"); f_pbtns.pack(fill="x")
    ctk.CTkButton(f_pbtns, text="+", width=40, command=lambda: add_p(0.0, 0.0)).pack(side="left", padx=5)
    ctk.CTkButton(f_pbtns, text="-", width=40, command=lambda: pnl_entries.pop()[0].destroy() if pnl_entries else None).pack(side="right", padx=5)

    f_step = sec("3. STEP R (TRAIL)"); f_step.pack(fill="x", padx=15)
    e_sz = ctk.CTkEntry(f_step, width=50); e_sz.insert(0, str(config.TSL_CONFIG.get("STEP_R_SIZE", 1.0))); e_sz.pack(side="left", padx=5)
    e_rt = ctk.CTkEntry(f_step, width=50); e_rt.insert(0, str(config.TSL_CONFIG.get("STEP_R_RATIO", 0.8))); e_rt.pack(side="right", padx=5)
    ctk.CTkLabel(f_step, text="Size(R):").pack(side="left"); ctk.CTkLabel(f_step, text="Lock(0-1):").pack(side="right", padx=5)

    def save():
        try:
            config.TSL_CONFIG.update({"BE_MODE":cbo_be.get(), "BE_OFFSET_RR":float(e_be_rr.get()), "PNL_LEVELS":sorted([[float(e1.get()), float(e2.get())] for r,e1,e2 in pnl_entries if e1.get()], key=lambda x:x[0]), "STEP_R_SIZE":float(e_sz.get()), "STEP_R_RATIO":float(e_rt.get())})
            app.save_settings(); app.log_message("✅ TSL Saved."); top.destroy()
        except: messagebox.showerror("Lỗi", "Cấu hình sai!")
    ctk.CTkButton(top, text="LƯU TSL LOGIC", fg_color=COL_GREEN, command=save).pack(pady=15, fill="x", padx=40)

# ==============================================================================
# 4. POPUP EDIT ORDER (FULL FEATURES: MATH SL, PRESET TP, DCA/PCA, TACTIC TOGGLES)
# ==============================================================================
def open_edit_popup(app, ticket):
    pos = next((p for p in app.connector.get_all_open_positions() if p.ticket == ticket), None)
    if not pos: return
    top = ctk.CTkToplevel(app); top.title(f"Sửa lệnh #{ticket}"); top.geometry("450x760"); top.attributes("-topmost", True)
    #top.transient(app)
    
    is_buy = pos.type == 0; bal = app.connector.get_account_info()['balance'] if app.connector.get_account_info() else 1000.0

    ctk.CTkLabel(top, text="NEW SL:", font=FONT_BOLD).pack(pady=(10,2))
    e_sl = ctk.CTkEntry(top, justify="center"); e_sl.insert(0, str(pos.sl)); e_sl.pack()
    lbl_h_sl = ctk.CTkLabel(top, text="~ -$0.00", text_color="gray", font=("Roboto", 11)); lbl_h_sl.pack(pady=(0, 5))

    ctk.CTkLabel(top, text="NEW TP:", font=FONT_BOLD).pack(pady=(5,2))
    e_tp = ctk.CTkEntry(top, justify="center"); e_tp.insert(0, str(pos.tp)); e_tp.pack()
    lbl_h_tp = ctk.CTkLabel(top, text="~ +$0.00", text_color="gray", font=("Roboto", 11)); lbl_h_tp.pack(pady=(0, 5))
    
    # Khung chứa Live Tactic Preview
    f_tactic_preview = ctk.CTkFrame(top, fg_color="#1a1a1a", corner_radius=6)
    f_tactic_preview.pack(fill="x", padx=20, pady=5)
    lbl_tactic_preview = ctk.CTkLabel(f_tactic_preview, text="TSL Preview", text_color="#29B6F6", font=("Consolas", 12))
    lbl_tactic_preview.pack(pady=5)

    cur_t = app.trade_mgr.get_trade_tactic(ticket)
    states = {"BE":"BE" in cur_t, "PNL":"PNL" in cur_t, "STEP":"STEP_R" in cur_t, "SWING":"SWING" in cur_t}

    def live_edit(*args):
        try:
            nsl, ntp = float(e_sl.get() or 0), float(e_tp.get() or 0)
            if nsl > 0:
                dist = abs(pos.price_open - nsl)
                loss = dist * pos.volume * 1.0 # Simple Contract Size
                lbl_h_sl.configure(text=f"~ -${loss:.2f} ({loss/bal*100:.2f}%)", text_color="#EF5350")
            if ntp > 0:
                p_dist = abs(pos.price_open - ntp)
                prof = p_dist * pos.volume * 1.0
                lbl_h_tp.configure(text=f"~ +${prof:.2f}", text_color="#66BB6A")
                
            # Cập nhật Live Trigger Price Preview
            if nsl > 0:
                r_dist = abs(pos.price_open - nsl)
                if r_dist > 0:
                    preview_txts = []
                    if states["BE"]:
                        trig_r = config.TSL_CONFIG.get("BE_OFFSET_RR", 0.8)
                        trig_p = pos.price_open + (trig_r * r_dist) if is_buy else pos.price_open - (trig_r * r_dist)
                        preview_txts.append(f"BE @ {trig_p:.2f}")
                    if states["STEP"]:
                        sz = config.TSL_CONFIG.get("STEP_R_SIZE", 1.0)
                        trig_p = pos.price_open + (sz * r_dist) if is_buy else pos.price_open - (sz * r_dist)
                        preview_txts.append(f"Step 1 @ {trig_p:.2f}")
                    if states["PNL"] and config.TSL_CONFIG.get("PNL_LEVELS"):
                        lvl = config.TSL_CONFIG["PNL_LEVELS"][0]
                        preview_txts.append(f"PNL @ Lãi {lvl[0]}%")
                    if states["SWING"]:
                        preview_txts.append("SWING (Đuổi theo nến H1/M15)")

                    if preview_txts:
                        lbl_tactic_preview.configure(text="Dự kiến Trigger TSL:\n" + " | ".join(preview_txts))
                    else:
                        lbl_tactic_preview.configure(text="TSL: OFF")
        except: pass

    e_sl.bind("<KeyRelease>", live_edit); e_tp.bind("<KeyRelease>", live_edit)

    f_ast = ctk.CTkFrame(top, fg_color="transparent"); f_ast.pack(pady=10)
    
    def do_math():
        ctx = app.latest_market_context.get(pos.symbol, {})
        val = ctx.get("swing_low" if is_buy else "swing_high")
        atr_val = ctx.get("atr")
        if val and str(val) != "--" and atr_val:
            mult = getattr(config, "sl_atr_multiplier", 0.2)
            calc_sl = float(val) - (float(atr_val) * mult) if is_buy else float(val) + (float(atr_val) * mult)
            e_sl.delete(0,'end'); e_sl.insert(0, f"{calc_sl:.5f}"); live_edit()
            
    ctk.CTkButton(f_ast, text="Lấy Math SL", width=140, fg_color="#1565C0", command=do_math).pack(side="left", padx=5)
    
    def do_tp():
        try:
            rr = config.PRESETS.get(app.cbo_preset.get(), {}).get("TP_RR_RATIO", 1.5)
            tp = pos.price_open + (abs(pos.price_open-float(e_sl.get()))*rr if is_buy else -abs(pos.price_open-float(e_sl.get()))*rr)
            e_tp.delete(0,'end'); e_tp.insert(0, f"{tp:.5f}"); live_edit()
        except: pass
        
    ctk.CTkButton(f_ast, text="Lấy Preset TP", width=140, fg_color="#2E7D32", command=do_tp).pack(side="right", padx=5)
    
    f_chk = ctk.CTkFrame(top, fg_color="transparent"); f_chk.pack()
    chk_dca, chk_pca = ctk.CTkCheckBox(f_chk, text="Auto DCA", font=("Roboto",11)), ctk.CTkCheckBox(f_chk, text="Auto PCA", font=("Roboto",11))
    chk_dca.pack(side="left", padx=10); chk_pca.pack(side="left")

    if "AUTO_DCA" in cur_t: chk_dca.select()
    if "AUTO_PCA" in cur_t: chk_pca.select()
    
    f_t = ctk.CTkFrame(top, fg_color="transparent"); f_t.pack(pady=10)
    btns = {}
    
    def tog(k): 
        states[k] = not states[k]
        btns[k].configure(fg_color=COL_BLUE_ACCENT if states[k] else COL_GRAY_BTN)
        live_edit() # Cập nhật lại Preview ngay khi toggle
        
    for k in states:
        btns[k] = ctk.CTkButton(f_t, text=k, width=50, fg_color=COL_BLUE_ACCENT if states[k] else COL_GRAY_BTN, command=lambda x=k: tog(x))
        btns[k].pack(side="left", padx=2)

    live_edit() # Lần gọi đầu tiên khi mở popup

    def save_e():
        try:
            app.connector.modify_position(ticket, float(e_sl.get()), float(e_tp.get()))
            act = [k if k!="STEP" else "STEP_R" for k,v in states.items() if v]
            final_t = "+".join(act) if act else "OFF"
            if chk_dca.get(): final_t += "+AUTO_DCA"
            if chk_pca.get(): final_t += "+AUTO_PCA"
            app.trade_mgr.update_trade_tactic(ticket, final_t); top.destroy()
        except Exception as e: messagebox.showerror("Lỗi", str(e))
        
    ctk.CTkButton(top, text="CẬP NHẬT LỆNH", height=45, fg_color="#2e7d32", font=FONT_BOLD, command=save_e).pack(pady=20, fill="x", padx=40)

def show_history_popup(app):
    top = ctk.CTkToplevel(app); top.title("History"); top.geometry("750x500")
    top.transient(app)
    cols = ("Time", "Symbol", "Type", "Profit", "Reason")
    tr = ttk.Treeview(top, columns=cols, show="headings"); tr.pack(fill="both", expand=True)
    for c in cols: tr.heading(c, text=c)
    for h in app.trade_mgr.state.get("daily_history", []): tr.insert("", "end", values=(h['time'], h['symbol'], h['type'], f"${h['profit']:.2f}", h.get('reason','')))