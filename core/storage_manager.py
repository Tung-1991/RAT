# -*- coding: utf-8 -*-
import json
import os
import csv
import time
import copy
from datetime import datetime, timedelta
from typing import Dict, Any
import config 

STATE_FILE = "data/bot_state.json"
BRAIN_FILE = "data/brain_settings.json"
HISTORY_FILE = "data/trade_history_log.csv" 
MASTER_LOG_FILE = "data/trade_history_master.csv"

# ==================== IN-MEMORY CACHE (TTL 2s) ====================
_cache_brain = {"data": None, "ts": 0.0}        # Cache brain_settings.json
_cache_overrides = {"data": None, "ts": 0.0}     # Cache symbol_overrides.json
_cache_merged = {}                                # Cache kết quả merge theo symbol
_CACHE_TTL = 2.0                                  # Thời gian sống cache (giây)

def invalidate_settings_cache():
    """Xóa cache khi UI lưu config mới. Gọi hàm này sau mỗi lần save."""
    _cache_brain["data"] = None
    _cache_brain["ts"] = 0.0
    _cache_overrides["data"] = None
    _cache_overrides["ts"] = 0.0
    _cache_merged.clear()

def get_reset_hour():
    try:
        bs = load_brain_settings()
        if "bot_safeguard" in bs and "RESET_HOUR" in bs["bot_safeguard"]:
            return int(bs["bot_safeguard"]["RESET_HOUR"])
    except:
        pass
    return getattr(config, "RESET_HOUR", 6)

def get_today_str():
    now = datetime.now()
    reset_hour = get_reset_hour()
    if now.hour < reset_hour:
        prev_day = now - timedelta(days=1)
        return prev_day.strftime("%Y-%m-%d")
    return now.strftime("%Y-%m-%d")

