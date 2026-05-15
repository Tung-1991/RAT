# -*- coding: utf-8 -*-
# FILE: ui_entry_exit_popup.py
# Entry/Exit Mode popup UI. UI/config only; engine is not wired yet.

import json
import os
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

import config
import core.storage_manager as storage_manager


COL_GREEN = "#00C853"
COL_WARN = "#FFAB00"
COL_GRAY_BTN = "#424242"
COL_ACCENT = "#00838F"

ENTRY_EXIT_TACTICS = {
    "FALLBACK_R": "R",
    "SWING_REJECTION": "SWING",
    "FIB_RETRACE": "FIB",
    "PULLBACK_ZONE": "PULL",
}


def default_entry_exit_config():
    return {
        "enabled": False,
        "preview_only": True,
        "active_tactics": [],
        "entry_tactics": ["SWING_REJECTION"],
        "exit_tactic": "FIB_RETRACE",
        "fallback_tactic": "FALLBACK_R",
        "signal_ttl_seconds": 900,
        "missing_data_policy": "FALLBACK_R",
        "tp_policy": "FALLBACK_R",
        "sl_source_group": "BASE_SL",
        "default_exit": {
            "use_rr_tp": True,
            "tp_rr_ratio": 1.5,
            "use_swing_tp": False,
        },
        "swing_rejection": {
            "source_group": "G2",
            "max_atr_from_swing": 0.7,
            "sl_atr_buffer": 0.2,
            "require_rejection_candle": True,
        },
        "fib_retrace": {
            "swing_source_group": "G2",
            "entry_levels": "0.5,0.618",
            "tp_levels": "1.272,1.618",
            "use_tactic_tp": False,
        },
        "pullback_zone": {
            "source": "EMA20",
            "max_atr_from_zone": 0.5,
        },
    }


def merge_cfg(base, source):
    if not isinstance(source, dict):
        return base
    for key, val in source.items():
        if isinstance(val, dict) and isinstance(base.get(key), dict):
            merge_cfg(base[key], val)
        else:
            base[key] = val
    return base


def _load_global_payload():
    try:
        if os.path.exists(storage_manager.BRAIN_FILE):
            with open(storage_manager.BRAIN_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}


def _load_global_cfg():
    payload = _load_global_payload()
    return merge_cfg(default_entry_exit_config(), payload.get("entry_exit", {}))


def _save_global_cfg(cfg):
    payload = _load_global_payload()
    payload["entry_exit"] = cfg
    os.makedirs(os.path.dirname(storage_manager.BRAIN_FILE), exist_ok=True)
    with open(storage_manager.BRAIN_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)
    storage_manager.invalidate_settings_cache()


def _hint(parent, text):
    frame = ctk.CTkFrame(
        parent,
        fg_color="#332B00",
        corner_radius=6,
        border_width=1,
        border_color="#FFD600",
    )
    frame.pack(fill="x", padx=10, pady=(8, 10))
    ctk.CTkLabel(
        frame,
        text=text,
        text_color="#FFD600",
        font=("Arial", 12, "italic"),
        justify="left",
        anchor="w",
        wraplength=690,
    ).pack(fill="x", padx=10, pady=6)


