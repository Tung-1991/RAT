# -*- coding: utf-8 -*-
# FILE: core/logger_setup.py
# V4.0: 3-TIER LOGGING SYSTEM (KAISER EDITION)

import logging
import os
from logging.handlers import TimedRotatingFileHandler 

def setup_logging(debug_mode=False, process_name="ui"):
    """
    Hệ thống quản trị Log 3 Lớp:
    1. CRITICAL: Khớp lệnh, DCA/PCA, SL/TP, Lỗi API.
    2. INFO: Sự kiện hệ thống, cấu hình, G0 đảo chiều.
    3. DEBUG: Chi tiết giá trị Indicator (Mặc định OFF).
    """
    
    CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
    PROJECT_ROOT = os.path.dirname(CURRENT_DIR)
    LOG_DIR = os.path.join(PROJECT_ROOT, "data", "logs")
    os.makedirs(LOG_DIR, exist_ok=True)
    
    logger = logging.getLogger("ExnessBot")
    
    # Master switch
    if debug_mode:
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)
    
    if logger.hasHandlers():
        logger.handlers.clear()
        
    file_formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    # --- LỚP 1: CRITICAL LOG (Giao dịch, Lỗi MT5) ---
    critical_handler = TimedRotatingFileHandler(os.path.join(LOG_DIR, f"{process_name}_trade_critical.log"), when='D', interval=1, backupCount=30, encoding='utf-8')
    critical_handler.setLevel(logging.CRITICAL)
    critical_handler.setFormatter(file_formatter)
    
    # --- LỚP 2: INFO LOG (Sự kiện hệ thống) ---
    info_handler = TimedRotatingFileHandler(os.path.join(LOG_DIR, f"{process_name}_system_events.log"), when='D', interval=1, backupCount=7, encoding='utf-8')
    info_handler.setLevel(logging.INFO)
    
    # Cấu hình bộ lọc để INFO không ghi lại các log CRITICAL (tránh trùng lặp)
    class InfoFilter(logging.Filter):
        def filter(self, record):
            return record.levelno >= logging.INFO and record.levelno < logging.CRITICAL
    info_handler.addFilter(InfoFilter())
    info_handler.setFormatter(file_formatter)
    
    # --- LỚP 3: DEBUG LOG (Dữ liệu Indicator 15s) ---
    debug_handler = TimedRotatingFileHandler(os.path.join(LOG_DIR, f"{process_name}_signal_debug.log"), when='D', interval=1, backupCount=2, encoding='utf-8')
    debug_handler.setLevel(logging.DEBUG)
    
    class DebugFilter(logging.Filter):
        def filter(self, record):
            return record.levelno == logging.DEBUG
    debug_handler.addFilter(DebugFilter())
    debug_handler.setFormatter(file_formatter)

    # --- LỚP MÀN HÌNH UI (CONSOLE) ---
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO) 
    console_handler.setFormatter(logging.Formatter('%(message)s'))

    # Nạp Handlers
    logger.addHandler(critical_handler)
    logger.addHandler(info_handler)
    if debug_mode:
        logger.addHandler(debug_handler)
    logger.addHandler(console_handler)
    
    logger.propagate = False
    
    if debug_mode:
        logger.info("Hệ thống Logging 3 Lớp ĐÃ BẬT DEBUG MODE.")
    
    return logger