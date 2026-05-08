# -*- coding: utf-8 -*-
"""Default GRID settings and identity constants."""

GRID_COMMENT_PREFIX = "[GRID]"
GRID_ENTRY_COMMENT = "[GRID]_ENTRY"
GRID_CHILD_COMMENT = "[GRID]_CHILD"
GRID_LOG_PREFIX = "[GRID]"

GRID_SETTINGS_FILE = "grid_settings.json"
GRID_STATE_FILE = "grid_state.json"

DEFAULT_GRID_SETTINGS = {
    "ENABLED": False,
    "WATCHLIST": [],
    "SIGNAL_SOURCE": "SANDBOX",
    "DYNAMIC_MODE_ENABLED": True,
    "NONE_POLICY": "NEUTRAL",
    "DEFAULT_MANUAL_MODE": "NEUTRAL",
    "MANUAL_BYPASS_SIGNAL": False,
    "GRID_TIMEFRAME_GROUP": "G2",
    "TREND_FILTER_GROUP": "G1",
    "BOUNDARY_MODE": "HYBRID",
    "MANUAL_UPPER_BOUNDARY": 0.0,
    "MANUAL_LOWER_BOUNDARY": 0.0,
    "SPACING_ATR_MULTIPLIER": 1.0,
    "TAKE_PROFIT_SPACING_MULTIPLIER": 0.8,
    "FIXED_LOT": 0.01,
    "MAX_GRID_ORDERS": 5,
    "MAX_TOTAL_LOT": 0.05,
    "MAX_BASKET_DRAWDOWN": 20.0,
    "MAX_BASKET_DRAWDOWN_UNIT": "USD",
    "CHECK_PING": True,
    "MAX_PING_MS": 150,
    "CHECK_SPREAD": True,
    "MAX_SPREAD_POINTS": 150,
    "COOLDOWN_SECONDS": 60,
    "LEVEL_REUSE": True,
    "REOPEN_COOLDOWN_SECONDS": 60,
    "STOP_ON_BREAKOUT": True,
    "STOP_NEW_MARKET_MODES": ["TREND", "BREAKOUT"],
    "GRID_SIGNAL_CONFIG": {},
    "NOTES": "GRID V1 test execution. Market orders only.",
}

DEFAULT_GRID_STATE = {
    "active_sessions": {},
    "grid_baskets": {},
    "grid_child_to_parent": {},
    "last_grid_action_times": {},
    "cooldown_until": {},
    "level_reopen_counts": {},
    "last_preview": {},
    "grid_active_tickets": [],
}


def is_grid_comment(comment: str) -> bool:
    return GRID_COMMENT_PREFIX in str(comment or "")


def is_grid_position(pos, grid_magic=None) -> bool:
    if pos is None:
        return False
    if grid_magic is not None and getattr(pos, "magic", None) == grid_magic:
        return True
    return is_grid_comment(getattr(pos, "comment", ""))
