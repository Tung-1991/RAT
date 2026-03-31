# -*- coding: utf-8 -*-
# FILE: config.py
# V4.1.1: HỢP NHẤT MASTER-WORKER (FIXED UI CRASH)

# ==============================================================================
# 1. HỆ THỐNG & KẾT NỐI (CORE)
# ==============================================================================
COIN_LIST = ["BTCUSD", "ETHUSD", "XAUUSD", "EURUSD", "GBPUSD"]
DEFAULT_SYMBOL = "ETHUSD"           # Coin mặc định khi mở app
MAGIC_NUMBER = 8888                 # ID nhận diện lệnh của Bot
LOOP_SLEEP_SECONDS = 0.25           # Tốc độ làm mới vòng lặp UI (giây)
RESET_HOUR = 6                      # Giờ bắt đầu tính ngày mới (6h sáng)

DATA_DIR = "data"                   # Thư mục chứa JSON, DB, Logs
STRICT_MODE_DEFAULT = True          # Bật kiểm tra an toàn trước khi trade
MAX_PING_MS = 150                   # Ping tối đa cho phép (ms)
MAX_SPREAD_POINTS = 150             # Spread tối đa cho phép (Points)

# ==============================================================================
# 2. TÀI KHOẢN & GIỚI HẠN GIAO DỊCH (CORE)
# ==============================================================================
ACCOUNT_TYPES_CONFIG = {
    "STANDARD": {"COMMISSION_PER_LOT": 0.0},
    "PRO":      {"COMMISSION_PER_LOT": 0.0},
    "RAW":      {"COMMISSION_PER_LOT": 7.0},
    "ZERO":     {"COMMISSION_PER_LOT": 7.0}
}
DEFAULT_ACCOUNT_TYPE = "STANDARD"
COMMISSION_RATES = {"BTCUSD": 16.5, "ETHUSD": 1.25, "XAUUSD": 7.0} # Ghi đè phí cho Raw/Zero

MAX_DAILY_LOSS_PERCENT = 1.5        # % Lỗ tối đa/ngày -> Dừng bot
LOSS_COUNT_MODE = "TOTAL"           # "TOTAL" (Tổng thua) hoặc "STREAK" (Thua liên tiếp)
MAX_LOSING_STREAK = 3               # Số lệnh thua cho phép
MAX_TRADES_PER_DAY = 15             # Tổng số lệnh tối đa/ngày
MAX_OPEN_POSITIONS = 2              # Số lệnh (hoặc cụm lệnh) chạy cùng lúc

MIN_LOT_SIZE, MAX_LOT_SIZE = 0.01, 200.0
LOT_STEP = 0.01

MANUAL_CONFIG = {"BYPASS_CHECKLIST": False, "DEFAULT_LOT": 0.0}

# ==============================================================================
# 3. QUẢN LÝ VỐN & TRAILING STOP (CORE)
# ==============================================================================
DEFAULT_PRESET = "SCALPING"

# --- CÁC BIẾN GỐC DỰ PHÒNG (TRÁNH CRASH GIAO DIỆN) ---
RISK_PER_TRADE_PERCENT = 0.30    # % Rủi ro mặc định (Fallback nếu Preset ko có)
RISK_PER_TRADE_USD = 10.0        # $ Rủi ro tối đa (Dự phòng an toàn)
MAX_RISK_ALLOWED = 2.0           # Giới hạn cứng % rủi ro
# ----------------------------------------------------

PRESETS = {
    "SCALPING": {"DESC": "Nhanh, SL ngắn", "SL_PERCENT": 0.4, "TP_RR_RATIO": 1.5, "RISK_PERCENT": 0.3},
    "SAFE":     {"DESC": "An toàn",        "SL_PERCENT": 0.8, "TP_RR_RATIO": 1.2, "RISK_PERCENT": 0.2},
    "BREAKOUT": {"DESC": "Săn trend lớn",  "SL_PERCENT": 1.0, "TP_RR_RATIO": 3.0, "RISK_PERCENT": 0.5}
}

