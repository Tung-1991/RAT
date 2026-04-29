# -*- coding: utf-8 -*-
# FILE: config.py
# V4.2: UNIFIED CONFIG - LEGO MASTER & MULTI-GROUP (KAISER EDITION)

import os
import MetaTrader5 as mt5

# ==============================================================================
# 1. HỆ THỐNG & KẾT NỐI
# ==============================================================================
COIN_LIST = [
    "BTCUSD", "ETHUSD", "XAUUSD", "USOIL", "UKOIL",
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"
]
DEFAULT_SYMBOL = "ETHUSD"           
BOT_ACTIVE_SYMBOLS = ["ETHUSD"]     

MANUAL_MAGIC_NUMBER = 8888                 
BOT_MAGIC_NUMBER = 9999

LOOP_SLEEP_SECONDS = 0.25           
RESET_HOUR = 6                      
DATA_DIR = "data"                   
STRICT_MODE_DEFAULT = True          
MAX_PING_MS = 150                   
MAX_SPREAD_POINTS = 150             
ENABLE_DEBUG_LOGGING = False        

# ==============================================================================
# 2. TÀI KHOẢN & GIỚI HẠN GIAO DỊCH 
# ==============================================================================
ACCOUNT_TYPES_CONFIG = {
    "STANDARD": {"COMMISSION_PER_LOT": 0.0},
    "PRO":      {"COMMISSION_PER_LOT": 0.0},
    "RAW":      {"COMMISSION_PER_LOT": 7.0},
    "ZERO":     {"COMMISSION_PER_LOT": 7.0}
}
DEFAULT_ACCOUNT_TYPE = "STANDARD"

COMMISSION_RATES = {
    "BTCUSD": 16.5, "ETHUSD": 1.25, "XAUUSD": 7.0, "USOIL": 0.0, "UKOIL": 0.0,     
    "EURUSD": 7.0, "GBPUSD": 7.0, "USDJPY": 7.0, "USDCHF": 7.0, "AUDUSD": 7.0, "USDCAD": 7.0
}

MAX_DAILY_LOSS_PERCENT = 2.5        
LOSS_COUNT_MODE = "TOTAL"           
MAX_LOSING_STREAK = 3               
MAX_TRADES_PER_DAY = 30             
MAX_OPEN_POSITIONS = 3              

MIN_LOT_SIZE, MAX_LOT_SIZE = 0.01, 200.0
LOT_STEP = 0.01
MANUAL_CONFIG = {"BYPASS_CHECKLIST": False, "DEFAULT_LOT": 0.0}

# ==============================================================================
# 3. QUẢN LÝ VỐN (Dành cho MANUAL PRESETS trên UI)
# ==============================================================================
DEFAULT_PRESET = "SCALPING"
RISK_PER_TRADE_PERCENT = 0.30    
RISK_PER_TRADE_USD = 10.0        
MAX_RISK_ALLOWED = 2.0           

PRESETS = {
    "SCALPING": {"DESC": "Nhanh, SL ngắn", "SL_PERCENT": 0.4, "TP_RR_RATIO": 1.5, "RISK_PERCENT": 0.3},
    "SAFE":     {"DESC": "An toàn",        "SL_PERCENT": 0.8, "TP_RR_RATIO": 1.2, "RISK_PERCENT": 0.2},
    "BREAKOUT": {"DESC": "Săn trend lớn",  "SL_PERCENT": 1.0, "TP_RR_RATIO": 3.0, "RISK_PERCENT": 0.5}
}

# ==============================================================================
# 4. THAM SỐ RIÊNG CHO BOT (BOT SPECIFIC SETTINGS)
# ==============================================================================
BOT_RISK_PERCENT = 0.30             
BOT_TP_RR_RATIO = 1.5               
BOT_DEFAULT_TSL = "BE+STEP_R+SWING" 
BOT_BASE_SL = "G2"               # Đã cập nhật từ 'entry' sang 'G2'
BOT_DAILY_TRADE_LIMIT = 10          
BOT_BYPASS_CHECKLIST = False
FORCE_ANY_MODE = False        # True: Bỏ qua check Vĩ mô G0/G1, ép Market Mode = ANY
STRICT_RISK_CALC = False      # True: Trừ hao chi phí Spread/Commission thẳng vào Lot Size

