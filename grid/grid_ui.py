# -*- coding: utf-8 -*-
"""GRID settings popup."""

import customtkinter as ctk
from tkinter import messagebox

import config
from .grid_storage import load_grid_settings, load_grid_state, save_grid_settings


def _entry(parent, label, value, row, col=0, width=90):
    ctk.CTkLabel(parent, text=label).grid(row=row, column=col, sticky="w", padx=10, pady=6)
    var = ctk.StringVar(value=str(value))
    ctk.CTkEntry(parent, textvariable=var, width=width, justify="center").grid(
        row=row, column=col + 1, sticky="w", padx=10, pady=6
    )
    return var


def open_grid_settings_popup(app):
    cfg = load_grid_settings()
    state = load_grid_state()

    top = ctk.CTkToplevel(app)
    top.title("GRID Module Settings")
    top.geometry("920x720")
    top.minsize(760, 560)
    top.attributes("-topmost", True)
    top.focus_force()
    top.grab_set()

    tabview = ctk.CTkTabview(top)
    tabview.pack(fill="both", expand=True, padx=12, pady=(10, 6))
    tab_signal = tabview.add("Signal")
    tab_behavior = tabview.add("Behavior")
    tab_risk = tabview.add("Risk")
    tab_preview = tabview.add("Preview")

    # Signal
    signal_hint = ctk.CTkFrame(tab_signal, fg_color="#06262B", border_width=1, border_color="#00B8D4")
    signal_hint.pack(fill="x", padx=10, pady=10)
    ctk.CTkLabel(
        signal_hint,
        text=(
            "GRID Signal reuses QUANT/Sandbox logic as a permission and bias gate.\n"
            "BUY -> Long Grid, SELL -> Short Grid, NONE -> Neutral or Block by NONE_POLICY."
        ),
        justify="left",
        anchor="w",
        wraplength=820,
        text_color="#80DEEA",
        font=("Arial", 12, "italic"),
    ).pack(fill="x", padx=10, pady=8)

    enabled = ctk.BooleanVar(value=cfg.get("ENABLED", False))
    dynamic_mode = ctk.BooleanVar(value=cfg.get("DYNAMIC_MODE_ENABLED", True))
    ctk.CTkCheckBox(tab_signal, text="GRID ENABLED", variable=enabled, font=("Roboto", 13, "bold"), text_color="#00B8D4").pack(anchor="w", padx=18, pady=8)
    ctk.CTkCheckBox(tab_signal, text="Dynamic mode from GRID signal", variable=dynamic_mode).pack(anchor="w", padx=18, pady=4)

    signal_row = ctk.CTkFrame(tab_signal, fg_color="transparent")
    signal_row.pack(fill="x", padx=12, pady=8)
    ctk.CTkLabel(signal_row, text="NONE policy:").pack(side="left", padx=6)
    none_policy = ctk.CTkOptionMenu(signal_row, values=["NEUTRAL", "BLOCK"], width=120)
    none_policy.set(cfg.get("NONE_POLICY", "NEUTRAL"))
    none_policy.pack(side="left", padx=6)
    ctk.CTkLabel(signal_row, text="Default manual mode:").pack(side="left", padx=(24, 6))
    default_manual = ctk.CTkOptionMenu(signal_row, values=["NEUTRAL", "LONG", "SHORT"], width=120)
    default_manual.set(cfg.get("DEFAULT_MANUAL_MODE", "NEUTRAL"))
    default_manual.pack(side="left", padx=6)

    tf_row = ctk.CTkFrame(tab_signal, fg_color="transparent")
    tf_row.pack(fill="x", padx=12, pady=8)
    ctk.CTkLabel(tf_row, text="GRID data group:").pack(side="left", padx=6)
    grid_group = ctk.CTkOptionMenu(tf_row, values=["G0", "G1", "G2", "G3"], width=90)
    grid_group.set(cfg.get("GRID_TIMEFRAME_GROUP", "G2"))
    grid_group.pack(side="left", padx=6)
    ctk.CTkLabel(tf_row, text="Trend filter group:").pack(side="left", padx=(24, 6))
    trend_group = ctk.CTkOptionMenu(tf_row, values=["G0", "G1", "G2", "G3"], width=90)
    trend_group.set(cfg.get("TREND_FILTER_GROUP", "G1"))
    trend_group.pack(side="left", padx=6)

    def import_quant_signal():
        try:
            brain = app.trade_mgr._get_brain_settings(app.cbo_symbol.get())
            cfg["GRID_SIGNAL_CONFIG"] = {
                "MASTER_EVAL_MODE": brain.get("MASTER_EVAL_MODE"),
                "MIN_MATCHING_VOTES": brain.get("MIN_MATCHING_VOTES"),
                "voting_rules": brain.get("voting_rules", {}),
                "indicators": brain.get("indicators", {}),
            }
            app.log_message("[GRID] Imported QUANT signal config into GRID settings draft.", target="grid-log")
        except Exception as e:
            messagebox.showerror("GRID", f"Cannot import QUANT config: {e}", parent=top)

    ctk.CTkButton(tab_signal, text="IMPORT QUANT SIGNAL CONFIG", command=import_quant_signal, fg_color="#1565C0").pack(anchor="w", padx=18, pady=10)

    # Behavior
    behavior = ctk.CTkFrame(tab_behavior, fg_color="#242424", corner_radius=8)
    behavior.pack(fill="x", padx=10, pady=10)
    fixed_lot = _entry(behavior, "Fixed Lot:", cfg.get("FIXED_LOT", 0.01), 0)
    spacing_atr = _entry(behavior, "Spacing ATR x:", cfg.get("SPACING_ATR_MULTIPLIER", 1.0), 1)
    tp_spacing = _entry(behavior, "TP Spacing x:", cfg.get("TAKE_PROFIT_SPACING_MULTIPLIER", 0.8), 2)
    reopen_cd = _entry(behavior, "Reopen Cooldown (s):", cfg.get("REOPEN_COOLDOWN_SECONDS", 60), 3)

    boundary_row = ctk.CTkFrame(tab_behavior, fg_color="#242424", corner_radius=8)
    boundary_row.pack(fill="x", padx=10, pady=10)
    ctk.CTkLabel(boundary_row, text="Boundary Mode:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
    boundary_mode = ctk.CTkOptionMenu(boundary_row, values=["HYBRID", "AUTO_SWING", "MANUAL"], width=130)
    boundary_mode.set(cfg.get("BOUNDARY_MODE", "HYBRID"))
    boundary_mode.grid(row=0, column=1, padx=10, pady=8, sticky="w")
    manual_upper = _entry(boundary_row, "Manual Upper:", cfg.get("MANUAL_UPPER_BOUNDARY", 0.0), 1)
    manual_lower = _entry(boundary_row, "Manual Lower:", cfg.get("MANUAL_LOWER_BOUNDARY", 0.0), 2)

    # Risk
    risk = ctk.CTkFrame(tab_risk, fg_color="#242424", corner_radius=8)
    risk.pack(fill="x", padx=10, pady=10)
    max_orders = _entry(risk, "Max Grid Orders:", cfg.get("MAX_GRID_ORDERS", 0), 0)
    max_total_lot = _entry(risk, "Max Gross Lot:", cfg.get("MAX_TOTAL_LOT", 0.0), 1)
    max_dd = _entry(risk, "Max Session DD:", cfg.get("MAX_BASKET_DRAWDOWN", 0.0), 2)
    check_ping = ctk.BooleanVar(value=cfg.get("CHECK_PING", True))
    ctk.CTkCheckBox(risk, text="Check Ping", variable=check_ping).grid(row=3, column=0, sticky="w", padx=10, pady=6)
    max_ping = _entry(risk, "Max Ping (ms):", cfg.get("MAX_PING_MS", 150), 4)
    check_spread = ctk.BooleanVar(value=cfg.get("CHECK_SPREAD", True))
    ctk.CTkCheckBox(risk, text="Check Spread", variable=check_spread).grid(row=5, column=0, sticky="w", padx=10, pady=6)
    max_spread = _entry(risk, "Max Spread (pts):", cfg.get("MAX_SPREAD_POINTS", 150), 6)
    stop_breakout = ctk.BooleanVar(value=cfg.get("STOP_ON_BREAKOUT", True))
    ctk.CTkCheckBox(risk, text="Stop new orders on TREND/BREAKOUT", variable=stop_breakout).grid(row=7, column=0, columnspan=2, sticky="w", padx=10, pady=6)

    # Watchlist
    watchlist_frame = ctk.CTkScrollableFrame(tab_risk, fg_color="#242424", corner_radius=8, height=170)
    watchlist_frame.pack(fill="x", padx=10, pady=10)
    ctk.CTkLabel(watchlist_frame, text="GRID Watchlist", font=("Roboto", 13, "bold"), text_color="#00B8D4").pack(anchor="w", padx=10, pady=8)
    current_watchlist = set(cfg.get("WATCHLIST", []) or [])
    coin_vars = {}
    grid = ctk.CTkFrame(watchlist_frame, fg_color="transparent")
    grid.pack(fill="x", padx=8, pady=(0, 10))
    for i, coin in enumerate(getattr(config, "COIN_LIST", getattr(config, "SYMBOLS", []))):
        var = ctk.BooleanVar(value=(coin in current_watchlist))
        coin_vars[coin] = var
        ctk.CTkCheckBox(grid, text=coin, variable=var, width=110).grid(row=i // 4, column=i % 4, sticky="w", padx=6, pady=4)

    # Preview
    preview_text = ctk.CTkTextbox(tab_preview, height=420, font=("Consolas", 13))
    preview_text.pack(fill="both", expand=True, padx=10, pady=10)
    preview = state.get("last_preview", {})
    sessions = state.get("active_sessions", {})
    preview_text.insert("end", "GRID LAST PREVIEW\n\n")
    preview_text.insert("end", f"Sessions: {list(sessions.keys())}\n\n")
    for sym, data in preview.items():
        preview_text.insert("end", f"{sym}: {data}\n")
    preview_text.configure(state="disabled")

    def save():
        try:
            next_cfg = dict(cfg)
            next_cfg.update({
                "ENABLED": enabled.get(),
                "DYNAMIC_MODE_ENABLED": dynamic_mode.get(),
                "NONE_POLICY": none_policy.get(),
                "DEFAULT_MANUAL_MODE": default_manual.get(),
                "GRID_TIMEFRAME_GROUP": grid_group.get(),
                "TREND_FILTER_GROUP": trend_group.get(),
                "BOUNDARY_MODE": boundary_mode.get(),
                "MANUAL_UPPER_BOUNDARY": float(manual_upper.get() or 0.0),
                "MANUAL_LOWER_BOUNDARY": float(manual_lower.get() or 0.0),
                "FIXED_LOT": float(fixed_lot.get() or 0.01),
                "SPACING_ATR_MULTIPLIER": float(spacing_atr.get() or 1.0),
                "TAKE_PROFIT_SPACING_MULTIPLIER": float(tp_spacing.get() or 0.8),
                "REOPEN_COOLDOWN_SECONDS": int(reopen_cd.get() or 60),
                "MAX_GRID_ORDERS": int(max_orders.get() or 0),
                "MAX_TOTAL_LOT": float(max_total_lot.get() or 0.0),
                "MAX_BASKET_DRAWDOWN": float(max_dd.get() or 0.0),
                "CHECK_PING": check_ping.get(),
                "MAX_PING_MS": int(max_ping.get() or 0),
                "CHECK_SPREAD": check_spread.get(),
                "MAX_SPREAD_POINTS": int(max_spread.get() or 0),
                "STOP_ON_BREAKOUT": stop_breakout.get(),
                "WATCHLIST": [coin for coin, var in coin_vars.items() if var.get()],
            })
            save_grid_settings(next_cfg)
            if hasattr(app, "log_message"):
                app.log_message("[GRID] Settings saved.", target="grid")
            top.destroy()
        except ValueError:
            messagebox.showerror("GRID", "GRID settings nhập sai kiểu số.", parent=top)

    ctk.CTkButton(top, text="SAVE GRID SETTINGS", fg_color="#00838F", hover_color="#006064", font=("Roboto", 13, "bold"), height=38, command=save).pack(fill="x", padx=24, pady=(4, 14))
