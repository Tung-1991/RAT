# -*- coding: utf-8 -*-
"""GRID settings popup."""

import customtkinter as ctk
from tkinter import messagebox

import config
from .grid_storage import load_grid_settings, load_grid_state, save_grid_settings, save_grid_state


COL_GRID = "#0097A7"
COL_PANEL = "#242424"
COL_HINT = "#80DEEA"
COL_TEXT = "#FFFFFF"
COL_MUTED = "#B0BEC5"
COL_READY = "#00C853"
COL_WAIT = "#FFB300"
COL_BLOCK = "#F44336"

STATUS_TEXT = {
    "READY": "SẴN SÀNG",
    "WAIT": "ĐANG CHỜ",
    "BLOCK": "ĐANG CHẶN",
    "OPEN": "ĐÃ VÀO LỆNH",
    "CLOSE": "ĐÃ ĐÓNG",
}

REASON_TEXT = {
    "No recent scan": "Chưa có lần quét gần nhất",
    "Missing range/spacing": "Thiếu vùng giá hoặc khoảng lưới",
    "Missing data": "Thiếu dữ liệu giá/range/ATR",
    "ORDER_READY": "Đủ điều kiện mở lệnh",
    "LEVEL_COOLDOWN": "Level vừa vào lệnh, đang cooldown",
    "LEVEL_ALREADY_OPEN": "Level này đã có lệnh mở",
    "NO_DIRECTION_FOR_MODE": "Giá chưa vào vùng hợp lệ của mode",
    "PRICE_OUT_OF_BOUNDARY": "Giá đang nằm ngoài vùng lưới",
    "MAX_GRID_ORDERS": "Đã chạm giới hạn số lệnh GRID",
    "MAX_GROSS_LOT": "Đã chạm giới hạn tổng lot",
    "MAX_SESSION_DD": "Basket đang âm quá ngưỡng",
    "GRID_DAILY_LOSS": "Lỗ ngày đã chạm ngưỡng",
    "GRID_MAX_TRADES_PER_DAY": "Đã chạm số lệnh tối đa trong ngày",
    "SIGNAL_NONE": "Signal không có hướng",
    "BASKET_TP": "Basket đạt TP",
    "BASKET_SL": "Basket chạm SL",
    "GRID_STOP_PRICE": "Giá chạm stop toàn GRID",
    "GRID_TAKE_PRICE": "Giá chạm take toàn GRID",
}


def _vn_status(status):
    return STATUS_TEXT.get(str(status or "").upper(), str(status or "---"))


def _vn_reason(reason):
    return REASON_TEXT.get(str(reason or ""), str(reason or "---"))


def _current_symbol(app):
    try:
        return app.cbo_symbol.get()
    except Exception:
        return getattr(config, "DEFAULT_SYMBOL", "")


def _entry(parent, label, value, row, col=0, width=110, hint=""):
    ctk.CTkLabel(parent, text=label, anchor="w", text_color=COL_TEXT, font=("Roboto", 14)).grid(
        row=row, column=col, sticky="w", padx=12, pady=8
    )
    var = ctk.StringVar(value=str(value))
    ctk.CTkEntry(textvariable=var, master=parent, width=width, justify="center", font=("Roboto", 14)).grid(
        row=row, column=col + 1, sticky="w", padx=12, pady=8
    )
    if hint:
        ctk.CTkLabel(
            parent,
            text=hint,
            text_color=COL_MUTED,
            font=("Arial", 13),
            anchor="w",
            justify="left",
            wraplength=640,
        ).grid(row=row, column=col + 2, sticky="w", padx=12, pady=8)
    return var


def _option(parent, label, values, value, row, col=0, width=170, hint=""):
    ctk.CTkLabel(parent, text=label, anchor="w", text_color=COL_TEXT, font=("Roboto", 14)).grid(
        row=row, column=col, sticky="w", padx=12, pady=8
    )
    opt = ctk.CTkOptionMenu(parent, values=values, width=width)
    opt.set(value if value in values else values[0])
    opt.grid(row=row, column=col + 1, sticky="w", padx=12, pady=8)
    if hint:
        ctk.CTkLabel(
            parent,
            text=hint,
            text_color=COL_MUTED,
            font=("Arial", 13),
            anchor="w",
            justify="left",
            wraplength=640,
        ).grid(row=row, column=col + 2, sticky="w", padx=12, pady=8)
    return opt


