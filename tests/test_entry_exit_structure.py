# -*- coding: utf-8 -*-
import unittest

import pandas as pd

from core.entry_exit_engine import evaluate_entry_exit, format_decision
from core.market_structure import analyze_market_structure


class MarketStructureTests(unittest.TestCase):
    def test_detects_up_structure_hh_hl(self):
        df = pd.DataFrame(
            {
                "high": [10, 12, 11, 14, 13, 16, 15],
                "low": [9, 10, 8, 11, 10, 12, 11],
                "close": [9.5, 11, 9, 13, 11, 15, 12],
            }
        )
        ms = analyze_market_structure(df, lookback=20, strength=1)
        self.assertEqual(ms["bias"], "UP")
        self.assertEqual(ms["high_label"], "HH")
        self.assertEqual(ms["low_label"], "HL")

    def test_detects_down_structure_lh_ll(self):
        df = pd.DataFrame(
            {
                "high": [14, 16, 13, 15, 12, 14, 11],
                "low": [13, 14, 12, 13, 11, 12, 10],
                "close": [13.5, 15, 12.5, 14, 11.5, 13, 10.5],
            }
        )
        ms = analyze_market_structure(df, lookback=20, strength=1)
        self.assertEqual(ms["bias"], "DOWN")
        self.assertEqual(ms["high_label"], "LH")
        self.assertEqual(ms["low_label"], "LL")

    def test_unknown_when_not_enough_pivots(self):
        df = pd.DataFrame({"high": [1, 2, 3], "low": [1, 1, 2], "close": [1, 2, 3]})
        ms = analyze_market_structure(df, lookback=20, strength=2)
        self.assertEqual(ms["bias"], "UNKNOWN")


class EntryExitStructureTests(unittest.TestCase):
    def test_wait_retest_does_not_block_fib_ready(self):
        cfg = {
            "enabled": True,
            "active_tactics": ["SWING_REJECTION", "FIB_RETRACE"],
            "entry_tactics": ["SWING_REJECTION", "FIB_RETRACE"],
            "missing_data_policy": "BLOCK",
            "sl_mode": "SANDBOX",
            "exit_tactic": "AUTO",
            "swing_rejection": {"source_group": "G2", "max_atr_from_swing": 0.7, "sl_atr_buffer": 0.2},
            "fib_retrace": {"swing_source_group": "G2", "entry_levels": "0.5,0.618", "entry_tolerance_atr": 0.15},
        }
        ctx = {"swing_high_G2": 100.0, "swing_low_G2": 80.0, "atr_G2": 10.0}
        decision = evaluate_entry_exit("TEST", "SELL", 91.0, ctx, cfg)
        self.assertEqual(decision["status"], "READY")
        self.assertEqual(decision["entry_tactic"], "FIB_RETRACE")
        self.assertEqual(decision["sl_source"], "SANDBOX")
        self.assertIsNone(decision.get("sl"))

    def test_fallback_r_runs_after_structured_modes(self):
        cfg = {
            "enabled": True,
            "active_tactics": ["FALLBACK_R", "FIB_RETRACE"],
            "entry_tactics": ["FALLBACK_R", "FIB_RETRACE"],
            "missing_data_policy": "BLOCK",
            "sl_mode": "AUTO",
            "exit_tactic": "AUTO",
            "fib_retrace": {"swing_source_group": "G2", "entry_levels": "0.5,0.618", "entry_tolerance_atr": 0.15},
        }
        ctx = {"swing_high_G2": 100.0, "swing_low_G2": 80.0, "atr_G2": 10.0}
        decision = evaluate_entry_exit("TEST", "SELL", 91.0, ctx, cfg)
        self.assertEqual(decision["status"], "READY")
        self.assertEqual(decision["entry_tactic"], "FIB_RETRACE")
        self.assertEqual(decision["sl_source"], "FIB_G2")

    def test_swing_structure_sell_ready_uses_lh_sl(self):
        cfg = {
            "enabled": True,
            "active_tactics": ["SWING_STRUCTURE"],
            "entry_tactics": ["SWING_STRUCTURE"],
            "missing_data_policy": "BLOCK",
            "sl_mode": "SWING_STRUCTURE",
            "exit_tactic": "AUTO",
            "swing_structure": {"source_group": "G2", "entry_atr": 0.7, "sl_atr_buffer": 0.2},
        }
        ctx = {
            "atr_G2": 10.0,
            "ms_G2_bias": "DOWN",
            "ms_G2_lh": 100.0,
            "ms_G2_ll": 80.0,
        }
        decision = evaluate_entry_exit("TEST", "SELL", 95.0, ctx, cfg)
        self.assertEqual(decision["status"], "READY")
        self.assertEqual(decision["entry_tactic"], "SWING_STRUCTURE")
        self.assertAlmostEqual(decision["sl"], 102.0)

    def test_swing_structure_buy_ready_uses_hl_sl(self):
        cfg = {
            "enabled": True,
            "active_tactics": ["SWING_STRUCTURE"],
            "entry_tactics": ["SWING_STRUCTURE"],
            "missing_data_policy": "BLOCK",
            "sl_mode": "SWING_STRUCTURE",
            "exit_tactic": "AUTO",
            "swing_structure": {"source_group": "G2", "entry_atr": 0.7, "sl_atr_buffer": 0.2},
        }
        ctx = {
            "atr_G2": 10.0,
            "ms_G2_bias": "UP",
            "ms_G2_hl": 90.0,
            "ms_G2_hh": 110.0,
        }
        decision = evaluate_entry_exit("TEST", "BUY", 94.0, ctx, cfg)
        self.assertEqual(decision["status"], "READY")
        self.assertEqual(decision["entry_tactic"], "SWING_STRUCTURE")
        self.assertAlmostEqual(decision["sl"], 88.0)

    def test_swing_structure_missing_structure_is_wait_not_error(self):
        cfg = {
            "enabled": True,
            "active_tactics": ["SWING_STRUCTURE"],
            "entry_tactics": ["SWING_STRUCTURE"],
            "missing_data_policy": "BLOCK",
            "sl_mode": "SANDBOX",
            "exit_tactic": "AUTO",
            "swing_structure": {"source_group": "G2", "entry_atr": 0.7, "sl_atr_buffer": 0.2},
        }
        ctx = {"atr_G2": 10.0, "ms_G2_bias": "RANGE"}
        decision = evaluate_entry_exit("TEST", "SELL", 95.0, ctx, cfg)
        self.assertEqual(decision["status"], "WAIT")
        self.assertIn("Chờ DOWN structure", decision["reason"])

    def test_no_tp_exit_mode_disables_tp_override(self):
        cfg = {
            "enabled": True,
            "active_tactics": ["FALLBACK_R"],
            "entry_tactics": ["FALLBACK_R"],
            "missing_data_policy": "BLOCK",
            "sl_mode": "AUTO",
            "exit_tactic": "NO_TP",
        }
        decision = evaluate_entry_exit("TEST", "BUY", 100.0, {}, cfg)
        self.assertEqual(decision["status"], "READY")
        self.assertEqual(decision["exit_tactic"], "NO_TP")
        self.assertTrue(decision["tp_disabled"])
        self.assertEqual(decision["tp"], 0.0)
        self.assertEqual(decision["tp_source"], "OFF")
        self.assertIn("TP OFF", format_decision(decision))


if __name__ == "__main__":
    unittest.main()
