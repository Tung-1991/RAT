# -*- coding: utf-8 -*-
import json
import os

from . import config_snapshot, history, paths


USER_CONTEXT_TEMPLATE = """# RAT6 AI Advisor Context

## Bot overview
RAT6 is a trading bot/workstation with manual, bot, GRID, HEDGE, DCA/PCA, TSL, BE, BE_CASH, REV_C, safeguard, and multi-timeframe signal context.

## Current operating goal

## Acceptable drawdown

## Priority symbols

## Suspected module/rule

## Market context notes

## Things AI should not suggest

## Test notes
Examples: testing REV_C, BE_CASH, TSL, GRID, HEDGE, DCA/PCA.
"""

ADVISOR_FLOW_TEMPLATE = """# RAT6 AI Advisor Flow

This file explains how to read the advisor package without needing the full source code.

## Package reading order
1. Read this advisor_flow.md first.
2. Read user_context.md for the operator's current goal, risk preference, and question.
3. Read technical_settings.json for current config and raw runtime snapshots.
4. Read advisor_export.xlsx for trade evidence, summaries, events, and config changes.
5. If present and intentionally included, read previous_advisor_response.md only as prior advice, not as fact.

## Main files
- technical_settings.json: Machine-readable snapshot. It is not runtime config and must not be treated as an edit target.
- advisor_export.xlsx: Trade and event evidence for the selected export window.
- user_context.md: Human notes from the operator.
- advisor_response.md: Latest saved LLM response after Send API succeeds.

## Config layers
- config_py: Static/default values from config.py.
- active_global: Current global brain settings used by the bot.
- active_by_symbol: Effective merged settings per active symbol.
- raw_sources: Raw snapshots of source JSON/state files.

When the same key appears in multiple layers, prefer active_by_symbol for symbol-specific review, active_global for global review, and config_py only as default/background.

## Trading modes
- Manual: Operator-triggered orders using manual UI and manual magic/comment classification.
- Bot: Signal-driven automatic order flow using active strategy, checklist, safeguard, SL/TP, and lot rules.
- GRID: Grid module with its own settings/state and boundary/level logic.
- HEDGE: Hedge module with its own settings/state and basket/recovery logic.

## High-level order flow
1. Market data and indicators produce multi-timeframe context.
2. Signal groups G0/G1/G2/G3 are evaluated.
3. Safeguards/checklists can block entry.
4. Lot, SL, TP, tactic, and session metadata are resolved.
5. Order is sent to MT5 and trade-open snapshot is recorded.
6. Runtime modules manage open trades and write events/history.

## Timeframe groups
- G0: Macro/base timeframe, usually highest timeframe.
- G1: Trend/context timeframe.
- G2: Execution/swing timeframe, often used for SL/TP swing references.
- G3: Fast confirmation timeframe.

## Runtime modules
- TSL: Trailing stop layer.
- BE: Break-even stop behavior.
- BE_CASH: Cash/profit lock behavior.
- STEP_R: R-multiple step trailing.
- SWING: Swing-point based SL/TP or trailing logic.
- PSAR: Parabolic SAR trailing.
- REV_C: Reverse/recovery close logic.
- DCA: Adds/averages into losing basket by rule.
- PCA: Adds into winning/confirmed basket by rule.
- A.CUT or ANTI_CASH: Giveback/hard cash protection.
- Safeguard: Risk gate such as max loss, max orders, spread, ping, cooldown, losing streak.

## Advisor response rules
- Diagnose from evidence first: profit, fee, MAE/MFE, close reason, module tags, event payloads, and config changes.
- Separate facts from assumptions.
- Do not suggest automatic order placement.
- Do not ask the bot to edit config directly.
- If a key is unclear, explain which evidence was used instead of inventing behavior.
"""

ADVISOR_RESPONSE_TEMPLATE = """# RAT6 AI Advisor Response

No API response has been saved yet.

When Send API succeeds, this file will be replaced with the latest LLM response.
Historical copies are stored in the account history folder as advisor_response_*.md.
"""


def ensure_user_context():
    paths.ensure_advisor_dirs()
    path = paths.user_context_path()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(USER_CONTEXT_TEMPLATE)
    return path


def ensure_advisor_flow():
    paths.ensure_advisor_dirs()
    path = paths.advisor_flow_path()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(ADVISOR_FLOW_TEMPLATE)
    return path


def ensure_advisor_response_template():
    paths.ensure_advisor_dirs()
    path = paths.advisor_response_path()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(ADVISOR_RESPONSE_TEMPLATE)
    return path


def write_technical_settings(reason="manual_export"):
    snapshot = config_snapshot.build_technical_settings(reason=reason)
    path = paths.technical_settings_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)
    return path, snapshot.get("config_snapshot_id")


def generate_advisor_package(
    export_days=7,
    save_archive=False,
    connector=None,
    state=None,
    market_contexts=None,
    reason="manual_export",
):
    result = {
        "ok": False,
        "root": paths.advisor_root(),
        "technical_settings": paths.technical_settings_path(),
        "advisor_history": paths.history_path(),
        "advisor_export": paths.export_path(),
        "advisor_flow": paths.advisor_flow_path(),
        "user_context": paths.user_context_path(),
        "archive": None,
        "warnings": [],
    }
    try:
        paths.ensure_advisor_dirs()
        ensure_user_context()
        ensure_advisor_flow()
        ensure_advisor_response_template()
        tech_path, snapshot_id = write_technical_settings(reason=reason)
        history.ensure_config_snapshot(reason=reason)
        synced = history.sync_from_master_csv()
        open_count = history.refresh_open_trades(connector=connector, state=state, market_contexts=market_contexts)
        history.rebuild_summaries()
        export_result = history.build_export_workbook(export_days=export_days)
        if not export_result.get("ok"):
            result["warnings"].append(export_result.get("error", "advisor export build failed"))
        result.update(
            {
                "ok": True,
                "technical_settings": tech_path,
                "advisor_export": export_result.get("path", paths.export_path()),
                "config_snapshot_id": snapshot_id,
                "synced_closed_trades": synced,
                "export_closed_trades": export_result.get("closed_trades", 0),
                "open_trades": open_count,
                "export_days": export_days,
            }
        )
        history.record_event("advisor_package_exported", "Advisor package generated", payload=result)
    except Exception as exc:
        result["error"] = str(exc)
        history.record_event("advisor_package_export_error", str(exc), severity="ERROR", payload=result)
    return result
