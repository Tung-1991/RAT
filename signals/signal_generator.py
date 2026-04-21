# -*- coding: utf-8 -*-
# FILE: signals/signal_generator.py
# V3.0: UNIFIED SIGNAL & VOTING ENGINE (KAISER EDITION)

import json
import os
import importlib
import logging
import pandas as pd
import config

logger = logging.getLogger("ExnessBot")
BRAIN_SETTINGS_PATH = "data/brain_settings.json"

class SignalGenerator:
    def __init__(self):
        self.config = self._load_config()

    def reload_config(self):
        """Được gọi bởi Bot Daemon khi phát hiện file JSON thay đổi (Hot-Reload)"""
        self.config = self._load_config()
        logger.info("[SignalGen] Đã nạp lại cấu hình Sandbox V3.0 (Hot-Reload)")

    def _load_config(self) -> dict:
        """
        Nguyên tắc Single Source of Truth: 
        Ưu tiên đọc từ brain_settings.json (UI xuất ra). 
        Nếu lỗi hoặc thiếu, lấy mặc định từ config.SANDBOX_CONFIG.
        """
        base_config = getattr(config, "SANDBOX_CONFIG", {})

        if os.path.exists(BRAIN_SETTINGS_PATH):
            try:
                with open(BRAIN_SETTINGS_PATH, "r", encoding="utf-8") as f:
                    brain_data = json.load(f)
                    # Lấy riêng block cấu hình Sandbox nếu có
                    if "voting_rules" in brain_data and "indicators" in brain_data:
                        return brain_data
            except Exception as e:
                logger.error(f"[SignalGen] Lỗi đọc {BRAIN_SETTINGS_PATH}: {e}. Dùng Fallback.")

        return base_config

    def _detect_market_mode(self, context: dict, payload: pd.DataFrame) -> str:
        """Nhận diện trạng thái thị trường (Gộp từ voting_engine cũ)"""
        if context.get("exhaustion_flag", False):
            return "EXHAUSTION"

        # Tìm cột ADX trong Payload (M15) để xác định độ mạnh
        adx_cols = [c for c in payload.columns if "ADX" in c]
        adx_val = payload[adx_cols[0]].iloc[-1] if adx_cols else 0

        # Đọc ngưỡng từ config (fallback 18, 23)
        adx_cfg = self.config.get("indicators", {}).get("adx", {}).get("params", {})
        weak = adx_cfg.get("weak", 18)
        strong = adx_cfg.get("strong", 23)

        if adx_val >= strong:
            return "BREAKOUT"
        if adx_val >= weak:
            return "TREND"
            
        return "RANGE"

    def _process_votes(self, votes: list, rules: dict) -> int:
        """Xử lý cơ chế bỏ phiếu (Gộp từ voting_engine cũ)"""
        if not votes:
            return 0

        buy_votes = votes.count(1)
        sell_votes = votes.count(-1)
        none_votes = votes.count(0)

        max_none = rules.get("max_none", 1)
        max_opp = rules.get("max_opposite", 0)
        master_rule = rules.get("master_rule", "FIX")

        # Luật Master Rule
        if none_votes > max_none:
            if master_rule == "FIX":
                return 0
            # Nếu là "PASS", tiếp tục đếm phiếu

        # Chống chọi (Có cả Buy và Sell)
        if buy_votes > 0 and sell_votes > 0:
            if buy_votes > sell_votes and sell_votes <= max_opp: return 1
            if sell_votes > buy_votes and buy_votes <= max_opp: return -1
            return 0

        # Thuận chiều
        if buy_votes > 0: return 1
        if sell_votes > 0: return -1
            
        return 0

    def generate_signal(self, data_package: dict) -> tuple:
        """
        Hàm cốt lõi: Quét qua các tín hiệu và trả về quyết định cuối cùng.
        Output bắt buộc: (final_signal (int), details (dict))
        """
        if not data_package or "context" not in data_package or "payload" not in data_package:
            return 0, {"error": "Invalid data package"}

        context = data_package["context"]
        payload = data_package["payload"]
        
        current_mode = self._detect_market_mode(context, payload)
        rules = self.config.get("voting_rules", {})
        inds_config = self.config.get("indicators", {})

        g2_votes = []
        g3_vetoes = []

        # Gọi các file Signal động dựa trên cấu hình
        for ind_name, ind_cfg in inds_config.items():
            if not ind_cfg.get("active", False):
                continue

            active_modes = ind_cfg.get("active_modes", ["ANY"])
            if "ANY" not in active_modes and current_mode not in active_modes:
                continue

            try:
                mod = importlib.import_module(f"signals.{ind_name}")
                params = ind_cfg.get("params", {})
                
                # Try inject context nếu file signal cần (như fibonacci, swing_point)
                try:
                    vote = mod.get_signal_vector(payload, params, context=context)
                except TypeError:
                    # Fallback cho các file signal chỉ nhận (df, params)
                    vote = mod.get_signal_vector(payload, params)
                    
            except Exception as e:
                logger.error(f"[SignalGen] Lỗi thực thi block {ind_name}: {e}")
                vote = 0

            group = ind_cfg.get("group", "G2")
            if group == "G3":
                g3_vetoes.append(vote)
            else:
                g2_votes.append(vote)

        # Logic Veto của Nhóm 3 (Ví dụ: Multi-candle báo đảo chiều thì hủy bỏ phiếu G2)
        if any(v == -1 for v in g3_vetoes):
            final_signal = 0
        else:
            final_signal = self._process_votes(g2_votes, rules)

        # Đóng gói Details (Hành trang mang sang Trade Manager)
        details = {
            "mode": current_mode,
            "trend": context.get("trend", "NONE"),
            "atr": context.get("atr", 0.0),
            "swing_high": context.get("swing_high", 0.0),
            "swing_low": context.get("swing_low", 0.0),
            "exhaustion": context.get("exhaustion_flag", False)
        }
        
        return final_signal, details