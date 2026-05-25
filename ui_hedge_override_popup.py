# -*- coding: utf-8 -*-
"""Per-symbol HEDGE override popup."""

import customtkinter as ctk
from tkinter import messagebox

import config
from hedge.hedge_storage import load_hedge_settings, save_hedge_settings

COL_WARN = "#FFB300"


def _symbols():
    return list(getattr(config, "COIN_LIST", []) or [getattr(config, "DEFAULT_SYMBOL", "ETHUSD")])


def _base_cfg():
    cfg = load_hedge_settings()
    cfg.setdefault("SYMBOL_OVERRIDES", {})
    return cfg


def _effective_cfg(symbol):
    cfg = _base_cfg()
    eff = dict(cfg)
    override = cfg.get("SYMBOL_OVERRIDES", {}).get(symbol, {})
    if isinstance(override, dict):
        eff.update(override)
    return eff


def _has_override(symbol):
    cfg = _base_cfg()
    return bool(cfg.get("SYMBOL_OVERRIDES", {}).get(symbol))


def open_hedge_override_popup(app, symbol=None, on_close=None):
    if not symbol:
        cbo = getattr(app, "cbo_symbol", None)
        symbol = cbo.get() if cbo else getattr(config, "DEFAULT_SYMBOL", "ETHUSD")

    top = ctk.CTkToplevel(app)
    top.title("HEDGE Symbol Override")
    top.geometry("820x720")
    top.minsize(760, 620)
    top.attributes("-topmost", True)
    top.focus_force()
    top.grab_set()

    selected = ctk.StringVar(value=symbol)

    header = ctk.CTkFrame(top, fg_color="#202020")
    header.pack(fill="x", padx=12, pady=(12, 8))
    lbl_title = ctk.CTkLabel(header, text="", font=("Roboto", 16, "bold"), text_color="#CE93D8")
    lbl_title.pack(anchor="w", padx=12, pady=(10, 4))
    ctk.CTkLabel(
        header,
        text="Override = cấu hình riêng cho từng symbol. Không có override thì symbol dùng cấu hình mặc định HEDGE.",
        font=("Arial", 12, "italic"),
        text_color="#F8BBD0",
        wraplength=760,
        justify="left",
    ).pack(anchor="w", padx=12, pady=(0, 10))

    body = ctk.CTkFrame(top, fg_color="transparent")
    body.pack(fill="both", expand=True, padx=12, pady=(0, 8))
    body.grid_columnconfigure(1, weight=1)
    body.grid_rowconfigure(0, weight=1)

    list_frame = ctk.CTkScrollableFrame(body, width=210, fg_color="#1E1E1E")
    list_frame.grid(row=0, column=0, sticky="nsw", padx=(0, 10))
    edit_frame = ctk.CTkScrollableFrame(body, fg_color="#242424")
    edit_frame.grid(row=0, column=1, sticky="nsew")

    fields = {}
    checks = {}

    def entry(label, key, row, col, width=120):
        ctk.CTkLabel(edit_frame, text=label).grid(row=row, column=col, sticky="w", padx=12, pady=6)
        e = ctk.CTkEntry(edit_frame, width=width, justify="center")
        e.grid(row=row, column=col + 1, sticky="w", padx=12, pady=6)
        fields[key] = e
        return e

    def set_entry(key, value):
        fields[key].delete(0, "end")
        fields[key].insert(0, str(value))

    ctk.CTkLabel(edit_frame, text="Cấu hình riêng", font=("Roboto", 14, "bold"), text_color="#CE93D8").grid(row=0, column=0, columnspan=4, sticky="w", padx=12, pady=(12, 8))
    ctk.CTkLabel(edit_frame, text="Tactic").grid(row=1, column=0, sticky="w", padx=12, pady=6)
    cbo_tactic = ctk.CTkOptionMenu(edit_frame, values=["BASKET", "LEG_OUT"], width=150)
    cbo_tactic.grid(row=1, column=1, sticky="w", padx=12, pady=6)
    checks["USE_SIGNAL_FILTER"] = ctk.BooleanVar(value=False)
    checks["USE_SWING_FILTER"] = ctk.BooleanVar(value=True)
    ctk.CTkCheckBox(edit_frame, text="Dùng signal filter", variable=checks["USE_SIGNAL_FILTER"]).grid(row=1, column=2, sticky="w", padx=12, pady=6)
    ctk.CTkCheckBox(edit_frame, text="Dùng swing filter", variable=checks["USE_SWING_FILTER"]).grid(row=1, column=3, sticky="w", padx=12, pady=6)

    entry("Lot mỗi chân", "FIXED_LOT", 2, 0)
    entry("Max pairs/symbol", "MAX_PAIRS_PER_SYMBOL", 2, 2)
    entry("Basket TP USD", "PAIR_TP_USD", 3, 0)
    entry("Basket SL USD", "PAIR_SL_USD", 3, 2)
    entry("Leg-out SL USD", "LOSING_LEG_SL_USD", 4, 0)
    entry("Recovery target", "RECOVERY_TARGET_USD", 4, 2)
    entry("Recovery giveback", "RECOVERY_GIVEBACK_USD", 5, 0)
    entry("Cooldown sau đóng", "COOLDOWN_AFTER_CLOSE_SECONDS", 6, 0)
    entry("Cooldown sau thua", "COOLDOWN_AFTER_LOSS_SECONDS", 6, 2)
    entry("Thua liên tiếp", "MAX_CONSECUTIVE_LOSSES", 7, 0)
    entry("Cooldown tổng", "GLOBAL_COOLDOWN_SECONDS", 7, 2)
    entry("Swing tolerance ATR", "SWING_TOLERANCE_ATR", 8, 0)

    ctk.CTkLabel(edit_frame, text="Nguồn swing").grid(row=8, column=2, sticky="w", padx=12, pady=6)
    cbo_group = ctk.CTkOptionMenu(edit_frame, values=["G0", "G1", "G2", "G3"], width=110)
    cbo_group.grid(row=8, column=3, sticky="w", padx=12, pady=6)
    ctk.CTkLabel(edit_frame, text="Khung nến HEDGE").grid(row=9, column=0, sticky="w", padx=12, pady=6)
    cbo_tf = ctk.CTkOptionMenu(edit_frame, values=["1m", "5m", "15m", "30m", "1h", "4h", "1d"], width=110)
    cbo_tf.grid(row=9, column=1, sticky="w", padx=12, pady=6)

    status_label = ctk.CTkLabel(edit_frame, text="", text_color="#F8BBD0", font=("Arial", 12, "italic"), wraplength=560, justify="left")
    status_label.grid(row=10, column=0, columnspan=4, sticky="w", padx=12, pady=(8, 4))

    def refresh_symbol_list():
        for child in list_frame.winfo_children():
            child.destroy()
        for sym in _symbols():
            active = sym == selected.get()
            has = _has_override(sym)
            label = f"{sym} *" if has else sym
            ctk.CTkButton(
                list_frame,
                text=label,
                height=30,
                fg_color=COL_WARN if has else ("#1f538d" if active else "#424242"),
                hover_color="#FFB300" if has else "#616161",
                text_color="#212121" if has else "#FFFFFF",
                command=lambda s=sym: load_symbol(s),
            ).pack(fill="x", padx=6, pady=4)

    def load_symbol(sym):
        selected.set(sym)
        cfg = _effective_cfg(sym)
        lbl_title.configure(text=f"HEDGE override: {sym} {'*' if _has_override(sym) else ''}")
        cbo_tactic.set(str(cfg.get("TACTIC", "BASKET")).upper())
        checks["USE_SIGNAL_FILTER"].set(bool(cfg.get("USE_SIGNAL_FILTER", False)))
        checks["USE_SWING_FILTER"].set(bool(cfg.get("USE_SWING_FILTER", True)))
        for key in fields:
            set_entry(key, cfg.get(key, ""))
        cbo_group.set(str(cfg.get("SWING_GROUP", "G2")).upper())
        cbo_tf.set(str(cfg.get("SWING_TIMEFRAME", "15m")))
        status_label.configure(
            text=(
                "Trạng thái: đang dùng cấu hình riêng cho symbol này."
                if _has_override(sym)
                else "Trạng thái: chưa có override, đang hiển thị mặc định HEDGE để làm mẫu."
            )
        )
        refresh_symbol_list()

    def values_from_form():
        return {
            "TACTIC": cbo_tactic.get(),
            "USE_SIGNAL_FILTER": checks["USE_SIGNAL_FILTER"].get(),
            "USE_SWING_FILTER": checks["USE_SWING_FILTER"].get(),
            "FIXED_LOT": float(fields["FIXED_LOT"].get() or 0.1),
            "MAX_PAIRS_PER_SYMBOL": int(float(fields["MAX_PAIRS_PER_SYMBOL"].get() or 1)),
            "PAIR_TP_USD": float(fields["PAIR_TP_USD"].get() or 0.0),
            "PAIR_SL_USD": float(fields["PAIR_SL_USD"].get() or 0.0),
            "LOSING_LEG_SL_USD": float(fields["LOSING_LEG_SL_USD"].get() or 0.0),
            "RECOVERY_TARGET_USD": float(fields["RECOVERY_TARGET_USD"].get() or 0.0),
            "RECOVERY_GIVEBACK_USD": float(fields["RECOVERY_GIVEBACK_USD"].get() or 0.0),
            "COOLDOWN_AFTER_CLOSE_SECONDS": int(float(fields["COOLDOWN_AFTER_CLOSE_SECONDS"].get() or 0)),
            "COOLDOWN_AFTER_LOSS_SECONDS": int(float(fields["COOLDOWN_AFTER_LOSS_SECONDS"].get() or 0)),
            "MAX_CONSECUTIVE_LOSSES": int(float(fields["MAX_CONSECUTIVE_LOSSES"].get() or 0)),
            "GLOBAL_COOLDOWN_SECONDS": int(float(fields["GLOBAL_COOLDOWN_SECONDS"].get() or 0)),
            "SWING_TOLERANCE_ATR": float(fields["SWING_TOLERANCE_ATR"].get() or 0.2),
            "SWING_GROUP": cbo_group.get(),
            "SWING_TIMEFRAME": cbo_tf.get(),
        }

    def save_override():
        try:
            cfg = _base_cfg()
            sym = selected.get()
            cfg.setdefault("SYMBOL_OVERRIDES", {})[sym] = values_from_form()
            save_hedge_settings(cfg)
            if hasattr(app, "log_message"):
                app.log_message(f"[HEDGE] Override saved for {sym}.", target="hedge")
            load_symbol(sym)
            if on_close:
                on_close()
        except ValueError:
            messagebox.showerror("HEDGE", "Cấu hình override sai kiểu số.", parent=top)

    def reset_override():
        cfg = _base_cfg()
        sym = selected.get()
        cfg.setdefault("SYMBOL_OVERRIDES", {}).pop(sym, None)
        save_hedge_settings(cfg)
        if hasattr(app, "log_message"):
            app.log_message(f"[HEDGE] Override reset for {sym}.", target="hedge")
        load_symbol(sym)
        if on_close:
            on_close()

    button_row = ctk.CTkFrame(top, fg_color="transparent")
    button_row.pack(fill="x", padx=12, pady=(0, 12))
    ctk.CTkButton(button_row, text="LƯU OVERRIDE SYMBOL", fg_color="#7B1FA2", hover_color="#4A148C", height=38, command=save_override).pack(side="left", fill="x", expand=True, padx=(0, 6))
    ctk.CTkButton(button_row, text="RESET VỀ MẶC ĐỊNH", fg_color="#B71C1C", hover_color="#7F0000", height=38, command=reset_override).pack(side="left", fill="x", expand=True, padx=(6, 0))

    load_symbol(symbol)
