# -*- coding: utf-8 -*-
# FILE: config.py
# V4.0: UNIFIED CONFIG - SINGLE SOURCE OF TRUTH (KAISER EDITION)

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

# TÁCH BIỆT LUỒNG LỆNH (V3.0 ARCHITECTURE)
MANUAL_MAGIC_NUMBER = 8888                 
BOT_MAGIC_NUMBER = 9999

LOOP_SLEEP_SECONDS = 0.25           
RESET_HOUR = 6                      
DATA_DIR = "data"                   
STRICT_MODE_DEFAULT = True          
MAX_PING_MS = 150                   
MAX_SPREAD_POINTS = 150             

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

# GIỚI HẠN CHUNG
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
BOT_DAILY_TRADE_LIMIT = 10          
BOT_BYPASS_CHECKLIST = False

# ==============================================================================
# 5. LOGIC TRAILING STOP CƠ BẢN (BE & STEP & PNL)
# ==============================================================================
TSL_CONFIG = {
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
# 7. BỘ NÃO PHÂN TÍCH (SANDBOX V4.0 DEFAULTS - ĐÃ CẬP NHẬT G0 & TRIGGER MODE)
# ==============================================================================
trend_timeframe = "1h"              
entry_timeframe = "15m"             
NUM_H1_BARS, NUM_M15_BARS = 70, 70  
COOLDOWN_MINUTES = 1                
AUTO_TRADE_ENABLED = False          
DAEMON_LOOP_DELAY = 15

# Toán lý Math SL
sl_atr_multiplier = 0.2             

# --- CẤU HÌNH V4.0 MỚI BỔ SUNG ---
MASTER_STRATEGY = "QUANT" 
MASTER_EVAL_MODE = "VETO" 
MIN_MATCHING_VOTES = 3

G0_TIMEFRAME = mt5.TIMEFRAME_D1
G1_TIMEFRAME = mt5.TIMEFRAME_H1
G2_TIMEFRAME = mt5.TIMEFRAME_M15
G3_TIMEFRAME = mt5.TIMEFRAME_M15

# Cấu hình Mặc định cho 16+ Signals (Đã tích hợp G0 và Trigger Mode)
SANDBOX_CONFIG = {
    "voting_rules": {
        "G0": {"max_opposite": 0, "max_none": 0, "master_rule": "PASS"},
        "G1": {"max_opposite": 0, "max_none": 0, "master_rule": "FIX"},
        "G2": {"max_opposite": 0, "max_none": 1, "master_rule": "FIX"},
        "G3": {"max_opposite": 0, "max_none": 1, "master_rule": "IGNORE"}
    },
    "indicators": {
        "swing_point": {"active": True, "group": "G1", "active_modes": ["ANY"], "params": {}, "trigger_mode": "REALTIME_TICK"},
        "atr": {"active": True, "group": "G1", "active_modes": ["ANY"], "params": {"period": 14, "multiplier": 1.5}, "trigger_mode": "REALTIME_TICK"},
        "adx": {"active": True, "group": "G1", "active_modes": ["TREND", "BREAKOUT"], "params": {"period": 14, "strong": 23}, "trigger_mode": "STRICT_CLOSE"},
        "ema": {"active": True, "group": "G1", "active_modes": ["ANY"], "params": {"period": 50}, "trigger_mode": "REALTIME_TICK"},
        "pivot_points": {"active": False, "group": "G3", "active_modes": ["ANY"], "params": {}, "trigger_mode": "REALTIME_TICK"},
        "ema_cross": {"active": False, "group": "G2", "active_modes": ["TREND", "BREAKOUT"], "params": {"fast": 9, "slow": 21}, "trigger_mode": "STRICT_CLOSE"},
        "volume": {"active": True, "group": "G2", "active_modes": ["BREAKOUT"], "params": {"period": 20, "multiplier": 1.1}, "trigger_mode": "STRICT_CLOSE"},
        "supertrend": {"active": True, "group": "G2", "active_modes": ["TREND"], "params": {"period": 10, "multiplier": 3.0}, "trigger_mode": "REALTIME_TICK"},
        "psar": {"active": False, "group": "G2", "active_modes": ["TREND"], "params": {"step": 0.02, "max_step": 0.2}, "trigger_mode": "REALTIME_TICK"},
        "bollinger_bands": {"active": False, "group": "G2", "active_modes": ["RANGE"], "params": {"period": 20, "std_dev": 2.0}, "trigger_mode": "REALTIME_TICK"},
        "fibonacci": {"active": False, "group": "G2", "active_modes": ["RANGE", "EXHAUSTION"], "params": {"tolerance": 0.001}, "trigger_mode": "REALTIME_TICK"},
        "rsi": {"active": False, "group": "G2", "active_modes": ["RANGE"], "params": {"period": 14, "upper": 70, "lower": 30}, "trigger_mode": "STRICT_CLOSE"},
        "stochastic": {"active": False, "group": "G2", "active_modes": ["RANGE"], "params": {"k": 14, "d": 3, "smooth": 3, "upper": 80, "lower": 20}, "trigger_mode": "STRICT_CLOSE"},
        "macd": {"active": False, "group": "G2", "active_modes": ["EXHAUSTION"], "params": {"fast": 12, "slow": 26, "signal": 9}, "trigger_mode": "STRICT_CLOSE"},
        "multi_candle": {"active": True, "group": "G3", "active_modes": ["EXHAUSTION"], "params": {}, "trigger_mode": "STRICT_CLOSE"},
        "candle": {"active": False, "group": "G3", "active_modes": ["ANY"], "params": {}, "trigger_mode": "STRICT_CLOSE"}
    }
}

# ==============================================================================
# 8. TÍNH NĂNG NHỒI LỆNH (AUTO DCA/PCA - PARENT/CHILD BASKET)
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
    "CONFIRM_ADX": 23               
}