import json
import os
import logging
from core.voting_engine import VotingEngine

logger = logging.getLogger("ExnessBot")
CONFIG_PATH = "data/bot_sandbox_presets.json"

class SignalGenerator:
    def __init__(self):
        self.config = self._load_config()
        self.voting_engine = VotingEngine(self.config)

    def _load_config(self) -> dict:
        if os.path.exists(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Sandbox config load error: {e}")
        return {}

    def reload_config(self):
        self.config = self._load_config()
        self.voting_engine = VotingEngine(self.config)

    def generate_signal(self, data_package: dict) -> tuple:
        if not data_package or "context" not in data_package or "payload" not in data_package:
            return 0, {"error": "Invalid data package"}

        context = data_package["context"]
        payload = data_package["payload"]
        
        final_signal = self.voting_engine.run_pipeline(payload, context)
        current_mode = self.voting_engine._detect_market_mode(context)
        
        details = {
            "mode": current_mode,
            "adx": round(context.get("adx", 0), 2),
            "trend": context.get("trend", "NONE"),
            "exhaustion": context.get("exhaustion_flag", False),
            "volatility_exp": context.get("volatility_expansion", False),
            "atr": round(context.get("atr", 0), 5),
            "swing_h": context.get("swing_high", 0),
            "swing_l": context.get("swing_low", 0),
            "signal_vector": final_signal
        }
        
        return final_signal, details