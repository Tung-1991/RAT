# -*- coding: utf-8 -*-
# FILE: config.py
# V6.1: GENTLE RULE UPDATE - INCREASE TRADE FREQUENCY FOR ETH TESTING

# ==============================================================================
# 1. HỆ THỐNG & KẾT NỐI
# ==============================================================================
COIN_LIST = [
    "BTCUSD", "ETHUSD", "XAUUSD", "USOIL", "UKOIL",
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "AUDUSD", "USDCAD"
]
DEFAULT_SYMBOL = "ETHUSD"           
BOT_ACTIVE_SYMBOLS = ["ETHUSD"]     # Mã Bot ngầm đang chạy
MAGIC_NUMBER = 8888                 
LOOP_SLEEP_SECONDS = 0.25           
RESET_HOUR = 6                      
DATA_DIR = "data"                   
STRICT_MODE_DEFAULT = True          
MAX_PING_MS = 150                   
MAX_SPREAD_POINTS = 150             

# ==============================================================================
# 2. TÀI KHOẢN & GIỚI HẠN GIAO DỊCH (GENTLE SETTINGS)
# ==============================================================================
ACCOUNT_TYPES_CONFIG = {
    "STANDARD": {"COMMISSION_PER_LOT": 0.0},
    "PRO":      {"COMMISSION_PER_LOT": 0.0},
    "RAW":      {"COMMISSION_PER_LOT": 7.0},
    "ZERO":     {"COMMISSION_PER_LOT": 7.0}
}
DEFAULT_ACCOUNT_TYPE = "STANDARD"

COMMISSION_RATES = {
    "BTCUSD": 16.5,   
    "ETHUSD": 1.25,   
    "XAUUSD": 7.0,    
    "USOIL": 0.0,     
    "UKOIL": 0.0,     
    "EURUSD": 7.0,    
    "GBPUSD": 7.0,
    "USDJPY": 7.0,
    "USDCHF": 7.0,
    "AUDUSD": 7.0,
    "USDCAD": 7.0
}

MAX_DAILY_LOSS_PERCENT = 2.5        # Tăng từ 1.5 -> 2.5 (Gentle)
LOSS_COUNT_MODE = "TOTAL"           
MAX_LOSING_STREAK = 3               
MAX_TRADES_PER_DAY = 30             # Tăng từ 15 -> 30 (Gentle)
MAX_OPEN_POSITIONS = 3              # Tăng từ 2 -> 3 (Gentle)

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
USE_DYNAMIC_ATR_BUFFER = False  

# ==============================================================================
# 7. BỘ NÃO PHÂN TÍCH - DAEMON & SIGNAL (GENTLE SETTINGS)
# ==============================================================================
trend_timeframe = "1H"              
entry_timeframe = "15M"             
NUM_H1_BARS, NUM_M15_BARS = 70, 70  
COOLDOWN_MINUTES = 1                

ALLOW_LONG_TRADES = True            
ALLOW_SHORT_TRADES = True           

# --- LỌC XU HƯỚNG (TREND H1) ---
USE_TREND_FILTER = True
USE_SUPERTREND_FILTER = False       # Tắt để tăng tần suất (Gentle)
USE_EMA_TREND_FILTER = True
USE_ADX_FILTER = True               

# --- VÙNG XÁM ADX (LỌC NHIỄU) ---
USE_ADX_GREY_ZONE = True            # Bật để linh hoạt Breakout/Pullback (Gentle)
ADX_WEAK = 18                       
ADX_STRONG = 23                     
ADX_MIN_LEVEL = 15                  # Hạ từ 20 -> 15 (Gentle)

# --- LOGIC VÀO LỆNH (ENTRY M15) ---
ENTRY_LOGIC_MODE = "DYNAMIC"        

# --- LỌC XÁC NHẬN NẾN & VOLUME (GENTLE SETTINGS) ---
USE_CANDLE_FILTER = True            
min_body_percent = 30.0             # Hạ từ 50.0 -> 30.0 (Gentle)
PULLBACK_CANDLE_PATTERN = "ENGULFING" 
USE_VOLUME_FILTER = False           # Tắt lọc Volume (Gentle)
volume_ma_period = 20               
volume_sd_multiplier = 0.1          # Giảm độ gắt của lọc volume

# --- SL KỸ THUẬT (MATH SL) ---
sl_atr_multiplier = 0.2             
USE_EMERGENCY_EXIT = True           

# ==============================================================================
# 8. CHU KỲ CÁC CHỈ BÁO
# ==============================================================================
atr_period = 14                 
swing_period = 5                

ST_ATR_PERIOD = 10              
ST_MULTIPLIER = 3.0             

DI_PERIOD = 14                  
ADX_PERIOD = 14                 

TREND_EMA_PERIOD = 50           
ENTRY_EMA_PERIOD = 21           

# ==============================================================================
# 9. TÍNH NĂNG NHỒI LỆNH (ĐANG PHÁT TRIỂN)
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
    "CONFIRM_INDICATOR": "ADX"      
}