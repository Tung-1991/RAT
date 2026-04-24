# -*- coding: utf-8 -*-
# FILE: signals/signal_generator.py
# V4.2.1: MULTI-GROUP, DYNAMIC MACRO & TREND COMPASS (KAISER EDITION)

import logging
import json
import os
import config

logger = logging.getLogger("SignalGenerator")

from signals.rsi import get_signal_vector as rsi_signal
from signals.macd import get_signal_vector as macd_signal
from signals.bollinger_bands import get_signal_vector as bollinger_bands_signal
from signals.ema import get_signal_vector as ema_signal
from signals.ema_cross import get_signal_vector as ema_cross_signal
from signals.stochastic import get_signal_vector as stochastic_signal
from signals.atr import get_signal_vector as atr_signal
from signals.adx import get_signal_vector as adx_signal
from signals.supertrend import get_signal_vector as supertrend_signal
from signals.psar import get_signal_vector as psar_signal
from signals.volume import get_signal_vector as volume_signal
from signals.multi_candle import get_signal_vector as multi_candle_signal
from signals.candle import get_signal_vector as candle_pattern_signal
from signals.swing_point import get_signal_vector as swing_point_signal
from signals.fibonacci import get_signal_vector as fibonacci_signal
from signals.pivot_points import get_signal_vector as pivot_points_signal

