# -*- coding: utf-8 -*-
import time


def default_entry_exit_config():
    return {
        "enabled": False,
        "preview_only": True,
        "active_tactics": [],
        "entry_tactics": ["SWING_REJECTION"],
        "exit_tactic": "AUTO",
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
            "require_rejection_candle": False,
        },
        "fib_retrace": {
            "swing_source_group": "G2",
            "entry_levels": "0.5,0.618",
            "entry_tolerance_atr": 0.15,
            "tp_levels": "1.272,1.618",
            "use_tactic_tp": True,
        },
        "pullback_zone": {
            "source": "EMA20",
            "max_atr_from_zone": 0.5,
            "sl_atr_buffer": 0.2,
            "tp_atr_multiplier": 1.5,
        },
    }


def merge_config(cfg):
    base = default_entry_exit_config()
    if isinstance(cfg, dict):
        _merge_dict(base, cfg)
    return base


def format_decision(decision):
    status = decision.get("status", "OFF")
    entry = _short_mode(decision.get("entry_tactic", "OFF"))
    zone = decision.get("entry_zone")
    sl = decision.get("sl")
    tp = decision.get("tp")
    reason = decision.get("reason", "")
    if status == "OFF":
        return "E/E: OFF"
    parts = [f"E/E: {status} {entry}"]
    if zone:
        parts.append(f"{decision.get('direction', '')} {zone[0]:.2f}-{zone[1]:.2f}")
    if sl:
        parts.append(f"SL {sl:.2f}")
    if tp:
        parts.append(f"TP {tp:.2f}")
    if reason:
        parts.append(reason)
    return " | ".join(parts)


def evaluate_entry_exit(symbol, direction, price, context, cfg, pending=None):
    cfg = merge_config(cfg)
    direction = str(direction or "").upper()
    now = time.time()
    ttl = max(1, int(float(cfg.get("signal_ttl_seconds", 900) or 900)))

    if not cfg.get("enabled") or not cfg.get("active_tactics"):
        return _decision("OFF", symbol, direction, price, reason="Entry/Exit disabled")

    context = context or {}
    entry_tactics = cfg.get("entry_tactics") or cfg.get("active_tactics") or ["SWING_REJECTION"]
    entry_tactics = [t for t in entry_tactics if t in cfg.get("active_tactics", []) or t == "FALLBACK_R"]
    if not entry_tactics:
        entry_tactics = cfg.get("active_tactics") or ["FALLBACK_R"]

    errors = []
    for tactic in entry_tactics:
        if tactic == "FALLBACK_R":
            entry_decision = _fallback_r_entry(symbol, direction, price, cfg, ttl, now)
        elif tactic == "SWING_REJECTION":
            entry_decision = _swing_entry(symbol, direction, price, context, cfg, ttl, now)
        elif tactic == "FIB_RETRACE":
            entry_decision = _fib_entry(symbol, direction, price, context, cfg, ttl, now)
        elif tactic == "PULLBACK_ZONE":
            entry_decision = _pull_entry(symbol, direction, price, context, cfg, ttl, now)
        else:
            continue

        if entry_decision["status"] in ("READY", "WAIT"):
            _apply_exit(entry_decision, price, context, cfg)
            return entry_decision
        errors.append(entry_decision.get("reason", tactic))

    if _allow_missing_fallback(cfg):
        decision = _fallback_r_entry(symbol, direction, price, cfg, ttl, now)
        decision["reason"] = "Missing E/E data, fallback R"
        _apply_exit(decision, price, context, cfg)
        return decision

    return _decision(
        "ERROR",
        symbol,
        direction,
        price,
        reason="; ".join(errors) if errors else "No E/E tactic available",
        expires_at=now + ttl,
    )


def _swing_entry(symbol, direction, price, context, cfg, ttl, now):
    sw = cfg.get("swing_rejection", {})
    group = _resolve_group(sw.get("source_group", "G2"), context)
    sh, sl, atr = _swing_values(context, group)
    if not _positive(sh) or not _positive(sl) or not _positive(atr):
        return _missing(symbol, direction, price, "SWING_REJECTION", f"Missing swing/ATR {group}", cfg, ttl, now)
    max_atr = float(sw.get("max_atr_from_swing", 0.7) or 0.7)
    sl_buffer = float(sw.get("sl_atr_buffer", 0.2) or 0.2)
    if direction == "BUY":
        zone = (float(sl), float(sl) + float(atr) * max_atr)
        status = "READY" if zone[0] <= price <= zone[1] else "WAIT"
        stop = float(sl) - float(atr) * sl_buffer
    else:
        zone = (float(sh) - float(atr) * max_atr, float(sh))
        status = "READY" if zone[0] <= price <= zone[1] else "WAIT"
        stop = float(sh) + float(atr) * sl_buffer
    return _decision(
        status,
        symbol,
        direction,
        price,
        entry_tactic="SWING_REJECTION",
        entry_zone=zone,
        sl=stop,
        sl_source=f"SWING_{group}",
        reason="Price in swing zone" if status == "READY" else "Waiting for swing pullback",
        expires_at=now + ttl,
    )