def _hint(parent, text):
    box = ctk.CTkFrame(parent, fg_color="#06262B", border_width=1, border_color=COL_GRID)
    box.pack(fill="x", padx=10, pady=10)
    ctk.CTkLabel(
        box,
        text=text,
        justify="left",
        anchor="w",
        wraplength=1100,
        text_color=COL_HINT,
        font=("Arial", 14, "italic"),
    ).pack(fill="x", padx=12, pady=10)


def _signal_summary(cfg):
    sig = cfg.get("GRID_SIGNAL_CONFIG") or {}
    inds = sig.get("indicators", {}) if isinstance(sig, dict) else {}
    groups = set()
    for ind_cfg in inds.values():
        if not isinstance(ind_cfg, dict):
            continue
        for grp in ind_cfg.get("groups", [ind_cfg.get("group", "")]):
            if grp:
                groups.add(str(grp))
    return {
        "imported": bool(sig),
        "indicators": len(inds),
        "eval": sig.get("MASTER_EVAL_MODE", "---") if sig else "---",
        "votes": sig.get("MIN_MATCHING_VOTES", "---") if sig else "---",
        "groups": ", ".join(sorted(groups)) if groups else "---",
    }


def _preview_data(cfg, state, app):
    symbol = _current_symbol(app)
    ctx = getattr(app, "latest_market_context", {}).get(symbol, {}) if symbol else {}
    price = float(ctx.get("current_price", 0.0) or 0.0)
    group = cfg.get("GRID_TIMEFRAME_GROUP", "G2")
    upper = float(cfg.get("MANUAL_UPPER_BOUNDARY", 0.0) or 0.0)
    lower = float(cfg.get("MANUAL_LOWER_BOUNDARY", 0.0) or 0.0)
    source = "Manual"
    if upper <= lower:
        upper = float(ctx.get(f"swing_high_{group}", ctx.get("swing_high")) or 0.0)
        lower = float(ctx.get(f"swing_low_{group}", ctx.get("swing_low")) or 0.0)
        source = f"Swing {group}"
    grid_type = cfg.get("GRID_TYPE", "ATR_DYNAMIC")
    spacing = 0.0
    if grid_type == "ARITHMETIC" and upper > lower:
        spacing = (upper - lower) / max(1, int(cfg.get("GRID_COUNT", 10) or 10))
    elif grid_type == "GEOMETRIC" and price > 0:
        spacing = price * (float(cfg.get("GEOMETRIC_STEP_PERCENT", 1.0) or 1.0) / 100.0)
    else:
        atr = float(ctx.get(f"atr_{group}", ctx.get("atr")) or 0.0)
        spacing = atr * float(cfg.get("SPACING_ATR_MULTIPLIER", 1.0) or 1.0)

    last = (state.get("last_decision") or {}).get(symbol) or {}
    status = last.get("status", "WAIT" if upper > lower and spacing > 0 else "BLOCK")
    reason = last.get("reason", "No recent scan" if upper > lower and spacing > 0 else "Missing range/spacing")
    color = COL_READY if status in ("READY", "OPEN") else (COL_WAIT if status == "WAIT" else COL_BLOCK)
    return {
        "symbol": symbol,
        "price": price,
        "lower": lower,
        "upper": upper,
        "source": source,
        "grid_type": grid_type,
        "spacing": spacing,
        "tp_distance": spacing * float(cfg.get("TAKE_PROFIT_SPACING_MULTIPLIER", 0.8) or 0.8) if spacing > 0 else 0.0,
        "status": status,
        "reason": reason,
        "reason_text": _vn_reason(reason),
        "color": color,
    }


def _set_card(label, value):
    try:
        label.configure(text=str(value))
    except Exception:
        pass


