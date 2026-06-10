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


def ensure_user_context():
    paths.ensure_advisor_dirs()
    path = paths.user_context_path()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(USER_CONTEXT_TEMPLATE)
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
        "user_context": paths.user_context_path(),
        "archive": None,
        "warnings": [],
    }
    try:
        paths.ensure_advisor_dirs()
        ensure_user_context()
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
