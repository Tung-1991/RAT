# -*- coding: utf-8 -*-
"""Default HEDGE Dual settings and identity constants."""

HEDGE_COMMENT_PREFIX = "[HEDGE]"
HEDGE_BUY_COMMENT = "HEDGE_BUY"
HEDGE_SELL_COMMENT = "HEDGE_SELL"

HEDGE_SETTINGS_FILE = "hedge_settings.json"
HEDGE_STATE_FILE = "hedge_state.json"

DEFAULT_HEDGE_SETTINGS = {
    "ENABLED": False,
    "HEDGE_SCAN_INTERVAL_SECONDS": 2,
    "WATCHLIST": [],
    "TACTIC": "BASKET",
    "USE_SIGNAL_FILTER": False,
    "USE_SWING_FILTER": True,
    "SWING_GROUP": "G2",
    "SWING_TIMEFRAME": "15m",
    "SWING_TOLERANCE_ATR": 0.2,
    "FIXED_LOT": 0.1,
    "SYMBOL_OVERRIDES": {},
    "MAX_PAIRS_PER_SYMBOL": 1,
    "PAIR_TP_USD": 5.0,
    "PAIR_SL_USD": 10.0,
    "LOSING_LEG_SL_USD": 5.0,
    "RECOVERY_TARGET_USD": 2.0,
    "RECOVERY_GIVEBACK_USD": 2.0,
    "NO_MOVE_TIMEOUT_SECONDS": 300,
    "NO_MOVE_MIN_MFE_USD": 1.0,
    "MAX_HOLD_SECONDS": 1800,
    "COOLDOWN_AFTER_CLOSE_SECONDS": 900,
    "COOLDOWN_AFTER_LOSS_SECONDS": 1800,
    "MAX_CONSECUTIVE_LOSSES": 3,
    "GLOBAL_COOLDOWN_SECONDS": 3600,
    "MAX_SESSIONS_PER_DAY": 0,
    "HEDGE_MAX_DAILY_LOSS": 0.0,
    "CHECK_PING": True,
    "MAX_PING_MS": 150,
    "CHECK_SPREAD": True,
    "MAX_SPREAD_POINTS": 150,
}

DEFAULT_HEDGE_STATE = {
    "active_sessions": {},
    "last_decision": {},
    "last_decision_log_keys": {},
    "last_close_times": {},
    "last_loss_times": {},
    "global_cooldown_until": 0.0,
    "consecutive_losses": 0,
    "hedge_active_tickets": [],
    "date": "",
    "hedge_pnl_today": 0.0,
    "hedge_sessions_today": 0,
    "hedge_daily_loss_count": 0,
}


def is_hedge_comment(comment: str) -> bool:
    comment = str(comment or "")
    return HEDGE_COMMENT_PREFIX in comment or comment.startswith("HEDGE_")