# ==============================================================================
# 5. BOT SAFEGUARD (HÀNG RÀO BẢO VỆ ĐỘC LẬP CỦA BOT)
# ==============================================================================
BOT_SAFEGUARD = {
    "MAX_DAILY_LOSS_PERCENT": 2.5,
    "MAX_OPEN_POSITIONS": 3,
    "MAX_TRADES_PER_DAY": 30,
    "MAX_LOSING_STREAK": 3,
    "LOSS_COUNT_MODE": "TOTAL",
    "COOLDOWN_MINUTES": 1,
    "NUM_H1_BARS": 100,
    "NUM_M15_BARS": 100,
    "CHECK_PING": True,
    "MAX_PING_MS": 150,
    "CHECK_SPREAD": True,
    "MAX_SPREAD_POINTS": 150,
    "DAEMON_LOOP_DELAY": 15.0,
    "DCA_PCA_SCAN_INTERVAL": 2.0,
    "LOG_COOLDOWN_MINUTES": 60.0,
    "BOT_USE_TP": True,
    "STRICT_MIN_LOT": False,               # [NEW V4.4] Chặn Lot < Min_Vol
    "POST_CLOSE_COOLDOWN": 0,              # [NEW V4.4] Thời gian nghỉ nến sau SL (Giây)
    "CLOSE_ON_REVERSE_MIN_TIME": 180       # [NEW V4.4] Min Hold Time cho REVERSE_CLOSE
}

# ==============================================================================
# 6. LOGIC TRAILING STOP CƠ BẢN (BE & STEP & PNL)
# ==============================================================================
TSL_CONFIG = {
    "BE_CASH_TYPE": "USD",          # [NEW V4.4] Tùy chọn: USD, PERCENT, POINT
    "BE_VALUE": 5.0,                # [NEW V4.4] Target khóa lãi cứng
    "BE_MODE": "SOFT",              
    "BE_OFFSET_RR": 0.8,            
    "BE_OFFSET_POINTS": 0,          
    "PNL_LEVELS": [[0.5, 0.1], [1.0, 0.5], [2.0, 1.2]], 
    "STEP_R_SIZE": 1.0,             
    "STEP_R_RATIO": 0.8             
}

# ==============================================================================
# 6. LOGIC TSL SWING POINT BÁM THEO CẤU TRÚC GIÁ
# ==============================================================================
TSL_LOGIC_MODE = "STATIC"       
trail_atr_buffer = 0.2          
be_atr_buffer = 0.8             

# ==============================================================================
# 7. BỘ NÃO PHÂN TÍCH V4.2 (LEGO MASTER DEFAULTS)
# ==============================================================================
# Bỏ các biến trùng lặp (đã chuyển vào BOT_SAFEGUARD)
AUTO_TRADE_ENABLED = False          
sl_atr_multiplier = 0.2             

MASTER_STRATEGY = "QUANT" 
MASTER_EVAL_MODE = "VETO" 
MIN_MATCHING_VOTES = 3

# Chuyển đổi hằng số MT5 sang String để DataEngine tự Map
G0_TIMEFRAME = "1d"
G1_TIMEFRAME = "1h"
G2_TIMEFRAME = "15m"
G3_TIMEFRAME = "15m"

