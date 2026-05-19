# -*- coding: utf-8 -*-

import unittest
import sys
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import patch


sys.modules.setdefault(
    "MetaTrader5",
    SimpleNamespace(
        DEAL_ENTRY_OUT=1,
        DEAL_ENTRY_IN=0,
        DEAL_TYPE_SELL=1,
        terminal_info=lambda: SimpleNamespace(ping_last=0),
        symbol_info_tick=lambda symbol: None,
        symbol_info=lambda symbol: None,
        history_deals_get=lambda position=None: [],
        history_orders_get=lambda position=None: [],
    ),
)

from grid.grid_manager import GridManager


class GridManagerCoreTests(unittest.TestCase):
    def setUp(self):
        self.manager = GridManager()

    def test_arithmetic_spacing(self):
        settings = {"GRID_TYPE": "ARITHMETIC", "GRID_COUNT": 10}
        boundary = {"lower": 100.0, "upper": 110.0}
        self.assertEqual(self.manager._resolve_spacing({}, settings, boundary), 1.0)

    def test_geometric_spacing(self):
        settings = {"GRID_TYPE": "GEOMETRIC", "GEOMETRIC_STEP_PERCENT": 1.0}
        self.assertEqual(self.manager._resolve_spacing({"current_price": 200.0}, settings), 2.0)

    def test_atr_spacing(self):
        settings = {"GRID_TYPE": "ATR_DYNAMIC", "GRID_TIMEFRAME_GROUP": "G2", "SPACING_ATR_MULTIPLIER": 2.0}
        self.assertEqual(self.manager._resolve_spacing({"atr_G2": 3.0}, settings), 6.0)

    def test_signal_source_off_uses_default_mode(self):
        settings = {
            "GRID_SIGNAL_SOURCE": "OFF",
            "DEFAULT_MANUAL_MODE": "SHORT",
            "BOUNDARY_MODE": "MANUAL",
            "MANUAL_LOWER_BOUNDARY": 100.0,
            "MANUAL_UPPER_BOUNDARY": 110.0,
            "GRID_TYPE": "ARITHMETIC",
            "GRID_COUNT": 10,
            "STOP_ON_BREAKOUT": False,
        }
        result = self.manager._evaluate_gate("X", {"current_price": 105.0, "latest_signal": 1}, settings)
        self.assertTrue(result["permission"])
        self.assertEqual(result["mode"], "SHORT")

    def test_signal_source_context_uses_latest_signal(self):
        settings = {
            "GRID_SIGNAL_SOURCE": "CONTEXT",
            "BOUNDARY_MODE": "MANUAL",
            "MANUAL_LOWER_BOUNDARY": 100.0,
            "MANUAL_UPPER_BOUNDARY": 110.0,
            "GRID_TYPE": "ARITHMETIC",
            "GRID_COUNT": 10,
            "STOP_ON_BREAKOUT": False,
        }
        result = self.manager._evaluate_gate("X", {"current_price": 105.0, "latest_signal": 1}, settings)
        self.assertTrue(result["permission"])
        self.assertEqual(result["mode"], "LONG")

    def test_signal_source_imported_uses_grid_signal(self):
        settings = {
            "GRID_SIGNAL_SOURCE": "IMPORTED",
            "BOUNDARY_MODE": "MANUAL",
            "MANUAL_LOWER_BOUNDARY": 100.0,
            "MANUAL_UPPER_BOUNDARY": 110.0,
            "GRID_TYPE": "ARITHMETIC",
            "GRID_COUNT": 10,
            "STOP_ON_BREAKOUT": False,
        }
        result = self.manager._evaluate_gate(
            "X",
            {"current_price": 105.0, "latest_signal": 1, "grid_latest_signal": -1},
            settings,
        )
        self.assertTrue(result["permission"])
        self.assertEqual(result["mode"], "SHORT")

    def test_clear_block_keeps_daily_counters(self):
        state = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "grid_pnl_today": -12.5,
            "grid_trades_today": 7,
            "grid_daily_loss_count": 2,
            "last_decision": {"X": {"status": "BLOCK", "reason": "MAX_GRID_ORDERS"}},
            "active_sessions": {
                "X": {
                    "status": "STOP_NEW",
                    "stop_reason": "MAX_GRID_ORDERS",
                    "last_block_reason": "MAX_GRID_ORDERS",
                }
            },
        }
        with patch("grid.grid_manager.load_grid_state", return_value=state), patch("grid.grid_manager.save_grid_state") as save:
            self.manager.clear_session_block("X")

        saved = save.call_args.args[0]
        self.assertEqual(saved["grid_pnl_today"], -12.5)
        self.assertEqual(saved["grid_trades_today"], 7)
        self.assertEqual(saved["grid_daily_loss_count"], 2)
        self.assertEqual(saved["active_sessions"]["X"]["status"], "ACTIVE")
        self.assertNotIn("X", saved["last_decision"])


if __name__ == "__main__":
    unittest.main()
