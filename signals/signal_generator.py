# -*- coding: utf-8 -*-
# FILE: signals/signal_generator.py
# V3.0: 2-TIER VOTING SYSTEM (KAISER EDITION)

import logging
import json
import os
import config

logger = logging.getLogger("SignalGenerator")

# Import tất cả các indicator
from signals.rsi import rsi_signal
from signals.macd import macd_signal
from signals.bollinger_bands import bollinger_bands_signal
from signals.ema import ema_signal
from signals.ema_cross import ema_cross_signal
from signals.stochastic import stochastic_signal
from signals.atr import atr_signal
from signals.adx import adx_signal
from signals.supertrend import supertrend_signal
from signals.psar import psar_signal
from signals.volume import volume_signal
from signals.multi_candle import multi_candle_signal
from signals.candle import candle_pattern_signal
from signals.swing_point import swing_point_signal
from signals.fibonacci import fibonacci_signal
from signals.pivot_points import pivot_points_signal

class SignalGenerator:
    def __init__(self):
        self.brain_path = "data/brain_settings.json"
        
        # Ánh xạ tên trong file JSON với hàm thực tế
        self.indicator_map = {
            "RSI": rsi_signal,
            "MACD": macd_signal,
            "BollingerBands": bollinger_bands_signal,
            "EMA": ema_signal,
            "EMACross": ema_cross_signal,
            "Stochastic": stochastic_signal,
            "ATR": atr_signal,
            "ADX": adx_signal,
            "SuperTrend": supertrend_signal,
            "ParabolicSAR": psar_signal,
            "Volume": volume_signal,
            "MultiCandle": multi_candle_signal,
            "CandlePattern": candle_pattern_signal,
            "SwingPoint": swing_point_signal,
            "Fibonacci": fibonacci_signal,
            "PivotPoints": pivot_points_signal
        }

    def _get_brain_settings(self):
        try:
            if os.path.exists(self.brain_path):
                with open(self.brain_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi đọc {self.brain_path}: {e}")
            
        # Fallback về config RAM nếu file lỗi
        return {
            "voting_rules": {
                "G1": {"max_opposite": 0, "max_none": 0, "master_rule": "FIX"},
                "G2": {"max_opposite": 0, "max_none": 1, "master_rule": "FIX"},
                "G3": {"max_opposite": 0, "max_none": 1, "master_rule": "IGNORE"}
            },
            "indicators": getattr(config, "SANDBOX_CONFIG", {}).get("indicators", {})
        }

    def _detect_market_mode(self, df, context):
        """Phát hiện Market Mode cơ bản dựa vào ADX (để tắt/bật indicator)"""
        try:
            from signals.adx import calculate_adx
            adx_val = calculate_adx(df, 14)
            if adx_val > 25:
                return "BREAKOUT" if adx_val > 40 else "TREND"
            else:
                return "RANGE"
        except:
            return "ANY"

    def _evaluate_group(self, group_name, group_indicators, df, context, current_mode, rules):
        """
        Tầng 1: Đánh giá một Group cụ thể.
        Trả về trạng thái của Group: 1 (BUY), -1 (SELL), hoặc 0 (NONE).
        """
        if not group_indicators:
            return 0 # Không có indicator nào hoạt động trong group này

        votes = []
        for ind_name, ind_cfg in group_indicators.items():
            # Chạy hàm indicator
            func = self.indicator_map.get(ind_name)
            if func:
                try:
                    params = ind_cfg.get("params", {})
                    # Chỉ báo cần context (như Fibonacci) hoặc chỉ cần df
                    if ind_name in ["Fibonacci", "PivotPoints", "SwingPoint"]:
                         signal = func(df, context, **params)
                    else:
                         signal = func(df, **params)
                    votes.append(signal)
                except Exception as e:
                    logger.error(f"Lỗi tính toán {ind_name}: {e}")
                    votes.append(0)

        if not votes: return 0

        total_buy = sum(1 for v in votes if v == 1)
        total_sell = sum(1 for v in votes if v == -1)
        total_none = sum(1 for v in votes if v == 0)

        max_opp = rules.get("max_opposite", 0)
        max_none = rules.get("max_none", 1)

        # Quyết định hướng chính của Group (ưu tiên bên nào đông hơn)
        if total_buy > 0 and total_buy >= total_sell:
            main_direction = 1
            opp_count = total_sell
        elif total_sell > 0 and total_sell > total_buy:
            main_direction = -1
            opp_count = total_buy
        else:
             # Bằng nhau hoặc toàn 0
            return 0

        # Kiểm tra luật lệ của Group
        if opp_count <= max_opp and total_none <= max_none:
            return main_direction
        
        return 0 # Fail luật -> Group trả về NONE


    def _evaluate_master_rules(self, g1_status, g2_status, g3_status, voting_rules):
        """
        Tầng 2: Áp dụng Master Rules để ra quyết định cuối cùng.
        """
        groups_status = {
            "G1": g1_status,
            "G2": g2_status,
            "G3": g3_status
        }
        
        final_direction = 0
        
        # Bước 1: Tìm hướng tiềm năng (Bỏ qua các group IGNORE và NONE)
        potential_directions = []
        for grp in ["G1", "G2", "G3"]:
            rule = voting_rules.get(grp, {}).get("master_rule", "FIX")
            status = groups_status[grp]
            if rule != "IGNORE" and status != 0:
                potential_directions.append(status)
                
        # Nếu không ai có ý kiến, hoặc ý kiến trái chiều từ đầu -> Bỏ
        if not potential_directions: return 0
        if len(set(potential_directions)) > 1: return 0 # G1 đòi BUY, G2 đòi SELL
        
        final_direction = potential_directions[0]
        
        # Bước 2: Kiểm tra khắt khe theo Master Rule
        for grp in ["G1", "G2", "G3"]:
            rule = voting_rules.get(grp, {}).get("master_rule", "FIX")
            status = groups_status[grp]
            
            if rule == "FIX":
                # Bắt buộc phải đồng thuận hướng lệnh. Nếu khác hoặc NONE -> Phá vỡ
                if status != final_direction:
                    return 0
            elif rule == "PASS":
                # Có ý kiến thì phải thuận, không thì được quyền im lặng (NONE)
                if status != 0 and status != final_direction:
                    return 0
            elif rule == "IGNORE":
                 pass # Kệ mẹ nó

        return final_direction


    def generate_signal(self, df_entry, df_trend, context):
        """
        Hàm chính được DataEngine gọi.
        """
        settings = self._get_brain_settings()
        voting_rules = settings.get("voting_rules", {})
        inds_config = settings.get("indicators", {})

        current_mode = self._detect_market_mode(df_trend, context)

        # Lọc các indicator đang Active và hợp Mode
        active_inds_by_group = {"G1": {}, "G2": {}, "G3": {}}
        
        for name, cfg in inds_config.items():
            if cfg.get("active", False):
                modes = cfg.get("active_modes", ["ANY"])
                if "ANY" in modes or current_mode in modes:
                    grp = cfg.get("group", "G2")
                    if grp in active_inds_by_group:
                        active_inds_by_group[grp][name] = cfg

        # Tầng 1: Đánh giá từng Group
        g1_status = self._evaluate_group("G1", active_inds_by_group["G1"], df_entry, context, current_mode, voting_rules.get("G1", {}))
        g2_status = self._evaluate_group("G2", active_inds_by_group["G2"], df_entry, context, current_mode, voting_rules.get("G2", {}))
        g3_status = self._evaluate_group("G3", active_inds_by_group["G3"], df_entry, context, current_mode, voting_rules.get("G3", {}))

        logger.debug(f"[2-Tier Vote] Mode: {current_mode} | G1: {g1_status}, G2: {g2_status}, G3: {g3_status}")

        # Tầng 2: Ra quyết định sinh tử
        final_signal = self._evaluate_master_rules(g1_status, g2_status, g3_status, voting_rules)
        
        return final_signal

# Singleton instance
signal_generator = SignalGenerator()