TSL_CONFIG = {
    "BE_MODE": "SOFT",              # "SOFT" (Entry-Fee) hoặc "SMART" (Entry+Fee)
    "BE_OFFSET_RR": 0.8,            # Lãi 0.8R -> Kéo SL về Entry
    "BE_OFFSET_POINTS": 0,          # Point cộng thêm cho an toàn
    "PNL_LEVELS": [[0.5, 0.1], [1.0, 0.5], [2.0, 1.2]], # [%Lãi, %Khóa]
    "STEP_R_SIZE": 1.0,             # Bước nhảy TSL (Ví dụ: 1R)
    "STEP_R_RATIO": 0.8             # Tỷ lệ giữ lại (0.8 = 80% của bước)
}

# ==============================================================================
# 4. BỘ NÃO PHÂN TÍCH - BRAIN DAEMON (P1)
# ==============================================================================
trend_timeframe = "1H"              # Khung xét Trend
entry_timeframe = "15M"             # Khung xét Entry
NUM_H1_BARS, NUM_M15_BARS = 70, 70  # Số nến cần tải
COOLDOWN_MINUTES = 1                # Thời gian chờ sau khi đóng lệnh

ALLOW_LONG_TRADES = True            # Cho phép đánh Lên
ALLOW_SHORT_TRADES = True           # Cho phép đánh Xuống

# --- Cấu hình Logic Entry & Trend ---
ENTRY_LOGIC_MODE = "DYNAMIC"        # "BREAKOUT", "PULLBACK", "DYNAMIC"
USE_TREND_FILTER = True
USE_SUPERTREND_FILTER = True
USE_EMA_TREND_FILTER = True
USE_ADX_FILTER = True               # Dùng ADX lọc Sideways

# --- Vùng xám ADX (Bảo vệ lúc nhiễu) ---
USE_ADX_GREY_ZONE = False           
ADX_WEAK, ADX_STRONG = 18, 23       # Dưới 18: Sideways | Trên 23: Trend
ADX_MIN_LEVEL = 20                  # Dùng nếu TẮT Grey Zone

# --- Cấu hình Nến & Volume ---
USE_CANDLE_FILTER = True            
min_body_percent = 50.0             # % thân nến tối thiểu (Breakout)
PULLBACK_CANDLE_PATTERN = "ENGULFING" # Mẫu nến đảo chiều
USE_VOLUME_FILTER = True            
volume_ma_period, volume_sd_multiplier = 20, 0.5

# --- Chu kỳ Indicator ---
atr_period, swing_period = 14, 5
ST_ATR_PERIOD, ST_MULTIPLIER = 10, 3.0
DI_PERIOD, ADX_PERIOD = 14, 14
TREND_EMA_PERIOD, ENTRY_EMA_PERIOD = 50, 21

# --- SL Kỹ thuật (Brain Toán học) ---
sl_atr_multiplier = 0.2             # SwingPoint +/- (0.2 * ATR)
USE_EMERGENCY_EXIT = True           # Thoát sớm nếu H1 đảo chiều

# ==============================================================================
# 5. CHIẾN THUẬT NÂNG CAO - DCA & PCA (BRAIN DAEMON) 
# ==============================================================================
# [ĐANG UPDATE] - Các thông số dưới đây sẽ được tích hợp vào Brain để nhồi lệnh
DCA_CONFIG = {
    "ENABLED": False,               # Bật/Tắt trung bình giá xuống
    "MAX_STEPS": 3,                 # Số lệnh nhồi tối đa
    "STEP_MULTIPLIER": 1.5,         # Hệ số Lot nhồi (Martingale nhẹ)
    "DISTANCE_ATR_R": 1.0           # Khoảng cách nhồi (Tính theo R hoặc ATR)
}

PCA_CONFIG = {
    "ENABLED": False,               # Bật/Tắt nhồi lệnh thuận xu hướng (Pyramiding)
    "MAX_STEPS": 2,                 # Số lệnh nhồi tối đa
    "STEP_MULTIPLIER": 0.5,         # Giảm lot khi nhồi thuận trend để giảm rủi ro
    "CONFIRM_INDICATOR": "ADX"      # Điều kiện nhồi (VD: ADX > 25, Volume Spike)
}