def _fib_entry(symbol, direction, price, context, cfg, ttl, now):
    fib = cfg.get("fib_retrace", {})
    group = _resolve_group(fib.get("swing_source_group", "G2"), context)
    sh, sl, atr = _swing_values(context, group)
    if not _positive(sh) or not _positive(sl) or not _positive(atr):
        return _missing(symbol, direction, price, "FIB_RETRACE", f"Missing fib swing/ATR {group}", cfg, ttl, now)
    levels = _parse_levels(fib.get("entry_levels", "0.5,0.618"), [0.5, 0.618])
    leg = abs(float(sh) - float(sl))
    if leg <= 0:
        return _missing(symbol, direction, price, "FIB_RETRACE", "Invalid fib leg", cfg, ttl, now)
    if direction == "BUY":
        vals = [float(sh) - leg * lvl for lvl in levels]
        zone = (min(vals), max(vals))
        stop = float(sl) - float(atr) * float(fib.get("entry_tolerance_atr", 0.15) or 0.15)
    else:
        vals = [float(sl) + leg * lvl for lvl in levels]
        zone = (min(vals), max(vals))
        stop = float(sh) + float(atr) * float(fib.get("entry_tolerance_atr", 0.15) or 0.15)
    status = "READY" if zone[0] <= price <= zone[1] else "WAIT"
    return _decision(
        status,
        symbol,
        direction,
        price,
        entry_tactic="FIB_RETRACE",
        entry_zone=zone,
        sl=stop,
        sl_source=f"FIB_{group}",
        reason="Price in fib zone" if status == "READY" else "Waiting for fib retrace",
        expires_at=now + ttl,
    )


def _pull_entry(symbol, direction, price, context, cfg, ttl, now):
    pull = cfg.get("pullback_zone", {})
    group = _resolve_group(cfg.get("sl_source_group", "G2"), context)
    atr = context.get(f"atr_{group}") or context.get("atr_entry")
    if not _positive(atr):
        return _missing(symbol, direction, price, "PULLBACK_ZONE", f"Missing ATR {group}", cfg, ttl, now)
    source = str(pull.get("source", "EMA20")).upper()
    zone_mid = None
    if source == "SWING":
        sh, sl, _ = _swing_values(context, group)
        zone_mid = sl if direction == "BUY" else sh
    elif source == "BB_MID":
        zone_mid = context.get(f"bb_mid_{group}") or context.get("bb_mid")
    else:
        zone_mid = context.get(f"ema20_{group}") or context.get("ema20") or context.get(f"EMA_20_{group}")
    if not _positive(zone_mid):
        return _missing(symbol, direction, price, "PULLBACK_ZONE", f"Missing pullback source {source}", cfg, ttl, now)
    dist = float(atr) * float(pull.get("max_atr_from_zone", 0.5) or 0.5)
    zone = (float(zone_mid) - dist, float(zone_mid) + dist)
    status = "READY" if zone[0] <= price <= zone[1] else "WAIT"
    sl_buffer = float(pull.get("sl_atr_buffer", 0.2) or 0.2)
    stop = zone[0] - float(atr) * sl_buffer if direction == "BUY" else zone[1] + float(atr) * sl_buffer
    return _decision(
        status,
        symbol,
        direction,
        price,
        entry_tactic="PULLBACK_ZONE",
        entry_zone=zone,
        sl=stop,
        sl_source=f"PULL_{source}",
        reason="Price in pullback zone" if status == "READY" else "Waiting for pullback zone",
        expires_at=now + ttl,
    )


def _fallback_r_entry(symbol, direction, price, cfg, ttl, now):
    return _decision(
        "READY",
        symbol,
        direction,
        price,
        entry_tactic="FALLBACK_R",
        reason="Fallback R entry",
        expires_at=now + ttl,
    )


def _apply_exit(decision, price, context, cfg):
    sl = decision.get("sl")
    exit_tactic = cfg.get("exit_tactic") or "AUTO"
    if exit_tactic == "AUTO":
        exit_tactic = _auto_exit_tactic(decision.get("entry_tactic"))
    decision["exit_tactic"] = exit_tactic
    if exit_tactic == "FIB_RETRACE":
        tp = _fib_tp(decision.get("direction"), context, cfg)
        if tp:
            decision["tp"] = tp
            decision["tp_source"] = "FIB"
        else:
            _apply_r_tp(decision, price, cfg)
    elif exit_tactic == "SWING_REJECTION":
        tp = _swing_tp(decision.get("direction"), context, cfg)
        if tp:
            decision["tp"] = tp
            decision["tp_source"] = "SWING"
        else:
            _apply_r_tp(decision, price, cfg)
    elif exit_tactic == "PULLBACK_ZONE":
        tp = _pullback_tp(decision.get("direction"), price, context, cfg)
        if tp:
            decision["tp"] = tp
            decision["tp_source"] = "PULLBACK"
        else:
            _apply_r_tp(decision, price, cfg)
    else:
        _apply_r_tp(decision, price, cfg)
    if sl:
        decision["risk_distance"] = abs(float(price) - float(sl))