class SignalGenerator:
    def __init__(self):
        self.brain_path = "data/brain_settings.json"
        
        # Đồng bộ toàn bộ Key về chữ thường khớp với cấu hình JSON từ UI
        self.indicator_map = {
            "rsi": rsi_signal, "macd": macd_signal, "bollinger_bands": bollinger_bands_signal,
            "ema": ema_signal, "ema_cross": ema_cross_signal, "stochastic": stochastic_signal,
            "atr": atr_signal, "adx": adx_signal, "supertrend": supertrend_signal,
            "psar": psar_signal, "volume": volume_signal, "multi_candle": multi_candle_signal,
            "candle": candle_pattern_signal, "swing_point": swing_point_signal,
            "fibonacci": fibonacci_signal, "pivot_points": pivot_points_signal
        }

    def _get_brain_settings(self):
        try:
            if os.path.exists(self.brain_path):
                with open(self.brain_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Lỗi đọc {self.brain_path}: {e}")
            
        return {
            "voting_rules": {
                "G0": {"max_opposite": 0, "max_none": 0, "master_rule": "PASS"},
                "G1": {"max_opposite": 0, "max_none": 0, "master_rule": "FIX"},
                "G2": {"max_opposite": 0, "max_none": 1, "master_rule": "FIX"},
                "G3": {"max_opposite": 0, "max_none": 1, "master_rule": "IGNORE"}
            },
            "indicators": getattr(config, "SANDBOX_CONFIG", {}).get("indicators", {})
        }

    def _detect_dynamic_trend(self, dfs, context, inds_config, eval_mode="VETO", min_votes=3):
        """
        V4.2.2: Trend Cục Bộ - Tách biệt độc lập theo từng Group
        Trả về dict: {"G0": "UP", "G1": "NONE", "G2": "DOWN", "G3": "NONE"}
        """
        if not inds_config: return {g: "NONE" for g in ["G0", "G1", "G2", "G3"]}

        group_trends = {"G0": "NONE", "G1": "NONE", "G2": "NONE", "G3": "NONE"}

        for target_grp in ["G0", "G1", "G2", "G3"]:
            trend_votes = []
            for ind_name, cfg in inds_config.items():
                if cfg.get("active") and cfg.get("is_trend", False):
                    groups = cfg.get("groups", [cfg.get("group", "G2")])
                    
                    # CHỈ lấy phiếu bầu của Indicator nếu nó thuộc Group đang xét
                    if target_grp in groups: 
                        df_eval = dfs.get(target_grp)
                        if df_eval is not None and not df_eval.empty:
                            dummy_rules = {"max_opposite": 0, "max_none": 0}
                            vote = self._evaluate_group(target_grp, {ind_name: cfg}, df_eval, context, "ANY", dummy_rules)
                            if vote != 0:
                                trend_votes.append(vote)

            if not trend_votes:
                continue # Giữ là NONE

            # Phân xử riêng cho Group này
            if eval_mode == "VETO":
                if all(v == 1 for v in trend_votes): group_trends[target_grp] = "UP"
                elif all(v == -1 for v in trend_votes): group_trends[target_grp] = "DOWN"
            
            elif eval_mode == "VOTING":
                buy_votes = sum(1 for v in trend_votes if v == 1)
                sell_votes = sum(1 for v in trend_votes if v == -1)
                
                # Giới hạn min_votes theo tổng số indicator được bật để chống kẹt NONE
                actual_min = min(min_votes, len(trend_votes))
                
                if buy_votes >= actual_min and buy_votes > sell_votes: group_trends[target_grp] = "UP"
                elif sell_votes >= actual_min and sell_votes > buy_votes: group_trends[target_grp] = "DOWN"

        return group_trends

    def _detect_market_mode(self, dfs, context, inds_config=None, voting_rules=None):
        """
        V4.2: Cảm biến Vĩ mô Động - 2 Bước
        Bước 1: Tính Base Mode (TREND/RANGE)
        Bước 2: Các Indicator bắt Breakout/Exhaustion chà đạp lên kết quả
        """
        if not isinstance(dfs, dict):
            return "ANY", "NONE", 0
                
        if not inds_config or not voting_rules: 
            return "ANY", "NONE", 0

        # 1. Tìm nhóm Macro (Ưu tiên các Indicator ở G0, nếu không thì G1)
        g0_inds = {k: v for k, v in inds_config.items() if v.get("active") and "G0" in v.get("groups", [v.get("group", "G2")])}
        source_grp = "G0"
        macro_inds = g0_inds
        
        if not macro_inds:
            source_grp = "G1"
            macro_inds = {k: v for k, v in inds_config.items() if v.get("active") and "G1" in v.get("groups", [v.get("group", "G2")])}
            
        df_eval = dfs.get(source_grp)
        if df_eval is None or df_eval.empty or not macro_inds:
            return "ANY", "NONE", 0
            
        rules = voting_rules.get(source_grp, {"max_opposite": 0, "max_none": 0})
        
        # 2. Phân loại theo Vai trò Macro (Macro Role)
        base_inds = {k: v for k, v in macro_inds.items() if v.get("macro_role", "NONE") == "BASE"}
        brk_inds = {k: v for k, v in macro_inds.items() if v.get("macro_role", "NONE") == "BREAKOUT"}
        exh_inds = {k: v for k, v in macro_inds.items() if v.get("macro_role", "NONE") == "EXHAUSTION"}

        # BƯỚC 1: ĐỊNH HÌNH BASE MODE (TREND HAY RANGE)
        base_dir = 0
        if base_inds:
            base_dir = self._evaluate_group(source_grp, base_inds, df_eval, context, "ANY", rules)
            
        mode = "TREND" if base_dir != 0 else "RANGE"

        # BƯỚC 2: GHI ĐÈ ĐỘT BIẾN (BREAKOUT / EXHAUSTION)
        if brk_inds:
            brk_dir = self._evaluate_group(source_grp, brk_inds, df_eval, context, "ANY", rules)
            if brk_dir != 0:
                mode = "BREAKOUT"
                
        if exh_inds and mode != "BREAKOUT": # Ưu tiên Breakout hơn nếu có xung đột, hoặc để song song
            exh_dir = self._evaluate_group(source_grp, exh_inds, df_eval, context, "ANY", rules)
            if exh_dir != 0:
                mode = "EXHAUSTION"
            
        return mode, source_grp, base_dir

    def _evaluate_group(self, group_name, group_indicators, df, context, current_mode, rules):
        if not group_indicators or df is None or df.empty: return 0

        votes = []
        for ind_name, ind_cfg in group_indicators.items():
            func = self.indicator_map.get(ind_name)
            if func:
                try:
                    params = ind_cfg.get("params", {})
                    trigger_mode = ind_cfg.get("trigger_mode", "STRICT_CLOSE")
                    
                    # Cắt đuôi nến nếu là STRICT_CLOSE để khóa cản tĩnh, chống repaint
                    eval_df = df.iloc[:-1] if trigger_mode == "STRICT_CLOSE" else df
                    if eval_df.empty: continue
                    
                    if ind_name in ["Fibonacci", "PivotPoints", "SwingPoint"]:
                         signal = func(eval_df, params, context)
                    else:
                         signal = func(eval_df, params)
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

        if total_buy > 0 and total_buy >= total_sell:
            main_direction = 1
            opp_count = total_sell
        elif total_sell > 0 and total_sell > total_buy:
            main_direction = -1
            opp_count = total_buy
        else:
            return 0

        if opp_count <= max_opp and total_none <= max_none:
            return main_direction
        return 0

    def _evaluate_pipeline_v4(self, dfs, context, current_mode, voting_rules, active_inds):
        eval_mode = getattr(config, "MASTER_EVAL_MODE", "VETO")
        min_votes = getattr(config, "MIN_MATCHING_VOTES", 3)
        votes = {}

        for grp in ["G0", "G1", "G2", "G3"]:
            rule = voting_rules.get(grp, {}).get("master_rule", "IGNORE")
            if rule == "IGNORE": continue
            
            df_grp = dfs.get(grp)
            if df_grp is None or df_grp.empty:
                if rule == "FIX": return 0 
                continue

            status = self._evaluate_group(grp, active_inds[grp], df_grp, context, current_mode, voting_rules.get(grp, {}))
            votes[grp] = status

            if eval_mode == "VETO":
                if rule == "FIX" and status == 0:
                    return 0 
                
                active_votes = [v for v in votes.values() if v != 0]
                if len(set(active_votes)) > 1:
                    return 0 

        if eval_mode == "VETO":
            active_votes = [v for v in votes.values() if v != 0]
            if not active_votes: return 0
            final_dir = active_votes[0]
            for grp, status in votes.items():
                rule = voting_rules.get(grp, {}).get("master_rule", "IGNORE")
                if rule == "FIX" and status != final_dir: return 0
            return final_dir
        
        elif eval_mode == "VOTING":
            buy_votes = sum(1 for v in votes.values() if v == 1)
            sell_votes = sum(1 for v in votes.values() if v == -1)
            
            if buy_votes >= min_votes and buy_votes > sell_votes: return 1
            if sell_votes >= min_votes and sell_votes > buy_votes: return -1
            return 0
        
        return 0

    def generate_signal_v4(self, dfs, context):
        settings = self._get_brain_settings()
        voting_rules = settings.get("voting_rules", {})
        inds_config = settings.get("indicators", {})
        
        eval_mode = getattr(config, "MASTER_EVAL_MODE", settings.get("MASTER_EVAL_MODE", "VETO"))
        min_votes = getattr(config, "MIN_MATCHING_VOTES", settings.get("MIN_MATCHING_VOTES", 3))
        
        # 1. Tính Dynamic Trend Compass Cục Bộ
        group_trends = self._detect_dynamic_trend(dfs, context, inds_config, eval_mode, min_votes)
        
        # Đóng gói Trend từng khung vào Context để Bot UI Dashboard đọc được
        for g, t in group_trends.items():
            context[f"trend_{g}"] = t
            
        context["real_trend"] = group_trends.get("G0", "NONE") # Giữ fallback 
        
        # 2. Tính Market Mode V4.2
        current_mode, mode_src, macro_dir = self._detect_market_mode(dfs, context, inds_config, voting_rules)
        
        context["market_mode"] = current_mode
        context["mode_source"] = mode_src
        context["macro_direction"] = macro_dir

        # 3. Phân bổ Indicator vào các Group
        active_inds_by_group = {"G0": {}, "G1": {}, "G2": {}, "G3": {}}
        for name, cfg in inds_config.items():
            if cfg.get("active", False):
                modes = cfg.get("active_modes", ["ANY"])
                if "ANY" in modes or current_mode in modes:
                    groups = cfg.get("groups", [cfg.get("group", "G2")])
                    for grp in groups:
                        if grp in active_inds_by_group:
                            active_inds_by_group[grp][name] = cfg

        # 4. Đẩy vào Phễu Vote
        return self._evaluate_pipeline_v4(dfs, context, current_mode, voting_rules, active_inds_by_group)

    # =========================================================================
    # HÀM CŨ (GIỮ LẠI ĐỂ BACKWARD-COMPATIBLE KHÔNG CRASH)
    # =========================================================================
    def _evaluate_master_rules(self, g1_status, g2_status, g3_status, voting_rules):
        groups_status = {"G1": g1_status, "G2": g2_status, "G3": g3_status}
        final_direction = 0
        potential_directions = []
        for grp in ["G1", "G2", "G3"]:
            rule = voting_rules.get(grp, {}).get("master_rule", "FIX")
            status = groups_status[grp]
            if rule != "IGNORE" and status != 0:
                potential_directions.append(status)
                
        if not potential_directions: return 0
        if len(set(potential_directions)) > 1: return 0
        final_direction = potential_directions[0]
        
        for grp in ["G1", "G2", "G3"]:
            rule = voting_rules.get(grp, {}).get("master_rule", "FIX")
            status = groups_status[grp]
            if rule == "FIX" and status != final_direction: return 0
            elif rule == "PASS" and status != 0 and status != final_direction: return 0

        return final_direction

    def generate_signal(self, df_entry, df_trend, context):
        settings = self._get_brain_settings()
        voting_rules = settings.get("voting_rules", {})
        inds_config = settings.get("indicators", {})
        
        current_mode, _, _ = self._detect_market_mode(df_trend, context)

        active_inds_by_group = {"G1": {}, "G2": {}, "G3": {}}
        for name, cfg in inds_config.items():
            if cfg.get("active", False):
                modes = cfg.get("active_modes", ["ANY"])
                if "ANY" in modes or current_mode in modes:
                    grp = cfg.get("group", "G2")
                    if grp in active_inds_by_group:
                        active_inds_by_group[grp][name] = cfg

        g1_status = self._evaluate_group("G1", active_inds_by_group["G1"], df_entry, context, current_mode, voting_rules.get("G1", {}))
        g2_status = self._evaluate_group("G2", active_inds_by_group["G2"], df_entry, context, current_mode, voting_rules.get("G2", {}))
        g3_status = self._evaluate_group("G3", active_inds_by_group["G3"], df_entry, context, current_mode, voting_rules.get("G3", {}))

        return self._evaluate_master_rules(g1_status, g2_status, g3_status, voting_rules)

signal_generator = SignalGenerator()