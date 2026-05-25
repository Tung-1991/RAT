# -*- coding: utf-8 -*-

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.modules.setdefault(
    "MetaTrader5",
    SimpleNamespace(
        ORDER_TYPE_BUY=0,
        ORDER_TYPE_SELL=1,
        TRADE_RETCODE_DONE=10009,
        terminal_info=lambda: SimpleNamespace(ping_last=0),
        symbol_info_tick=lambda symbol: None,
        symbol_info=lambda symbol: None,
        last_error=lambda: (0, ""),
    ),
)

from hedge.hedge_manager import HedgeManager


class HedgeManagerCoreTests(unittest.TestCase):
    def setUp(self):
        self.manager = HedgeManager()

    def test_entry_gate_all_filters_off_is_ready(self):
        settings = {"USE_SIGNAL_FILTER": False, "USE_SWING_FILTER": False, "TACTIC": "BASKET"}
        gate = self.manager.evaluate_entry_gate("ETHUSD", {}, settings)
        self.assertTrue(gate["permission"])
        self.assertEqual(gate["reason"], "OK")
        self.assertEqual(gate["signal_status"], "OFF")
        self.assertEqual(gate["swing_status"], "OFF")

    def test_signal_filter_blocks_none_signal(self):
        settings = {"USE_SIGNAL_FILTER": True, "USE_SWING_FILTER": False}
        gate = self.manager.evaluate_entry_gate("ETHUSD", {"latest_signal": 0}, settings)
        self.assertFalse(gate["permission"])
        self.assertEqual(gate["reason"], "SIGNAL_NONE")

    def test_swing_filter_passes_near_swing(self):
        settings = {
            "USE_SIGNAL_FILTER": False,
            "USE_SWING_FILTER": True,
            "SWING_GROUP": "G2",
            "SWING_TOLERANCE_ATR": 0.2,
        }
        context = {"current_price": 100.1, "swing_low_G2": 100.0, "swing_high_G2": 110.0, "atr_G2": 1.0}
        gate = self.manager.evaluate_entry_gate("ETHUSD", context, settings)
        self.assertTrue(gate["permission"])
        self.assertEqual(gate["swing_status"], "PASS")
        self.assertEqual(gate["nearest_swing"], "LOW")

    def test_swing_filter_blocks_far_price(self):
        settings = {
            "USE_SIGNAL_FILTER": False,
            "USE_SWING_FILTER": True,
            "SWING_GROUP": "G2",
            "SWING_TOLERANCE_ATR": 0.2,
        }
        context = {"current_price": 105.0, "swing_low_G2": 100.0, "swing_high_G2": 110.0, "atr_G2": 1.0}
        gate = self.manager.evaluate_entry_gate("ETHUSD", context, settings)
        self.assertFalse(gate["permission"])
        self.assertEqual(gate["reason"], "SWING_NOT_NEAR")

    def test_symbol_override_replaces_global(self):
        settings = {
            "FIXED_LOT": 0.1,
            "TACTIC": "BASKET",
            "SYMBOL_OVERRIDES": {"BTCUSD": {"FIXED_LOT": 0.2, "TACTIC": "LEG_OUT"}},
        }
        cfg = self.manager.settings_for_symbol("BTCUSD", settings)
        self.assertEqual(cfg["FIXED_LOT"], 0.2)
        self.assertEqual(cfg["TACTIC"], "LEG_OUT")

    def test_second_leg_fail_closes_first_leg(self):
        state = {
            "active_sessions": {},
            "last_decision": {},
            "last_decision_log_keys": {},
            "last_close_times": {},
            "date": "",
            "hedge_pnl_today": 0.0,
            "hedge_sessions_today": 0,
            "hedge_daily_loss_count": 0,
        }
        settings = {
            "USE_SIGNAL_FILTER": False,
            "USE_SWING_FILTER": False,
            "FIXED_LOT": 0.1,
            "MAX_PAIRS_PER_SYMBOL": 1,
            "COOLDOWN_AFTER_CLOSE_SECONDS": 0,
            "CHECK_PING": False,
            "CHECK_SPREAD": False,
        }
        first_pos = SimpleNamespace(ticket=101, symbol="ETHUSD", magic=55, comment="HEDGE_BUY")
        self.manager.connector = SimpleNamespace(_is_connected=True, get_all_open_positions=lambda: [first_pos])
        self.manager.executor = SimpleNamespace(calls=0, closed=[])

        def fake_place(*args, **kwargs):
            self.manager.executor.calls += 1
            return "SUCCESS|101" if self.manager.executor.calls == 1 else "HEDGE_FAIL|SECOND"

        def fake_close(pos, reason):
            self.manager.executor.closed.append((pos.ticket, reason))
            return "SUCCESS|101"

        self.manager.executor.place_hedge_leg = fake_place
        self.manager.executor.close_position = fake_close

        with patch("hedge.hedge_manager.load_hedge_settings", return_value=settings), \
             patch("hedge.hedge_manager.load_hedge_state", return_value=state), \
             patch("hedge.hedge_manager.save_hedge_state") as save, \
             patch("hedge.hedge_manager.get_magic_numbers", return_value={"hedge_magic": 55}), \
             patch("hedge.hedge_manager.is_symbol_trade_window_open", return_value=(True, "OK")):
            result = self.manager.start_manual_session("ETHUSD", {})

        self.assertIn("PAIR_OPEN_FAILED", result)
        self.assertEqual(self.manager.executor.closed, [(101, "PAIR_FAIL")])
        self.assertEqual(save.call_args.args[0]["hedge_sessions_today"], 0)

    def test_daily_loss_guard_blocks_new_pair(self):
        state = {
            "active_sessions": {},
            "last_decision": {},
            "last_decision_log_keys": {},
            "date": "",
            "hedge_pnl_today": -12.0,
            "hedge_sessions_today": 0,
            "hedge_daily_loss_count": 1,
        }
        settings = {"HEDGE_MAX_DAILY_LOSS": 10.0, "USE_SIGNAL_FILTER": False, "USE_SWING_FILTER": False}
        with patch("hedge.hedge_manager.get_today_str", return_value=""):
            self.manager._ensure_hedge_state(state)
            result = self.manager._start_pair_session("ETHUSD", {}, settings, state, source="AUTO")
        self.assertEqual(result, "HEDGE_BLOCK|HEDGE_DAILY_LOSS")
        self.assertEqual(state["last_decision"]["ETHUSD"]["reason"], "HEDGE_DAILY_LOSS")

    def test_scan_auto_starts_from_watchlist(self):
        state = {
            "active_sessions": {},
            "last_decision": {},
            "last_decision_log_keys": {},
            "last_close_times": {},
            "date": "",
            "hedge_pnl_today": 0.0,
            "hedge_sessions_today": 0,
            "hedge_daily_loss_count": 0,
        }
        settings = {
            "ENABLED": True,
            "WATCHLIST": ["ETHUSD"],
            "USE_SIGNAL_FILTER": False,
            "USE_SWING_FILTER": False,
            "FIXED_LOT": 0.1,
            "MAX_PAIRS_PER_SYMBOL": 1,
            "COOLDOWN_AFTER_CLOSE_SECONDS": 0,
            "CHECK_PING": False,
            "CHECK_SPREAD": False,
        }
        opened = []
        self.manager.connector = SimpleNamespace(_is_connected=True, get_all_open_positions=lambda: opened)
        self.manager.executor = SimpleNamespace(calls=0)

        def fake_place(*args, **kwargs):
            self.manager.executor.calls += 1
            ticket = 100 + self.manager.executor.calls
            comment = "HEDGE_BUY" if self.manager.executor.calls == 1 else "HEDGE_SELL"
            opened.append(SimpleNamespace(ticket=ticket, symbol="ETHUSD", magic=55, comment=comment, profit=0.0, swap=0.0, commission=0.0))
            return f"SUCCESS|{ticket}"

        self.manager.executor.place_hedge_leg = fake_place

        with patch("hedge.hedge_manager.load_hedge_settings", return_value=settings), \
             patch("hedge.hedge_manager.load_hedge_state", return_value=state), \
             patch("hedge.hedge_manager.save_hedge_state") as save, \
             patch("hedge.hedge_manager.get_magic_numbers", return_value={"hedge_magic": 55}), \
             patch("hedge.hedge_manager.is_symbol_trade_window_open", return_value=(True, "OK")):
            result = self.manager.scan(["ETHUSD"], {"ETHUSD": {}})

        saved_state = save.call_args.args[0]
        self.assertIn("HEDGE_OPEN|ETHUSD|AUTO", result["actions"])
        self.assertEqual(saved_state["active_sessions"]["ETHUSD"]["source"], "AUTO")

    def test_daily_reset_uses_storage_today(self):
        state = {
            "date": "old",
            "hedge_pnl_today": -9.0,
            "hedge_sessions_today": 3,
            "hedge_daily_loss_count": 2,
        }
        with patch("hedge.hedge_manager.get_today_str", return_value="2026-05-25"):
            self.manager._ensure_hedge_state(state)
        self.assertEqual(state["date"], "2026-05-25")
        self.assertEqual(state["hedge_pnl_today"], 0.0)
        self.assertEqual(state["hedge_sessions_today"], 0)
        self.assertEqual(state["hedge_daily_loss_count"], 0)


if __name__ == "__main__":
    unittest.main()