def open_entry_exit_popup(app):
    top = ctk.CTkToplevel(app)
    top.title("Entry/Exit Mode Configuration")
    top.geometry("820x780")
    top.minsize(720, 560)
    top.attributes("-topmost", True)
    top.focus_force()
    top.grab_set()

    cfg = _load_global_cfg()

    tabview = ctk.CTkTabview(top)
    tabview.pack(fill="both", expand=True, padx=12, pady=(10, 4))
    tab_basic = ctk.CTkScrollableFrame(tabview.add("Basic"), fg_color="transparent")
    tab_advanced = ctk.CTkScrollableFrame(tabview.add("Advanced"), fg_color="transparent")
    tab_overwrite = ctk.CTkScrollableFrame(tabview.add("Overwrite"), fg_color="transparent")
    for tab in (tab_basic, tab_advanced, tab_overwrite):
        tab.pack(fill="both", expand=True, padx=4, pady=4)

    var_enabled = tk.BooleanVar()
    var_preview_only = tk.BooleanVar()
    tactic_vars = {key: tk.BooleanVar() for key in ENTRY_EXIT_TACTICS}
    entry_tactic_vars = {key: tk.BooleanVar() for key in ENTRY_EXIT_TACTICS}
    var_exit_tactic = tk.StringVar()
    var_fallback_tactic = tk.StringVar()
    var_signal_ttl = tk.StringVar()
    var_missing_policy = tk.StringVar()
    var_tp_policy = tk.StringVar()
    var_sl_source = tk.StringVar()
    var_use_rr_tp = tk.BooleanVar()
    var_tp_rr = tk.StringVar()
    var_use_swing_tp = tk.BooleanVar()
    var_swing_group = tk.StringVar()
    var_swing_max_atr = tk.StringVar()
    var_swing_reject = tk.BooleanVar()
    var_fib_group = tk.StringVar()
    var_fib_entry = tk.StringVar()
    var_fib_tp = tk.StringVar()
    var_fib_use_tp = tk.BooleanVar()
    var_pull_source = tk.StringVar()
    var_pull_max_atr = tk.StringVar()

    def load_into_form(next_cfg):
        next_cfg = merge_cfg(default_entry_exit_config(), next_cfg)
        active = set(next_cfg.get("active_tactics", []))
        var_enabled.set(bool(next_cfg.get("enabled", False)))
        var_preview_only.set(bool(next_cfg.get("preview_only", True)))
        for key, var in tactic_vars.items():
            var.set(key in active)
        entry_active = set(next_cfg.get("entry_tactics", ["SWING_REJECTION"]))
        for key, var in entry_tactic_vars.items():
            var.set(key in entry_active)
        var_exit_tactic.set(next_cfg.get("exit_tactic", "FIB_RETRACE"))
        var_fallback_tactic.set(next_cfg.get("fallback_tactic", "FALLBACK_R"))
        var_signal_ttl.set(str(next_cfg.get("signal_ttl_seconds", 900)))
        var_missing_policy.set(next_cfg.get("missing_data_policy", "FALLBACK_R"))
        var_tp_policy.set(next_cfg.get("tp_policy", "FALLBACK_R"))
        var_sl_source.set(next_cfg.get("sl_source_group", "BASE_SL"))
        default_exit = next_cfg.get("default_exit", {})
        var_use_rr_tp.set(bool(default_exit.get("use_rr_tp", True)))
        var_tp_rr.set(str(default_exit.get("tp_rr_ratio", 1.5)))
        var_use_swing_tp.set(bool(default_exit.get("use_swing_tp", False)))
        swing = next_cfg.get("swing_rejection", {})
        var_swing_group.set(swing.get("source_group", "G2"))
        var_swing_max_atr.set(str(swing.get("max_atr_from_swing", 0.7)))
        var_swing_reject.set(bool(swing.get("require_rejection_candle", True)))
        fib = next_cfg.get("fib_retrace", {})
        var_fib_group.set(fib.get("swing_source_group", "G2"))
        var_fib_entry.set(fib.get("entry_levels", "0.5,0.618"))
        var_fib_tp.set(fib.get("tp_levels", "1.272,1.618"))
        var_fib_use_tp.set(bool(fib.get("use_tactic_tp", False)))
        pull = next_cfg.get("pullback_zone", {})
        var_pull_source.set(pull.get("source", "EMA20"))
        var_pull_max_atr.set(str(pull.get("max_atr_from_zone", 0.5)))

    def collect_form():
        try:
            tp_rr = float(var_tp_rr.get() or 1.5)
            swing_max_atr = float(var_swing_max_atr.get() or 0.7)
            pull_max_atr = float(var_pull_max_atr.get() or 0.5)
            signal_ttl = int(float(var_signal_ttl.get() or 900))
        except ValueError as exc:
            raise ValueError("Numeric Entry/Exit settings are invalid.") from exc

        active = [key for key, var in tactic_vars.items() if var.get()]
        entry_active = [key for key, var in entry_tactic_vars.items() if var.get()]
        return {
            "enabled": bool(var_enabled.get()) and bool(active),
            "preview_only": bool(var_preview_only.get()),
            "active_tactics": active,
            "entry_tactics": entry_active or ["SWING_REJECTION"],
            "exit_tactic": var_exit_tactic.get() or "FIB_RETRACE",
            "fallback_tactic": var_fallback_tactic.get() or "FALLBACK_R",
            "signal_ttl_seconds": signal_ttl,
            "missing_data_policy": var_missing_policy.get() or "FALLBACK_R",
            "tp_policy": var_tp_policy.get() or "FALLBACK_R",
            "sl_source_group": var_sl_source.get() or "BASE_SL",
            "default_exit": {
                "use_rr_tp": bool(var_use_rr_tp.get()),
                "tp_rr_ratio": tp_rr,
                "use_swing_tp": bool(var_use_swing_tp.get()),
            },
            "swing_rejection": {
                "source_group": var_swing_group.get() or "G2",
                "max_atr_from_swing": swing_max_atr,
                "require_rejection_candle": bool(var_swing_reject.get()),
            },
            "fib_retrace": {
                "swing_source_group": var_fib_group.get() or "G2",
                "entry_levels": var_fib_entry.get() or "0.5,0.618",
                "tp_levels": var_fib_tp.get() or "1.272,1.618",
                "use_tactic_tp": bool(var_fib_use_tp.get()),
            },
            "pullback_zone": {
                "source": var_pull_source.get() or "EMA20",
                "max_atr_from_zone": pull_max_atr,
            },
        }

    def _section(parent, title, color="#00B8D4"):
        frame = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=8)
        frame.pack(fill="x", padx=10, pady=8)
        ctk.CTkLabel(frame, text=title, font=("Roboto", 13, "bold"), text_color=color).grid(
            row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(8, 6)
        )
        return frame

    def _field(frame, row, label, variable, values=None, width=130, col=0):
        ctk.CTkLabel(frame, text=label).grid(row=row, column=col, sticky="w", padx=12, pady=5)
        if values:
            widget = ctk.CTkOptionMenu(frame, values=values, variable=variable, width=width)
        else:
            widget = ctk.CTkEntry(frame, textvariable=variable, width=width, justify="center")
        widget.grid(row=row, column=col + 1, sticky="w", padx=8, pady=5)
        return widget

    # Basic tab
    ctk.CTkLabel(
        tab_basic,
        text="ENTRY/EXIT MODE",
        font=("Roboto", 16, "bold"),
        text_color="#00B8D4",
    ).pack(pady=(4, 0))
    _hint(
        tab_basic,
        "- UI/config only: engine is not wired into bot/manual yet.\n"
        "- Basic keeps R and Swing easy to understand. Advanced contains FIB and PULL.\n"
        "- R means no entry gate; use fallback TP by R.",
    )
    f_master = _section(tab_basic, "MASTER")
    ctk.CTkCheckBox(
        f_master,
        text="Entry/Exit Mode ON",
        variable=var_enabled,
        font=("Roboto", 12, "bold"),
        text_color=COL_GREEN,
    ).grid(row=1, column=0, sticky="w", padx=12, pady=8)
    ctk.CTkCheckBox(
        f_master,
        text="Preview only",
        variable=var_preview_only,
        font=("Roboto", 12, "bold"),
        text_color=COL_WARN,
    ).grid(row=1, column=1, sticky="w", padx=12, pady=8)
    ctk.CTkCheckBox(f_master, text="R", variable=tactic_vars["FALLBACK_R"], width=90).grid(row=2, column=0, sticky="w", padx=12, pady=8)
    ctk.CTkCheckBox(f_master, text="SWING", variable=tactic_vars["SWING_REJECTION"], width=110).grid(row=2, column=1, sticky="w", padx=12, pady=8)
    ctk.CTkLabel(
        f_master,
        text="Entry tactics:",
        font=("Roboto", 11, "bold"),
        text_color="#D7DCE2",
    ).grid(row=3, column=0, sticky="w", padx=12, pady=(8, 2))
    ctk.CTkCheckBox(f_master, text="R", variable=entry_tactic_vars["FALLBACK_R"], width=90).grid(row=4, column=0, sticky="w", padx=12, pady=4)
    ctk.CTkCheckBox(f_master, text="SWING", variable=entry_tactic_vars["SWING_REJECTION"], width=110).grid(row=4, column=1, sticky="w", padx=12, pady=4)
    _field(f_master, 5, "Exit / TP Source:", var_exit_tactic, ["FIB_RETRACE", "SWING_REJECTION", "FALLBACK_R"], width=160)
    _field(f_master, 5, "Fallback:", var_fallback_tactic, ["FALLBACK_R"], width=130, col=2)
    _field(f_master, 6, "Signal TTL(s):", var_signal_ttl, width=90)
    _field(f_master, 6, "Missing Data:", var_missing_policy, ["FALLBACK_R", "BLOCK"], width=130, col=2)

    f_exit = _section(tab_basic, "DEFAULT EXIT / FALLBACK", "#FFD600")
    _field(f_exit, 1, "TP Policy:", var_tp_policy, ["FALLBACK_R", "BOT_DEFAULT", "TACTIC_FIRST", "TACTIC_ONLY"], width=150)
    _field(f_exit, 1, "SL Source:", var_sl_source, ["BASE_SL", "G0", "G1", "G2", "G3", "DYNAMIC-G1/G2"], width=150, col=2)
    ctk.CTkCheckBox(f_exit, text="Use R TP", variable=var_use_rr_tp).grid(row=2, column=0, sticky="w", padx=12, pady=8)
    _field(f_exit, 2, "TP R:", var_tp_rr, width=80, col=1)
    ctk.CTkCheckBox(f_exit, text="Use Swing TP", variable=var_use_swing_tp).grid(row=2, column=3, sticky="w", padx=12, pady=8)

    f_swing = _section(tab_basic, "SWING")
    _field(f_swing, 1, "Source Group:", var_swing_group, ["G0", "G1", "G2", "G3"], width=120)
    _field(f_swing, 1, "Max ATR:", var_swing_max_atr, width=90, col=2)
    ctk.CTkCheckBox(
        f_swing,
        text="Require rejection candle later",
        variable=var_swing_reject,
    ).grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=(4, 10))

    # Advanced tab
    _hint(tab_advanced, "- Advanced tactics stay disabled unless selected: FIB and PULL.")
    f_adv_tactics = _section(tab_advanced, "ADVANCED TACTICS")
    ctk.CTkCheckBox(f_adv_tactics, text="FIB", variable=tactic_vars["FIB_RETRACE"], width=90).grid(row=1, column=0, sticky="w", padx=12, pady=8)
    ctk.CTkCheckBox(f_adv_tactics, text="PULL", variable=tactic_vars["PULLBACK_ZONE"], width=90).grid(row=1, column=1, sticky="w", padx=12, pady=8)
    ctk.CTkLabel(
        f_adv_tactics,
        text="Use as entry gate:",
        font=("Roboto", 11, "bold"),
        text_color="#D7DCE2",
    ).grid(row=2, column=0, sticky="w", padx=12, pady=(4, 2))
    ctk.CTkCheckBox(f_adv_tactics, text="FIB Entry", variable=entry_tactic_vars["FIB_RETRACE"], width=110).grid(row=3, column=0, sticky="w", padx=12, pady=6)
    ctk.CTkCheckBox(f_adv_tactics, text="PULL Entry", variable=entry_tactic_vars["PULLBACK_ZONE"], width=120).grid(row=3, column=1, sticky="w", padx=12, pady=6)

    f_fib = _section(tab_advanced, "FIB")
    _field(f_fib, 1, "Swing Group:", var_fib_group, ["G0", "G1", "G2", "G3", "DYNAMIC-G1/G2"], width=150)
    _field(f_fib, 2, "Entry Levels:", var_fib_entry, width=130)
    _field(f_fib, 2, "TP Levels:", var_fib_tp, width=130, col=2)
    ctk.CTkCheckBox(f_fib, text="Use FIB TP later", variable=var_fib_use_tp).grid(row=3, column=0, columnspan=3, sticky="w", padx=12, pady=(4, 10))

    f_pull = _section(tab_advanced, "PULLBACK")
    _field(f_pull, 1, "Source:", var_pull_source, ["EMA20", "BB_MID", "SWING"], width=140)
    _field(f_pull, 1, "Max ATR:", var_pull_max_atr, width=90, col=2)

    # Overwrite tab
    _hint(
        tab_overwrite,
        "- Save current form as a symbol override when a symbol needs E/E settings different from Global.\n"
        "- Reset override returns that symbol to Global E/E.",
    )
    f_ow = _section(tab_overwrite, "SYMBOL OVERWRITE", "#FFD600")
    symbol_values = list(getattr(config, "COIN_LIST", []) or [getattr(config, "DEFAULT_SYMBOL", "ETHUSD")])
    var_ow_symbol = tk.StringVar(value=getattr(config, "UI_ACTIVE_SYMBOL", symbol_values[0]))
    _field(f_ow, 1, "Symbol:", var_ow_symbol, symbol_values, width=150)
    lbl_ow_status = ctk.CTkLabel(f_ow, text="", text_color="#B0BEC5")
    lbl_ow_status.grid(row=2, column=0, columnspan=4, sticky="w", padx=12, pady=5)

    def refresh_override_status():
        overrides = storage_manager.load_symbol_overrides()
        symbol = var_ow_symbol.get()
        has_override = bool(overrides.get(symbol, {}).get("entry_exit"))
        lbl_ow_status.configure(
            text=f"{symbol}: {'has Entry/Exit override' if has_override else 'using Global Entry/Exit'}",
            text_color=COL_WARN if has_override else "#B0BEC5",
        )

    def load_symbol_override():
        overrides = storage_manager.load_symbol_overrides()
        symbol = var_ow_symbol.get()
        raw = overrides.get(symbol, {}).get("entry_exit")
        if not raw:
            messagebox.showinfo("Entry/Exit", f"{symbol} has no Entry/Exit override.", parent=top)
            return
        load_into_form(raw)
        refresh_override_status()

    def save_symbol_override():
        try:
            next_cfg = collect_form()
        except ValueError as exc:
            messagebox.showerror("Entry/Exit", str(exc), parent=top)
            return
        overrides = storage_manager.load_symbol_overrides()
        symbol = var_ow_symbol.get()
        overrides.setdefault(symbol, {})["entry_exit"] = next_cfg
        storage_manager.save_symbol_overrides(overrides)
        refresh_override_status()
        refresh_override_overview()
        if hasattr(app, "log_message"):
            app.log_message(f"✅ Entry/Exit Override Saved for {symbol}.", target="bot")

    def reset_symbol_override():
        overrides = storage_manager.load_symbol_overrides()
        symbol = var_ow_symbol.get()
        if symbol in overrides and "entry_exit" in overrides[symbol]:
            overrides[symbol].pop("entry_exit", None)
            if not overrides[symbol]:
                overrides.pop(symbol, None)
            storage_manager.save_symbol_overrides(overrides)
        refresh_override_status()
        refresh_override_overview()
        if hasattr(app, "log_message"):
            app.log_message(f"✅ Entry/Exit Override Reset for {symbol}.", target="bot")

    ctk.CTkButton(f_ow, text="LOAD OVERRIDE", command=load_symbol_override, width=140).grid(row=3, column=0, padx=12, pady=10, sticky="w")
    ctk.CTkButton(f_ow, text="SAVE AS OVERRIDE", command=save_symbol_override, width=160, fg_color=COL_ACCENT, hover_color="#006064").grid(row=3, column=1, padx=8, pady=10, sticky="w")
    ctk.CTkButton(f_ow, text="RESET OVERRIDE", command=reset_symbol_override, width=150, fg_color="#B71C1C", hover_color="#7F0000").grid(row=3, column=2, padx=8, pady=10, sticky="w")

    f_overview = _section(tab_overwrite, "OVERRIDE OVERVIEW", "#00B8D4")
    ctk.CTkLabel(
        f_overview,
        text="Symbol",
        font=("Roboto", 11, "bold"),
        text_color="#D7DCE2",
    ).grid(row=1, column=0, sticky="w", padx=12, pady=(0, 4))
    ctk.CTkLabel(
        f_overview,
        text="Status",
        font=("Roboto", 11, "bold"),
        text_color="#D7DCE2",
    ).grid(row=1, column=1, sticky="w", padx=12, pady=(0, 4))
    f_overview_rows = ctk.CTkFrame(f_overview, fg_color="transparent")
    f_overview_rows.grid(row=2, column=0, columnspan=4, sticky="ew", padx=8, pady=(0, 8))

    def select_symbol(symbol, load_override=False):
        var_ow_symbol.set(symbol)
        refresh_override_status()
        if load_override:
            overrides = storage_manager.load_symbol_overrides()
            raw = overrides.get(symbol, {}).get("entry_exit")
            if raw:
                load_into_form(raw)

    def reset_symbol_override_for(symbol):
        overrides = storage_manager.load_symbol_overrides()
        if symbol in overrides and "entry_exit" in overrides[symbol]:
            overrides[symbol].pop("entry_exit", None)
            if not overrides[symbol]:
                overrides.pop(symbol, None)
            storage_manager.save_symbol_overrides(overrides)
        refresh_override_status()
        refresh_override_overview()
        if hasattr(app, "log_message"):
            app.log_message(f"Entry/Exit Override Reset for {symbol}.", target="bot")

    def refresh_override_overview():
        for child in f_overview_rows.winfo_children():
            child.destroy()

        overrides = storage_manager.load_symbol_overrides()
        for row, symbol in enumerate(symbol_values):
            has_override = bool(overrides.get(symbol, {}).get("entry_exit"))
            row_frame = ctk.CTkFrame(
                f_overview_rows,
                fg_color="#2F2A12" if has_override else "#242424",
                corner_radius=6,
            )
            row_frame.grid(row=row, column=0, sticky="ew", padx=2, pady=2)
            row_frame.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(
                row_frame,
                text=symbol,
                width=110,
                anchor="w",
                font=("Roboto", 12, "bold"),
                text_color="#FFFFFF",
            ).grid(row=0, column=0, sticky="w", padx=10, pady=6)
            ctk.CTkLabel(
                row_frame,
                text="OVERRIDE" if has_override else "GLOBAL",
                anchor="w",
                font=("Roboto", 11, "bold"),
                text_color=COL_WARN if has_override else "#B0BEC5",
            ).grid(row=0, column=1, sticky="w", padx=8, pady=6)
            ctk.CTkButton(
                row_frame,
                text="LOAD" if has_override else "SELECT",
                width=76,
                height=24,
                fg_color="#1f538d" if has_override else COL_GRAY_BTN,
                hover_color="#14375e" if has_override else "#616161",
                command=lambda s=symbol, h=has_override: select_symbol(s, h),
            ).grid(row=0, column=2, sticky="e", padx=(4, 6), pady=5)
            ctk.CTkButton(
                row_frame,
                text="RESET",
                width=70,
                height=24,
                fg_color="#B71C1C" if has_override else "#303030",
                hover_color="#7F0000" if has_override else "#303030",
                state="normal" if has_override else "disabled",
                command=lambda s=symbol: reset_symbol_override_for(s),
            ).grid(row=0, column=3, sticky="e", padx=(0, 6), pady=5)

    var_ow_symbol.trace_add("write", lambda *_: refresh_override_status())

    def save_global():
        try:
            next_cfg = collect_form()
        except ValueError as exc:
            messagebox.showerror("Entry/Exit", str(exc), parent=top)
            return
        _save_global_cfg(next_cfg)
        for key in app.entry_exit_tactic_states:
            app.entry_exit_tactic_states[key] = key in next_cfg.get("active_tactics", [])
        if hasattr(app, "update_entry_exit_buttons_ui"):
            app.update_entry_exit_buttons_ui()
        if hasattr(app, "log_message"):
            app.log_message("✅ Entry/Exit config saved.", target="bot")
        top.destroy()

    load_into_form(cfg)
    refresh_override_status()
    refresh_override_overview()

    ctk.CTkButton(
        top,
        text="SAVE GLOBAL ENTRY/EXIT",
        command=save_global,
        fg_color=COL_ACCENT,
        hover_color="#006064",
        height=38,
        font=("Roboto", 13, "bold"),
    ).pack(fill="x", padx=20, pady=(4, 12))