def open_grid_settings_popup(app):
    cfg = load_grid_settings()
    state = load_grid_state()

    top = ctk.CTkToplevel(app)
    top.title("Cài đặt GRID")
    top.geometry("1180x760")
    top.minsize(980, 680)
    top.attributes("-topmost", True)
    top.focus_force()
    top.grab_set()

    tabs = ctk.CTkTabview(top)
    tabs.pack(fill="both", expand=True, padx=12, pady=(10, 6))
    tab_preview = tabs.add("Tổng quan")
    tab_basic = tabs.add("Cơ bản")
    tab_safety = tabs.add("An toàn")
    tab_adv = tabs.add("Tín hiệu & Nâng cao")
    try:
        tabs._segmented_button.configure(text_color=COL_TEXT, text_color_disabled=COL_TEXT)
    except Exception:
        pass

    pdata = _preview_data(cfg, state, app)
    _hint(
        tab_preview,
        "Đèn trạng thái: xanh = đủ điều kiện vào lệnh; vàng = đang chờ giá/cooldown; đỏ = bị safety hoặc thiếu dữ liệu chặn. "
        "Preview chỉ để đọc nhanh, bấm START ở panel trade mới vào lệnh manual.",
    )
    preview = ctk.CTkFrame(tab_preview, fg_color=COL_PANEL, corner_radius=8)
    preview.pack(fill="x", padx=10, pady=10)
    lbl_status = ctk.CTkLabel(preview, text=_vn_status(pdata["status"]), font=("Roboto", 26, "bold"), text_color=pdata["color"])
    lbl_status.grid(row=0, column=0, padx=14, pady=(12, 4), sticky="w")
    lbl_reason = ctk.CTkLabel(preview, text=pdata["reason_text"], font=("Roboto", 13, "bold"), text_color=pdata["color"])
    lbl_reason.grid(row=0, column=1, padx=14, pady=(12, 4), sticky="w")
    rows = [
        ("Mã giao dịch", pdata["symbol"]),
        ("Giá hiện tại", f"{pdata['price']:.5f}" if pdata["price"] else "---"),
        ("Vùng lưới", f"{pdata['lower']:.5f} -> {pdata['upper']:.5f} ({pdata['source']})" if pdata["upper"] > pdata["lower"] else "---"),
        ("Kiểu lưới", pdata["grid_type"]),
        ("Khoảng lưới", f"{pdata['spacing']:.5f}" if pdata["spacing"] else "---"),
        ("TP mỗi lệnh", f"{pdata['tp_distance']:.5f}" if pdata["tp_distance"] else "---"),
        ("Hôm nay", f"PnL {float(state.get('grid_pnl_today', 0.0) or 0.0):+.2f} | Lệnh {int(state.get('grid_trades_today', 0) or 0)} | Lỗ {int(state.get('grid_daily_loss_count', 0) or 0)}"),
    ]
    for i, (k, v) in enumerate(rows, start=1):
        ctk.CTkLabel(preview, text=k, text_color=COL_TEXT, anchor="w", width=140, font=("Roboto", 12, "bold")).grid(row=i, column=0, padx=14, pady=5, sticky="w")
        ctk.CTkLabel(preview, text=v, text_color="#E0F7FA", anchor="w").grid(row=i, column=1, padx=14, pady=5, sticky="w")

    _hint(tab_basic, "NEUTRAL: mua vùng thấp, bán vùng cao. LONG: chỉ canh BUY ở vùng thấp. SHORT: chỉ canh SELL ở vùng cao.")
    enabled = ctk.BooleanVar(value=cfg.get("ENABLED", False))
    basic = ctk.CTkFrame(tab_basic, fg_color=COL_PANEL, corner_radius=8)
    basic.pack(fill="x", padx=10, pady=10)
    basic.grid_columnconfigure(2, weight=1)
    ctk.CTkLabel(
        basic,
        text="Tab này chỉ cấu hình chiến thuật. Bật/tắt Auto GRID nằm ở Advanced Tools -> GRID Control.",
        text_color=COL_HINT,
        font=("Arial", 14, "italic"),
        anchor="w",
        justify="left",
        wraplength=980,
    ).grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(10, 6))
    default_mode = _option(basic, "Mode mặc định:", ["NEUTRAL", "LONG", "SHORT"], cfg.get("DEFAULT_MANUAL_MODE", "NEUTRAL"), 1, hint="Auto GRID dùng mode này khi Signal Source = OFF. Manual thì dùng mode đang chọn ở panel trade.")
    grid_type = _option(basic, "Kiểu lưới:", ["ATR_DYNAMIC", "ARITHMETIC", "GEOMETRIC"], cfg.get("GRID_TYPE", "ATR_DYNAMIC"), 2, hint="ATR_DYNAMIC: co giãn theo biến động. ARITHMETIC: chia đều theo giá. GEOMETRIC: chia đều theo phần trăm.")
    boundary_mode = _option(basic, "Cách lấy vùng giá:", ["HYBRID", "AUTO_SWING", "MANUAL"], cfg.get("BOUNDARY_MODE", "HYBRID"), 4, hint="HYBRID: ưu tiên giá nhập tay, nếu trống thì dùng swing. AUTO_SWING: dùng swing. MANUAL: dùng giá nhập tay.")
    upper = _entry(basic, "Giá trên:", cfg.get("MANUAL_UPPER_BOUNDARY", 0.0), 5, hint="Nhập 0 nếu muốn lấy range tự động từ swing/context.")
    lower = _entry(basic, "Giá dưới:", cfg.get("MANUAL_LOWER_BOUNDARY", 0.0), 6, hint="Ví dụ ETH 2100-2150 thì giá dưới = 2100, giá trên = 2150.")
    fixed_lot = _entry(basic, "Lot mỗi lệnh:", cfg.get("FIXED_LOT", 0.01), 7, hint="V1 dùng lot cố định, không martingale.")
    tp_mult = _entry(basic, "TP mỗi lưới x:", cfg.get("TAKE_PROFIT_SPACING_MULTIPLIER", 0.8), 8, hint="Ví dụ 0.8 nghĩa là TP cách entry 0.8 lần khoảng lưới.")
    scan_interval = _entry(basic, "Chu kỳ quét Auto (giây):", cfg.get("GRID_SCAN_INTERVAL_SECONDS", 5), 9, hint="Manual START quét ngay; Auto GRID sẽ quét theo chu kỳ này.")
    ctk.CTkButton(basic, text="LƯU CÀI ĐẶT GRID", fg_color=COL_GRID, command=lambda: save()).grid(row=10, column=0, columnspan=3, sticky="ew", padx=12, pady=(14, 10))

    _hint(tab_safety, "Safety của GRID độc lập với BOT. Clear block chỉ xóa trạng thái STOP_NEW/block, không reset PnL hoặc số lệnh hôm nay.")
    safety = ctk.CTkFrame(tab_safety, fg_color=COL_PANEL, corner_radius=8)
    safety.pack(fill="x", padx=10, pady=10)
    safety.grid_columnconfigure(2, weight=1)
    max_orders = _entry(safety, "Số lệnh GRID tối đa:", cfg.get("MAX_GRID_ORDERS", 0), 0, hint="0 = không giới hạn. Nên để 3-10 khi test.")
    max_total_lot = _entry(safety, "Tổng lot tối đa:", cfg.get("MAX_TOTAL_LOT", 0.0), 1, hint="0 = không giới hạn. Ví dụ 0.05 nghĩa là tối đa 5 lệnh x 0.01 lot.")
    max_dd = _entry(safety, "Âm nổi tối đa:", cfg.get("MAX_BASKET_DRAWDOWN", 0.0), 2, hint="Nếu basket GRID âm vượt ngưỡng này thì dừng mở lệnh mới.")
    daily_loss = _entry(safety, "Lỗ ngày tối đa:", cfg.get("GRID_MAX_DAILY_LOSS", 0.0), 3, hint="0 = tắt. Tính theo PnL đã đóng của GRID trong ngày.")
    trades_day = _entry(safety, "Số lệnh/ngày tối đa:", cfg.get("GRID_MAX_TRADES_PER_DAY", 0), 4, hint="0 = không giới hạn số lệnh đã đóng trong ngày.")
    basket_tp = _entry(safety, "Basket TP USD:", cfg.get("BASKET_TP_USD", 0.0), 5, hint="0 = tắt. Đạt tổng lời nổi này thì đóng toàn bộ lệnh GRID của symbol.")
    basket_sl = _entry(safety, "Basket SL USD:", cfg.get("BASKET_SL_USD", 0.0), 6, hint="0 = tắt. Âm tới mức này thì đóng toàn bộ lệnh GRID của symbol.")
    stop_price = _entry(safety, "Giá stop toàn GRID:", cfg.get("GRID_STOP_LOSS_PRICE", 0.0), 7, hint="0 = tắt. Giá chạm mức này thì đóng basket GRID.")
    take_price = _entry(safety, "Giá take toàn GRID:", cfg.get("GRID_TAKE_PROFIT_PRICE", 0.0), 8, hint="0 = tắt. Giá chạm mức này thì đóng basket GRID.")

    def clear_grid_block():
        try:
            st = load_grid_state()
            for session in (st.get("active_sessions") or {}).values():
                if isinstance(session, dict):
                    if session.get("status") == "STOP_NEW":
                        session["status"] = "ACTIVE"
                    session.pop("stop_reason", None)
                    session.pop("last_block_reason", None)
            st["last_decision"] = {}
            save_grid_state(st)
            app.log_message("[GRID] Clear GRID block done.", target="grid")
            lbl_status.configure(text=_vn_status("WAIT"), text_color=COL_WAIT)
            lbl_reason.configure(text="Đã xóa block", text_color=COL_WAIT)
        except Exception as e:
            messagebox.showerror("GRID", f"Clear block failed: {e}", parent=top)

    ctk.CTkButton(safety, text="XÓA BLOCK GRID", fg_color="#455A64", command=clear_grid_block).grid(row=9, column=0, columnspan=2, sticky="ew", padx=10, pady=(12, 10))
    ctk.CTkButton(safety, text="LƯU CÀI ĐẶT GRID", fg_color=COL_GRID, command=lambda: save()).grid(row=9, column=2, sticky="ew", padx=10, pady=(12, 10))

    _hint(tab_adv, "Signal engine dùng chung với BOT/QUANT, nhưng GRID có config riêng. Import = copy rule hiện tại sang GRID; Clear = xóa signal GRID, GRID vẫn chạy bằng mode mặc định/chọn tay.")
    adv = ctk.CTkFrame(tab_adv, fg_color=COL_PANEL, corner_radius=8)
    adv.pack(fill="x", padx=10, pady=10)
    adv.grid_columnconfigure(2, weight=1)
    signal_source = _option(adv, "Nguồn signal:", ["OFF", "CONTEXT", "IMPORTED"], cfg.get("GRID_SIGNAL_SOURCE", "OFF"), 0, hint="OFF: không dùng signal. CONTEXT: dùng signal daemon có sẵn. IMPORTED: dùng GRID_SIGNAL_CONFIG riêng.")
    none_policy = _option(adv, "Khi signal NONE:", ["NEUTRAL", "BLOCK"], cfg.get("NONE_POLICY", "NEUTRAL"), 2, hint="NEUTRAL = vẫn đánh 2 chiều; BLOCK = không mở lệnh khi signal không rõ.")
    grid_group = _option(adv, "Nhóm timeframe GRID:", ["G0", "G1", "G2", "G3"], cfg.get("GRID_TIMEFRAME_GROUP", "G2"), 3, hint="GRID lấy swing/ATR từ group này. D1/M15 nếu cần thì cấu hình trong signal/group cũ.")
    atr_mult = _entry(adv, "ATR multiplier:", cfg.get("SPACING_ATR_MULTIPLIER", 1.0), 4, hint="Chỉ dùng cho ATR_DYNAMIC. Ví dụ ATR 5 và multiplier 1.2 thì khoảng lưới = 6.")
    grid_count = _entry(adv, "Grid count:", cfg.get("GRID_COUNT", 10), 5, hint="Chỉ dùng cho ARITHMETIC. Ví dụ range 100 giá, count 10 thì mỗi lưới cách 10 giá.")
    geo_step = _entry(adv, "Geometric step %:", cfg.get("GEOMETRIC_STEP_PERCENT", 1.0), 6, hint="Chỉ dùng cho GEOMETRIC. Ví dụ 1% tại giá 2000 thì khoảng lưới khoảng 20.")
    reopen_cd = _entry(adv, "Cooldown level (giây):", cfg.get("REOPEN_COOLDOWN_SECONDS", 60), 7)
    check_ping = ctk.BooleanVar(value=cfg.get("CHECK_PING", True))
    check_spread = ctk.BooleanVar(value=cfg.get("CHECK_SPREAD", True))
    stop_breakout = ctk.BooleanVar(value=cfg.get("STOP_ON_BREAKOUT", True))
    ctk.CTkCheckBox(adv, text="Chặn khi ping cao", variable=check_ping).grid(row=8, column=0, sticky="w", padx=10, pady=4)
    ctk.CTkCheckBox(adv, text="Chặn khi spread cao", variable=check_spread).grid(row=8, column=1, sticky="w", padx=10, pady=4)
    ctk.CTkCheckBox(adv, text="Dừng mở lệnh mới khi TREND/BREAKOUT", variable=stop_breakout).grid(row=9, column=0, columnspan=2, sticky="w", padx=10, pady=4)
    max_ping = _entry(adv, "Ping tối đa ms:", cfg.get("MAX_PING_MS", 150), 10)
    max_spread = _entry(adv, "Spread tối đa points:", cfg.get("MAX_SPREAD_POINTS", 150), 11)

    sig_summary = _signal_summary(cfg)
    lbl_sig = ctk.CTkLabel(adv, text=f"Signal: {'Đã import' if sig_summary['imported'] else 'Trống'} | Indicators: {sig_summary['indicators']} | Eval: {sig_summary['eval']} | Votes: {sig_summary['votes']} | Groups: {sig_summary['groups']}", text_color=COL_HINT, font=("Roboto", 12, "bold"))
    lbl_sig.grid(row=12, column=0, columnspan=2, sticky="w", padx=10, pady=(12, 4))

    def import_signal():
        try:
            brain = app.trade_mgr._get_brain_settings(_current_symbol(app))
            cfg["GRID_SIGNAL_CONFIG"] = {
                "MASTER_EVAL_MODE": brain.get("MASTER_EVAL_MODE"),
                "MIN_MATCHING_VOTES": brain.get("MIN_MATCHING_VOTES"),
                "voting_rules": brain.get("voting_rules", {}),
                "indicators": brain.get("indicators", {}),
            }
            cfg["GRID_SIGNAL_SOURCE"] = "IMPORTED"
            persisted = load_grid_settings()
            persisted["GRID_SIGNAL_CONFIG"] = cfg["GRID_SIGNAL_CONFIG"]
            persisted["GRID_SIGNAL_SOURCE"] = "IMPORTED"
            save_grid_settings(persisted)
            signal_source.set("IMPORTED")
            summary = _signal_summary(cfg)
            lbl_sig.configure(text=f"Signal: Đã import | Indicators: {summary['indicators']} | Eval: {summary['eval']} | Votes: {summary['votes']} | Groups: {summary['groups']}")
            app.log_message("[GRID] Imported signal config from BOT/QUANT.", target="grid-log")
        except Exception as e:
            messagebox.showerror("GRID", f"Import signal failed: {e}", parent=top)

    def clear_signal():
        cfg["GRID_SIGNAL_CONFIG"] = {}
        cfg["GRID_SIGNAL_SOURCE"] = "OFF"
        persisted = load_grid_settings()
        persisted["GRID_SIGNAL_CONFIG"] = {}
        persisted["GRID_SIGNAL_SOURCE"] = "OFF"
        save_grid_settings(persisted)
        signal_source.set("OFF")
        lbl_sig.configure(text="Signal: Trống | Indicators: 0 | Eval: --- | Votes: --- | Groups: ---")
        app.log_message("[GRID] Cleared GRID signal config.", target="grid-log")

    ctk.CTkButton(adv, text="IMPORT TỪ BOT/QUANT", fg_color="#1565C0", command=import_signal).grid(row=13, column=0, sticky="ew", padx=10, pady=(8, 10))
    ctk.CTkButton(adv, text="XÓA SIGNAL GRID", fg_color="#455A64", command=clear_signal).grid(row=13, column=1, sticky="ew", padx=10, pady=(8, 10))
    ctk.CTkButton(adv, text="LƯU CÀI ĐẶT GRID", fg_color=COL_GRID, command=lambda: save()).grid(row=13, column=2, sticky="ew", padx=10, pady=(8, 10))

    watch = ctk.CTkScrollableFrame(tab_adv, fg_color=COL_PANEL, height=150)
    watch.pack(fill="x", padx=10, pady=8)
    ctk.CTkLabel(watch, text="Danh sách mã Auto GRID", text_color=COL_TEXT, font=("Roboto", 13, "bold")).pack(anchor="w", padx=10, pady=8)
    current_watchlist = set(cfg.get("WATCHLIST", []) or [])
    coin_vars = {}
    coin_grid = ctk.CTkFrame(watch, fg_color="transparent")
    coin_grid.pack(fill="x", padx=8, pady=(0, 10))
    for i, coin in enumerate(getattr(config, "COIN_LIST", getattr(config, "SYMBOLS", []))):
        var = ctk.BooleanVar(value=(coin in current_watchlist))
        coin_vars[coin] = var
        ctk.CTkCheckBox(coin_grid, text=coin, variable=var, width=110).grid(row=i // 4, column=i % 4, sticky="w", padx=6, pady=4)

    def save():
        try:
            if enabled.get() and hasattr(app, "set_auto_trade_enabled"):
                app.set_auto_trade_enabled(False, reason="GRID_AUTO_ON")
            next_cfg = dict(cfg)
            next_cfg.update({
                "ENABLED": enabled.get(),
                "DYNAMIC_MODE_ENABLED": True,
                "GRID_SCAN_INTERVAL_SECONDS": float(scan_interval.get() or 5),
                "GRID_SIGNAL_SOURCE": signal_source.get(),
                "NONE_POLICY": none_policy.get(),
                "DEFAULT_MANUAL_MODE": default_mode.get(),
                "GRID_TIMEFRAME_GROUP": grid_group.get(),
                "BOUNDARY_MODE": boundary_mode.get(),
                "MANUAL_UPPER_BOUNDARY": float(upper.get() or 0.0),
                "MANUAL_LOWER_BOUNDARY": float(lower.get() or 0.0),
                "GRID_TYPE": grid_type.get(),
                "GRID_COUNT": int(grid_count.get() or 10),
                "GEOMETRIC_STEP_PERCENT": float(geo_step.get() or 1.0),
                "SPACING_ATR_MULTIPLIER": float(atr_mult.get() or 1.0),
                "FIXED_LOT": float(fixed_lot.get() or 0.01),
                "TAKE_PROFIT_SPACING_MULTIPLIER": float(tp_mult.get() or 0.8),
                "REOPEN_COOLDOWN_SECONDS": int(reopen_cd.get() or 60),
                "MAX_GRID_ORDERS": int(max_orders.get() or 0),
                "MAX_TOTAL_LOT": float(max_total_lot.get() or 0.0),
                "MAX_BASKET_DRAWDOWN": float(max_dd.get() or 0.0),
                "GRID_MAX_DAILY_LOSS": float(daily_loss.get() or 0.0),
                "GRID_MAX_TRADES_PER_DAY": int(trades_day.get() or 0),
                "BASKET_TP_USD": float(basket_tp.get() or 0.0),
                "BASKET_SL_USD": float(basket_sl.get() or 0.0),
                "GRID_STOP_LOSS_PRICE": float(stop_price.get() or 0.0),
                "GRID_TAKE_PROFIT_PRICE": float(take_price.get() or 0.0),
                "CHECK_PING": check_ping.get(),
                "MAX_PING_MS": int(max_ping.get() or 0),
                "CHECK_SPREAD": check_spread.get(),
                "MAX_SPREAD_POINTS": int(max_spread.get() or 0),
                "STOP_ON_BREAKOUT": stop_breakout.get(),
                "WATCHLIST": [coin for coin, var in coin_vars.items() if var.get()],
            })
            save_grid_settings(next_cfg)
            app.log_message("[GRID] Settings saved.", target="grid")
            top.destroy()
        except ValueError:
            messagebox.showerror("GRID", "Gia tri nhap vao khong hop le.", parent=top)

    ctk.CTkButton(top, text="LƯU CÀI ĐẶT GRID", fg_color=COL_GRID, hover_color="#006064", font=("Roboto", 13, "bold"), height=38, command=save).pack(fill="x", padx=24, pady=(4, 14))