SANDBOX_CONFIG = {
    "voting_rules": {
        "G0": {"max_opposite": 0, "max_none": 0, "master_rule": "PASS"},
        "G1": {"max_opposite": 0, "max_none": 0, "master_rule": "FIX"},
        "G2": {"max_opposite": 0, "max_none": 1, "master_rule": "FIX"},
        "G3": {"max_opposite": 0, "max_none": 1, "master_rule": "IGNORE"}
    },
    "indicators": {
        # Bổ sung groups: [], is_trend, macro_role cho toàn bộ Indicator
        "adx": {
            "active": True, "groups": ["G0"], "is_trend": False, "macro_role": "BREAKOUT", 
            "active_modes": ["ANY"], "params": {"period": 14, "strong": 23}, "trigger_mode": "STRICT_CLOSE"
        },
        "ema": {
            "active": True, "groups": ["G0"], "is_trend": True, "macro_role": "BASE", 
            "active_modes": ["ANY"], "params": {"period": 50}, "trigger_mode": "REALTIME_TICK"
        },
        "swing_point": {
            "active": True, "groups": ["G1"], "is_trend": False, "macro_role": "NONE", 
            "active_modes": ["ANY"], "params": {"lookback": 50, "strength": 2, "atr_buffer": 0.5}, "trigger_mode": "REALTIME_TICK"
        },
        "atr": {
            "active": True, "groups": ["G1"], "is_trend": False, "macro_role": "NONE", 
            "active_modes": ["ANY"], "params": {"period": 14, "multiplier": 1.5}, "trigger_mode": "REALTIME_TICK"
        },
        "pivot_points": {
            "active": False, "groups": ["G3"], "is_trend": False, "macro_role": "NONE", 
            "active_modes": ["ANY"], "params": {}, "trigger_mode": "REALTIME_TICK"
        },
        "ema_cross": {
            "active": False, "groups": ["G2"], "is_trend": False, "macro_role": "NONE", 
            "active_modes": ["TREND"], "params": {"fast": 9, "slow": 21}, "trigger_mode": "STRICT_CLOSE"
        },
        "volume": {
            "active": True, "groups": ["G2"], "is_trend": False, "macro_role": "BREAKOUT", 
            "active_modes": ["BREAKOUT"], "params": {"period": 20, "multiplier": 1.1}, "trigger_mode": "STRICT_CLOSE"
        },
        "supertrend": {
            "active": True, "groups": ["G2"], "is_trend": True, "macro_role": "NONE", 
            "active_modes": ["TREND"], "params": {"period": 10, "multiplier": 3.0}, "trigger_mode": "REALTIME_TICK"
        },
        "psar": {
            "active": False, "groups": ["G2"], "is_trend": False, "macro_role": "NONE", 
            "active_modes": ["TREND"], "params": {"step": 0.02, "max_step": 0.2}, "trigger_mode": "REALTIME_TICK"
        },
        "bollinger_bands": {
            "active": False, "groups": ["G2"], "is_trend": False, "macro_role": "NONE", 
            "active_modes": ["RANGE"], "params": {"period": 20, "std_dev": 2.0}, "trigger_mode": "REALTIME_TICK"
        },
        "fibonacci": {
            "active": False, "groups": ["G2"], "is_trend": False, "macro_role": "NONE", 
            "active_modes": ["RANGE"], "params": {"tolerance": 0.001}, "trigger_mode": "REALTIME_TICK"
        },
        "rsi": {
            "active": False, "groups": ["G2"], "is_trend": False, "macro_role": "NONE", 
            "active_modes": ["RANGE"], "params": {"period": 14, "upper": 70, "lower": 30}, "trigger_mode": "STRICT_CLOSE"
        },
        "stochastic": {
            "active": False, "groups": ["G2"], "is_trend": False, "macro_role": "NONE", 
            "active_modes": ["RANGE"], "params": {"k": 14, "d": 3, "smooth": 3, "upper": 80, "lower": 20}, "trigger_mode": "STRICT_CLOSE"
        },
        "macd": {
            "active": False, "groups": ["G2"], "is_trend": False, "macro_role": "NONE", 
            "active_modes": ["EXHAUSTION"], "params": {"fast": 12, "slow": 26, "signal": 9}, "trigger_mode": "STRICT_CLOSE"
        },
        "multi_candle": {
            "active": True, "groups": ["G3"], "is_trend": False, "macro_role": "NONE", 
            "active_modes": ["EXHAUSTION"], "params": {"num_candles": 3, "min_total_pips": 50}, "trigger_mode": "STRICT_CLOSE"
        },
        "candle": {
            "active": False, "groups": ["G3"], "is_trend": False, "macro_role": "NONE", 
            "active_modes": ["ANY"], "params": {"min_body_size": 1.2, "check_volume": True}, "trigger_mode": "STRICT_CLOSE"
        }
    }
}

# ==============================================================================
# 8. TÍNH NĂNG NHỒI LỆNH (AUTO DCA/PCA)
# ==============================================================================
DCA_CONFIG = {
    "ENABLED": False,               
    "MAX_STEPS": 3,                 
    "STEP_MULTIPLIER": 1.5,         
    "DISTANCE_ATR_R": 1.0           
}
PCA_CONFIG = {
    "ENABLED": False,               
    "MAX_STEPS": 2,                 
    "STEP_MULTIPLIER": 0.5,         
    "DISTANCE_ATR_R": 1.5           
}