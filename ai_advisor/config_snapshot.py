# -*- coding: utf-8 -*-
import copy
import hashlib
import json
import os
from datetime import datetime

import config

from . import paths


def _json_safe(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    return str(value)


def _read_json_file(path):
    if not path or not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        return {"_advisor_read_error": str(exc)}


def _public_config_values():
    values = {}
    for name in dir(config):
        if name.startswith("__"):
            continue
        value = getattr(config, name)
        if callable(value):
            continue
        if isinstance(value, (str, int, float, bool, list, tuple, dict, set)) or value is None:
            values[name] = _json_safe(value)
    return values


def _active_symbols(global_cfg):
    symbols = []
    raw = global_cfg.get("BOT_ACTIVE_SYMBOLS") or getattr(config, "BOT_ACTIVE_SYMBOLS", [])
    if isinstance(raw, (list, tuple, set)):
        symbols.extend(str(s) for s in raw if s)
    for sym in getattr(config, "COIN_LIST", []):
        if sym not in symbols:
            symbols.append(sym)
    return symbols


def _source_paths():
    import core.storage_manager as storage_manager

    return {
        "brain_settings": getattr(storage_manager, "BRAIN_FILE", None),
        "symbol_overrides": getattr(storage_manager, "SYMBOL_OVERRIDES_FILE", None),
        "tsl_settings": os.path.join(paths.account_dir(), "tsl_settings.json"),
        "presets_config": os.path.join(paths.account_dir(), "presets_config.json"),
        "grid_settings": os.path.join(paths.account_dir(), "grid_settings.json"),
        "hedge_settings": os.path.join(paths.account_dir(), "hedge_settings.json"),
        "bot_state": getattr(storage_manager, "STATE_FILE", None),
        "grid_state": os.path.join(paths.account_dir(), "grid_state.json"),
        "hedge_state": os.path.join(paths.account_dir(), "hedge_state.json"),
        "live_signals": os.path.join(paths.account_dir(), "live_signals.json"),
        "system_meta": getattr(storage_manager, "SYSTEM_META_FILE", None),
    }


def _stable_hash(payload):
    raw = json.dumps(_json_safe(payload), sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def build_snapshot(reason="manual"):
    import core.storage_manager as storage_manager

    paths.ensure_advisor_dirs()
    global_cfg = storage_manager.load_brain_settings()
    active_by_symbol = {}
    for symbol in _active_symbols(global_cfg):
        try:
            active_by_symbol[symbol] = storage_manager.get_brain_settings_for_symbol(symbol)
        except Exception as exc:
            active_by_symbol[symbol] = {"_advisor_merge_error": str(exc)}

    source_paths = _source_paths()
    raw_sources = {
        name: {"path": path, "data": _read_json_file(path)}
        for name, path in source_paths.items()
        if path
    }

    config_payload = {
        "config_py": _public_config_values(),
        "active_global": _json_safe(global_cfg),
        "active_by_symbol": _json_safe(active_by_symbol),
        "raw_sources": _json_safe(raw_sources),
    }
    snapshot_id = _stable_hash(config_payload)

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "reason": reason,
        "account_id": paths.account_id(),
        "account_dir": paths.account_dir(),
        "config_snapshot_id": snapshot_id,
        "hash_basis": "config_py + active_global + active_by_symbol + raw_settings_sources",
        "settings": config_payload,
    }


def build_technical_settings(reason="manual"):
    return build_snapshot(reason=reason)


def compact_snapshot_json(snapshot, limit=30000):
    raw = json.dumps(_json_safe(snapshot), ensure_ascii=False, sort_keys=True)
    if len(raw) <= limit:
        return raw
    return raw[:limit] + "...[truncated]"


def flatten_dict(data, prefix=""):
    out = {}
    if isinstance(data, dict):
        for key, value in data.items():
            next_key = f"{prefix}.{key}" if prefix else str(key)
            out.update(flatten_dict(value, next_key))
    elif isinstance(data, list):
        out[prefix] = json.dumps(_json_safe(data), ensure_ascii=False, sort_keys=True)
    else:
        out[prefix] = _json_safe(data)
    return out


def diff_snapshots(old_snapshot, new_snapshot, limit=300):
    old_flat = flatten_dict((old_snapshot or {}).get("settings", old_snapshot or {}))
    new_flat = flatten_dict((new_snapshot or {}).get("settings", new_snapshot or {}))
    changes = []
    for key in sorted(set(old_flat) | set(new_flat)):
        old_val = old_flat.get(key)
        new_val = new_flat.get(key)
        if old_val != new_val:
            changes.append((key, old_val, new_val))
            if len(changes) >= limit:
                changes.append(("_advisor_diff_truncated", "", f"limit={limit}"))
                break
    return changes


def clone_json(value):
    return copy.deepcopy(_json_safe(value))