def _auto_exit_tactic(entry_tactic):
    if entry_tactic in ("SWING_REJECTION", "FIB_RETRACE", "PULLBACK_ZONE"):
        return entry_tactic
    return "FALLBACK_R"


def _fib_tp(direction, context, cfg):
    fib = cfg.get("fib_retrace", {})
    group = _resolve_group(fib.get("swing_source_group", "G2"), context)
    sh, sl, _ = _swing_values(context, group)
    if not _positive(sh) or not _positive(sl):
        return None
    levels = _parse_levels(fib.get("tp_levels", "1.272,1.618"), [1.272, 1.618])
    level = max(levels) if levels else 1.272
    leg = abs(float(sh) - float(sl))
    if leg <= 0:
        return None
    return float(sl) + leg * level if direction == "BUY" else float(sh) - leg * level


def _swing_tp(direction, context, cfg):
    group = _resolve_group(cfg.get("sl_source_group", "G2"), context)
    sh, sl, atr = _swing_values(context, group)
    if not _positive(sh) or not _positive(sl):
        return None
    buffer = float(atr or 0) * float(cfg.get("swing_rejection", {}).get("sl_atr_buffer", 0.2) or 0.2)
    return float(sh) - buffer if direction == "BUY" else float(sl) + buffer


def _pullback_tp(direction, price, context, cfg):
    pull = cfg.get("pullback_zone", {})
    group = _resolve_group(cfg.get("sl_source_group", "G2"), context)
    atr = context.get(f"atr_{group}") or context.get("atr_entry")
    if not _positive(atr):
        return None
    mult = float(pull.get("tp_atr_multiplier", 1.5) or 1.5)
    return float(price) + float(atr) * mult if direction == "BUY" else float(price) - float(atr) * mult


def _apply_r_tp(decision, price, cfg):
    sl = decision.get("sl")
    if not sl:
        return
    rr = float(cfg.get("default_exit", {}).get("tp_rr_ratio", 1.5) or 1.5)
    dist = abs(float(price) - float(sl))
    decision["tp"] = float(price) + dist * rr if decision.get("direction") == "BUY" else float(price) - dist * rr
    decision["tp_source"] = "R"


def _missing(symbol, direction, price, tactic, reason, cfg, ttl, now):
    if _allow_missing_fallback(cfg):
        return _fallback_r_entry(symbol, direction, price, cfg, ttl, now)
    return _decision("ERROR", symbol, direction, price, entry_tactic=tactic, reason=reason, expires_at=now + ttl)


def _allow_missing_fallback(cfg):
    return str(cfg.get("missing_data_policy", "FALLBACK_R")).upper() == "FALLBACK_R"


def _swing_values(context, group):
    return (
        context.get(f"swing_high_{group}"),
        context.get(f"swing_low_{group}"),
        context.get(f"atr_{group}"),
    )


def _resolve_group(group, context):
    if not group:
        return "G2"
    group = str(group)
    if "DYNAMIC" in group:
        market_mode = (context or {}).get("market_mode", "ANY")
        return "G1" if market_mode in ("TREND", "BREAKOUT") else "G2"
    if group == "BASE_SL":
        return "G2"
    return group


def _parse_levels(raw, default):
    try:
        if isinstance(raw, (int, float)):
            return [float(raw)]
        return [float(x.strip()) for x in str(raw).split(",") if x.strip()]
    except Exception:
        return default


def _positive(value):
    try:
        return value is not None and float(value) > 0
    except Exception:
        return False


def _decision(status, symbol, direction, price, **kwargs):
    data = {
        "status": status,
        "symbol": symbol,
        "direction": direction,
        "current_price": price,
        "entry_tactic": kwargs.pop("entry_tactic", "OFF"),
        "exit_tactic": kwargs.pop("exit_tactic", None),
        "entry_zone": kwargs.pop("entry_zone", None),
        "sl": kwargs.pop("sl", None),
        "tp": kwargs.pop("tp", None),
        "sl_source": kwargs.pop("sl_source", None),
        "tp_source": kwargs.pop("tp_source", None),
        "reason": kwargs.pop("reason", ""),
        "expires_at": kwargs.pop("expires_at", None),
    }
    data.update(kwargs)
    return data


def _short_mode(mode):
    return {
        "FALLBACK_R": "R",
        "SWING_REJECTION": "SWING",
        "FIB_RETRACE": "FIB",
        "PULLBACK_ZONE": "PULL",
    }.get(mode, mode or "OFF")


def _merge_dict(dst, src):
    if not isinstance(src, dict):
        return dst
    for key, val in src.items():
        if isinstance(val, dict) and isinstance(dst.get(key), dict):
            _merge_dict(dst[key], val)
        else:
            dst[key] = val
    return dst
