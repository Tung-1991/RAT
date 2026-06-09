# -*- coding: utf-8 -*-
import time


def _as_float(value, default=0.0):
    try:
        return float(value or default)
    except Exception:
        return default


def evaluate(state=None, connector=None):
    state = state or {}
    now = time.time()
    reasons = []

    cooldown_until = _as_float(state.get("cooldown_until"), 0.0)
    if cooldown_until > now:
        reasons.append("cooldown_active")

    active_brake = state.get("active_brake") or {}
    if isinstance(active_brake, dict):
        if active_brake.get("global"):
            reasons.append("safeguard_global_active")
        symbols = active_brake.get("symbols") or {}
        if any(symbols.values()):
            reasons.append("safeguard_symbol_active")

    starting_balance = _as_float(state.get("starting_balance"), 0.0)
    bot_pnl = _as_float(state.get("bot_pnl_today"), 0.0)
    max_loss_pct = 0.0
    try:
        import core.storage_manager as storage_manager

        brain = storage_manager.get_brain_settings_for_symbol()
        max_loss_pct = _as_float(brain.get("bot_safeguard", {}).get("MAX_DAILY_LOSS_PERCENT"), 0.0)
        max_streak = int(brain.get("bot_safeguard", {}).get("MAX_LOSING_STREAK", 0) or 0)
    except Exception:
        max_streak = 0

    if starting_balance > 0 and max_loss_pct > 0:
        loss_pct = bot_pnl / starting_balance * 100.0
        if loss_pct <= -abs(max_loss_pct):
            reasons.append("daily_loss_threshold")

    if max_streak > 0 and int(state.get("bot_losing_streak", 0) or 0) >= max_streak:
        reasons.append("losing_streak_threshold")

    try:
        parent_baskets = state.get("parent_baskets") or {}
        if parent_baskets and connector:
            positions = connector.get_all_open_positions() or []
            pos_by_ticket = {str(getattr(p, "ticket", "")): p for p in positions}
            for parent, children in parent_baskets.items():
                tickets = [str(parent)] + [str(c) for c in children]
                basket_pnl = sum(_as_float(getattr(pos_by_ticket.get(t), "profit", 0.0)) for t in tickets)
                if basket_pnl < 0:
                    reasons.append("basket_loss_active")
                    break
    except Exception:
        reasons.append("basket_loss_data_warning")

    return sorted(set(reasons))
