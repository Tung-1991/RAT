import importlib
import logging

logger = logging.getLogger("ExnessBot")

class VotingEngine:
    def __init__(self, sandbox_config: dict):
        self.config = sandbox_config
        self.voting_rules = self.config.get("voting_rules", {
            "max_opposite": 0,
            "max_none": 1,
            "master_rule": "FIX"
        })
        self.indicators = self.config.get("indicators", {})

    def _detect_market_mode(self, context_data: dict) -> str:
        adx = context_data.get("adx", 0)
        adx_weak = self.config.get("adx_weak", 18)
        adx_strong = self.config.get("adx_strong", 23)
        volatility_expansion = context_data.get("volatility_expansion", False)
        exhaustion_flag = context_data.get("exhaustion_flag", False)

        if exhaustion_flag:
            return "EXHAUSTION"
        if adx >= adx_strong and volatility_expansion:
            return "BREAKOUT"
        if adx >= adx_weak:
            return "TREND"
        return "RANGE"

    def _execute_indicator(self, ind_name: str, ind_cfg: dict, data_payload: dict) -> int:
        try:
            module_name = ind_cfg.get("module")
            func_name = ind_cfg.get("func", "get_signal_vector")
            params = ind_cfg.get("params", {})
            
            mod = importlib.import_module(module_name)
            func = getattr(mod, func_name)
            
            return func(data_payload, params)
        except Exception as e:
            logger.error(f"[VotingEngine] Fail {ind_name}: {e}")
            return 0

    def _process_group_votes(self, votes: list) -> int:
        if not votes:
            return 0

        buy_votes = votes.count(1)
        sell_votes = votes.count(-1)
        none_votes = votes.count(0)

        if none_votes > self.voting_rules["max_none"]:
            if self.voting_rules["master_rule"] == "FIX":
                return 0
            elif self.voting_rules["master_rule"] == "PASS":
                pass 

        if buy_votes > 0 and sell_votes > 0:
            if buy_votes > sell_votes and sell_votes <= self.voting_rules["max_opposite"]:
                return 1
            if sell_votes > buy_votes and buy_votes <= self.voting_rules["max_opposite"]:
                return -1
            return 0

        if buy_votes > 0:
            return 1
        if sell_votes > 0:
            return -1
            
        return 0

    def run_pipeline(self, data_payload: dict, context_data: dict) -> int:
        current_mode = self._detect_market_mode(context_data)
        
        g2_votes = []
        g3_vetoes = []

        for ind_name, ind_cfg in self.indicators.items():
            active_modes = ind_cfg.get("active_modes", [])
            group = ind_cfg.get("group", "G2")

            if "ANY" not in active_modes and current_mode not in active_modes:
                continue

            vote = self._execute_indicator(ind_name, ind_cfg, data_payload)

            if group == "G3":
                g3_vetoes.append(vote)
            else:
                g2_votes.append(vote)

        if any(v == -1 for v in g3_vetoes):
            return 0

        final_signal = self._process_group_votes(g2_votes)
        
        return final_signal