def append_trade_log(ticket, symbol, type_str, volume, entry_price, sl, tp, fee, pnl, close_reason, market_mode="ANY", trigger_signal="UNK", session_id="LEGACY", open_time_str=""):
    file_exists = os.path.isfile(MASTER_LOG_FILE)
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S") 
        time_display = f"{open_time_str[11:]} -> {now_str[11:]}" if open_time_str else now_str
        with open(MASTER_LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                # [NEW V5] Thêm cột Entry, SL, TP, Fee
                writer.writerow(["Time", "Ticket", "Symbol", "Type", "Vol", "Entry", "SL", "TP", "Fee", "PnL ($)", "Reason", "Market Mode", "Trigger", "Session_ID"])
            writer.writerow([
                time_display, ticket, symbol, type_str, volume, 
                f"{entry_price:.5f}", f"{sl:.5f}", f"{tp:.5f}", f"{fee:.2f}", 
                f"{pnl:.2f}", close_reason, market_mode, trigger_signal, session_id
            ])
    except:
        pass

def delete_session_log(session_id: str):
    """Xóa tất cả các lệnh thuộc một Session cụ thể khỏi CSV"""
    if not os.path.exists(MASTER_LOG_FILE):
        return
    try:
        rows = []
        with open(MASTER_LOG_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if header:
                rows.append(header)
                for row in reader:
                    # Nếu có Session_ID (cột cuối) và nó khớp thì bỏ qua (xóa)
                    # Support cả format cũ (10 cột) và mới (14 cột)
                    if len(row) >= 10 and row[-1] == session_id:
                        continue
                    rows.append(row)
        
        with open(MASTER_LOG_FILE, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    except:
        pass

def save_daily_history_to_csv(prev_date, pnl, trades_count, win_streak, lose_streak):
    file_exists = os.path.isfile(HISTORY_FILE)
    try:
        with open(HISTORY_FILE, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["Date", "PnL ($)", "Total Trades", "End Streak"])
            streak_str = f"L{lose_streak}" if lose_streak > 0 else f"W{win_streak}"
            writer.writerow([prev_date, f"{pnl:.2f}", trades_count, streak_str])
    except:
        pass

def load_state() -> Dict[str, Any]:
    default_state = {
        "date": get_today_str(),
        "pnl_today": 0.0,
        "fee_today": 0.0,
        "starting_balance": 0.0,
        "trades_today_count": 0,
        "losing_streak": 0,
        "daily_loss_count": 0,
        "active_trades": [],
        "tsl_disabled_tickets": [], 
        "daily_history": [],
        "trade_tactics": {},        
        "initial_r_dist": {},
        "parent_baskets": {},       
        "child_to_parent": {},       
        "last_child_bar_time": {},
        "bot_last_entry_times": {},
        "exit_reasons": {},          # [NEW V4.4] Tracking lý do đóng lệnh
        "last_close_times": {},      # [NEW V4.4] Tracking thời gian đóng lệnh cho Cooldown
        "last_dca_pca_close_time": {}, # [NEW V4.4] Tracking DCA/PCA Cooldown
        "current_session_id": datetime.now().strftime("%Y%m%d_%H%M%S"),
        "cooldown_until": 0.0
    }
    
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)

    if not os.path.exists(STATE_FILE):
        return default_state

    try:
        with open(STATE_FILE, "r") as f:
            state = json.load(f)
            
            if "daily_history" not in state: state["daily_history"] = []
            if "tsl_disabled_tickets" not in state: state["tsl_disabled_tickets"] = []
            if "trade_tactics" not in state: state["trade_tactics"] = {} 
            if "initial_r_dist" not in state: state["initial_r_dist"] = {}       
            if "parent_baskets" not in state: state["parent_baskets"] = {} 
            if "child_to_parent" not in state: state["child_to_parent"] = {}
            if "last_child_bar_time" not in state: state["last_child_bar_time"] = {} 
            if "bot_last_entry_times" not in state: state["bot_last_entry_times"] = {}
            if "exit_reasons" not in state: state["exit_reasons"] = {}
            if "last_close_times" not in state: state["last_close_times"] = {}
            if "last_dca_pca_close_time" not in state: state["last_dca_pca_close_time"] = {}
            if "bot_pnl_today" not in state: state["bot_pnl_today"] = 0.0
            if "bot_trades_today" not in state: state["bot_trades_today"] = 0
            if "bot_daily_loss_count" not in state: state["bot_daily_loss_count"] = 0
            if "daily_loss_count" not in state: state["daily_loss_count"] = 0    
            if "fee_today" not in state: state["fee_today"] = 0.0

            current_date = get_today_str()
            saved_date = state.get("date")

            if saved_date != current_date:
                save_daily_history_to_csv(
                    saved_date, 
                    state.get("pnl_today", 0), 
                    state.get("trades_today_count", 0),
                    0, 
                    state.get("losing_streak", 0)
                )

                state["date"] = current_date
                state["pnl_today"] = 0.0
                state["trades_today_count"] = 0
                state["losing_streak"] = 0 
                state["daily_loss_count"] = 0  
                state["daily_history"] = [] 
                state["starting_balance"] = 0.0 
                
                # [FIX] Reset các biến phân tách rạch ròi
                state["bot_pnl_today"] = 0.0
                state["bot_trades_today"] = 0
                state["bot_daily_loss_count"] = 0
                state["manual_pnl_today"] = 0.0
                state["manual_trades_today"] = 0
                state["manual_daily_loss_count"] = 0
                state["fee_today"] = 0.0
                
                # Khởi tạo session mới cho ngày mới
                state["current_session_id"] = datetime.now().strftime("%Y%m%d_%H%M%S")
                state["cooldown_until"] = 0.0

            if "current_session_id" not in state:
                state["current_session_id"] = datetime.now().strftime("%Y%m%d_%H%M%S")
            if "cooldown_until" not in state:
                state["cooldown_until"] = 0.0
                
        return state
    except:
        return default_state

def save_state(state: Dict[str, Any]):
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
    except:
        pass

def reset_bot_session(reason="Manual"):
    """Dọn dẹp cache bot hiện hành và tạo Session_ID mới"""
    state = load_state()
    # Save session tổng kết (nếu cần thiết)
    
    # Đặt lại cache của bot
    state["bot_pnl_today"] = 0.0
    state["bot_trades_today"] = 0
    state["bot_daily_loss_count"] = 0
    state["losing_streak"] = 0
    state["cooldown_until"] = 0.0
    
    # Tạo Session_ID mới
    state["current_session_id"] = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_state(state)

def get_last_dca_pca_close_time(symbol: str) -> float:
    state = load_state()
    return state.get("last_dca_pca_close_time", {}).get(symbol, 0.0)

def update_last_dca_pca_close_time(symbol: str, timestamp: float):
    state = load_state()
    if "last_dca_pca_close_time" not in state:
        state["last_dca_pca_close_time"] = {}
    state["last_dca_pca_close_time"][symbol] = timestamp
    save_state(state)

def load_brain_settings() -> Dict[str, Any]:
    default_brain = {
        "MASTER_EVAL_MODE": getattr(config, "MASTER_EVAL_MODE", "VETO"),
        "MIN_MATCHING_VOTES": getattr(config, "MIN_MATCHING_VOTES", 3),
        "G0_TIMEFRAME": getattr(config, "G0_TIMEFRAME", "1d"),
        "G1_TIMEFRAME": getattr(config, "G1_TIMEFRAME", "1h"),
        "G2_TIMEFRAME": getattr(config, "G2_TIMEFRAME", "15m"),
        "G3_TIMEFRAME": getattr(config, "G3_TIMEFRAME", "15m"),
        "voting_rules": {
            "G0": {"max_opposite": 0, "max_none": 0, "master_rule": "PASS"},
            "G1": {"max_opposite": 0, "max_none": 0, "master_rule": "FIX"},
            "G2": {"max_opposite": 0, "max_none": 1, "master_rule": "FIX"},
            "G3": {"max_opposite": 0, "max_none": 1, "master_rule": "IGNORE"}
        },
        "indicators": getattr(config, "SANDBOX_CONFIG", {}).get("indicators", {})
    }
    
    os.makedirs(os.path.dirname(BRAIN_FILE), exist_ok=True)
    if not os.path.exists(BRAIN_FILE):
        return default_brain

    try:
        with open(BRAIN_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            
            for key in ["MASTER_EVAL_MODE", "MIN_MATCHING_VOTES", "G0_TIMEFRAME", "G1_TIMEFRAME", "G2_TIMEFRAME", "G3_TIMEFRAME"]:
                if key in data: default_brain[key] = data[key]
            
            if "voting_rules" in data:
                for grp in ["G0", "G1", "G2", "G3"]:
                    if grp in data["voting_rules"]:
                        default_brain["voting_rules"][grp] = data["voting_rules"][grp]
            
            if "indicators" in data:
                for ind, cfg in data["indicators"].items():
                    if ind in default_brain["indicators"]:
                        default_brain["indicators"][ind].update(cfg)
                    else:
                        default_brain["indicators"][ind] = cfg
            return default_brain
    except:
        return default_brain

def save_brain_settings(data: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(BRAIN_FILE), exist_ok=True)
        with open(BRAIN_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except:
        pass

# =====================================================================
# [NEW V4.4] SYMBOL OVERRIDES (MẸ - CON)
# =====================================================================
SYMBOL_OVERRIDES_FILE = "data/symbol_overrides.json"

def load_symbol_overrides() -> Dict[str, Any]:
    try:
        if os.path.exists(SYMBOL_OVERRIDES_FILE):
            with open(SYMBOL_OVERRIDES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def save_symbol_overrides(data: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(SYMBOL_OVERRIDES_FILE), exist_ok=True)
        with open(SYMBOL_OVERRIDES_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        invalidate_settings_cache()  # Xóa cache khi lưu override mới
    except Exception:
        pass

def _load_brain_cached() -> Dict[str, Any]:
    """Đọc brain_settings.json với cache TTL."""
    now = time.monotonic()
    if _cache_brain["data"] is not None and (now - _cache_brain["ts"]) < _CACHE_TTL:
        return _cache_brain["data"]
    
    data = {}
    try:
        if os.path.exists(BRAIN_FILE):
            with open(BRAIN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
    except Exception:
        data = load_brain_settings()
    
    _cache_brain["data"] = data
    _cache_brain["ts"] = now
    return data

def _load_overrides_cached() -> Dict[str, Any]:
    """Đọc symbol_overrides.json với cache TTL."""
    now = time.monotonic()
    if _cache_overrides["data"] is not None and (now - _cache_overrides["ts"]) < _CACHE_TTL:
        return _cache_overrides["data"]
    
    data = load_symbol_overrides()
    _cache_overrides["data"] = data
    _cache_overrides["ts"] = now
    return data

def get_brain_settings_for_symbol(symbol: str = None) -> Dict[str, Any]:
    """
    Hàm chuẩn mới: Đọc toàn bộ brain_settings.json (Mẹ),
    sau đó nếu có symbol và symbol có config riêng, sẽ merge đè lên.
    Kết quả được cache trong RAM (TTL 2s) để tối ưu hiệu năng.
    """
    # Cache key: symbol hoặc "__GLOBAL__"
    cache_key = symbol or "__GLOBAL__"
    now = time.monotonic()
    
    # Kiểm tra cache merged đã có và còn hạn không
    if cache_key in _cache_merged:
        cached = _cache_merged[cache_key]
        if (now - cached["ts"]) < _CACHE_TTL:
            return copy.deepcopy(cached["data"])  # deepcopy để tránh mutation
    
    # Cache miss → đọc file (qua cache layer 1)
    base_brain = copy.deepcopy(_load_brain_cached())
        
    if not symbol:
        _cache_merged[cache_key] = {"data": base_brain, "ts": now}
        return copy.deepcopy(base_brain)
        
    overrides = _load_overrides_cached()
    if symbol in overrides:
        sym_override = overrides[symbol]
        
        # Merge Sandbox config
        if "sandbox" in sym_override:
            sb = sym_override["sandbox"]
            for k in ["MASTER_EVAL_MODE", "MIN_MATCHING_VOTES", "FORCE_ANY_MODE", 
                      "G0_TIMEFRAME", "G1_TIMEFRAME", "G2_TIMEFRAME", "G3_TIMEFRAME"]:
                if k in sb: base_brain[k] = sb[k]
                
            if "voting_rules" in sb:
                if "voting_rules" not in base_brain: base_brain["voting_rules"] = {}
                for grp, rules in sb["voting_rules"].items():
                    base_brain["voting_rules"][grp] = rules
                    
            if "risk_tsl" in sb:
                if "risk_tsl" not in base_brain: base_brain["risk_tsl"] = {}
                base_brain["risk_tsl"].update(sb["risk_tsl"])
                
            if "indicators" in sb:
                if "indicators" not in base_brain: base_brain["indicators"] = {}
                base_brain["indicators"] = sb["indicators"]
                
            if "dca_config" in sb:
                if "dca_config" not in base_brain: base_brain["dca_config"] = {}
                base_brain["dca_config"].update(sb["dca_config"])
                
            if "pca_config" in sb:
                if "pca_config" not in base_brain: base_brain["pca_config"] = {}
                base_brain["pca_config"].update(sb["pca_config"])
                
        # Merge TSL config
        if "tsl" in sym_override:
            tsl = sym_override["tsl"]
            if "TSL_CONFIG" in tsl:
                if "TSL_CONFIG" not in base_brain: base_brain["TSL_CONFIG"] = {}
                base_brain["TSL_CONFIG"].update(tsl["TSL_CONFIG"])
            if "TSL_LOGIC_MODE" in tsl:
                base_brain["TSL_LOGIC_MODE"] = tsl["TSL_LOGIC_MODE"]

    _cache_merged[cache_key] = {"data": base_brain, "ts": now}
    return copy.deepcopy(base_brain)
