# -*- coding: utf-8 -*-
# FILE: signals/signal_generator.py
# V4.1: 4-TIER PIPELINE, DYNAMIC MACRO MODE SENSOR (KAISER EDITION)

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
        
        self.indicator_map = {
            "RSI": rsi_signal, "MACD": macd_signal, "BollingerBands": bollinger_bands_signal,
            "EMA": ema_signal, "EMACross": ema_cross_signal, "Stochastic": stochastic_signal,
            "ATR": atr_signal, "ADX": adx_signal, "SuperTrend": supertrend_signal,
            "ParabolicSAR": psar_signal, "Volume": volume_signal, "MultiCandle": multi_candle_signal,
            "CandlePattern": candle_pattern_signal, "SwingPoint": swing_point_signal,
            "Fibonacci": fibonacci_signal, "PivotPoints": pivot_points_signal
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

    def _detect_market_mode(self, dfs, context, inds_config=None, voting_rules=None):
        """
        V4.1: Cảm biến Vĩ mô Động (Dynamic Macro Sensor)
        - Hỗ trợ ngược (Backward Compatible): Nếu truyền DF cũ, dùng ADX cứng.
        - Bản mới: Tự động gom các Indicator của G0 (hoặc G1) để Vote ra Trend/Mode.
        """
        # Nếu chạy bản cũ (truyền vào DataFrame thay vì Dict)
        if not isinstance(dfs, dict):
            df = dfs
            try:
                adx_val = df[f"ADX_{14}"].iloc[-1] if f"ADX_{14}" in df.columns else 0
                if adx_val > 25:
                    return "BREAKOUT" if adx_val > 40 else "TREND"
                else:
                    return "RANGE"
            except:
                return "ANY"
                
        # --- LOGIC V4.1 DYNAMIC MACRO MODE ---
        if not inds_config or not voting_rules: 
            return "ANY", "NONE", 0

        # 1. Quét tìm các Indicator được gán cho G0 (Ưu tiên 1)
        g0_inds = {k: v for k, v in inds_config.items() if v.get("active") and v.get("group") == "G0"}
        
        source_grp = "G0"
        macro_inds = g0_inds
        
        # 2. Cơ chế Fallback: Nếu G0 trống, lấy G1 làm la bàn vĩ mô
        if not macro_inds:
            source_grp = "G1"
            macro_inds = {k: v for k, v in inds_config.items() if v.get("active") and v.get("group") == "G1"}
            
        df_eval = dfs.get(source_grp)
        if df_eval is None or df_eval.empty or not macro_inds:
            return "ANY", "NONE", 0
            
        # 3. Lấy luật phân xử (Rules) của nhóm đó
        rules = voting_rules.get(source_grp, {"max_opposite": 0, "max_none": 0})
        
        # 4. Chạy Vote để xem Trend Vĩ Mô đang là gì
        direction = self._evaluate_group(source_grp, macro_inds, df_eval, context, "ANY", rules)
        
        # 5. Xác định Mode (1/-1 là TREND, 0 là RANGE - Sideway giằng co)
        mode = "TREND" if direction != 0 else "RANGE"
        
        # Phân tách Breakout (Tùy chọn: Nếu người dùng có nhét ADX vào nhóm Macro và trị số > 40)
        try:
            adx_cfg = macro_inds.get("adx")
            if adx_cfg:
                p = adx_cfg.get("params", {}).get("period", 14)
                if f"ADX_{p}" in df_eval.columns:
                    adx_val = df_eval[f"ADX_{p}"].iloc[-1]
                    if adx_val > 40:
                        mode = "BREAKOUT"
        except:
            pass
            
        return mode, source_grp, direction

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

    # =========================================================================
    # PIPELINE V4.0: ÁNH XẠ MULTI-TF + EARLY-EXIT + VETO/VOTING
    # =========================================================================
    def _evaluate_pipeline_v4(self, dfs, context, current_mode, voting_rules, active_inds):
        eval_mode = getattr(config, "MASTER_EVAL_MODE", "VETO")
        min_votes = getattr(config, "MIN_MATCHING_VOTES", 3)
        votes = {}

        # Duyệt tuần tự từ trên xuống để tối ưu CPU (Early-Exit)
        for grp in ["G0", "G1", "G2", "G3"]:
            rule = voting_rules.get(grp, {}).get("master_rule", "IGNORE")
            if rule == "IGNORE": continue
            
            df_grp = dfs.get(grp)
            if df_grp is None or df_grp.empty:
                if rule == "FIX": return 0 
                continue

            status = self._evaluate_group(grp, active_inds[grp], df_grp, context, current_mode, voting_rules.get(grp, {}))
            votes[grp] = status

            # CHẶN LẬP TỨC nếu chế độ là VETO
            if eval_mode == "VETO":
                if rule == "FIX" and status == 0:
                    return 0 
                
                active_votes = [v for v in votes.values() if v != 0]
                if len(set(active_votes)) > 1:
                    return 0 

        # Xử lý tổng hợp kết quả
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
        
        # V4.1 Dynamic Macro Detection
        current_mode, mode_src, macro_dir = self._detect_market_mode(dfs, context, inds_config, voting_rules)
        
        # Lưu lại để truyền ra ngoài Daemon & Giao diện UI
        context["market_mode"] = current_mode
        context["mode_source"] = mode_src
        context["macro_direction"] = macro_dir

        active_inds_by_group = {"G0": {}, "G1": {}, "G2": {}, "G3": {}}
        for name, cfg in inds_config.items():
            if cfg.get("active", False):
                modes = cfg.get("active_modes", ["ANY"])
                if "ANY" in modes or current_mode in modes:
                    grp = cfg.get("group", "G2")
                    if grp in active_inds_by_group:
                        active_inds_by_group[grp][name] = cfg

        return self._evaluate_pipeline_v4(dfs, context, current_mode, voting_rules, active_inds_by_group)

    # =========================================================================
    # HÀM CŨ (GIỮ NGUYÊN ĐỂ KHÔNG CRASH DAEMON CŨ CHƯA KỊP CẬP NHẬT)
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
        
        current_mode = self._detect_market_mode(df_trend, context)

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