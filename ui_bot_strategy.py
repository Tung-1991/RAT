import os
import json
import customtkinter as ctk
import tkinter.messagebox as messagebox

CONFIG_PATH = "data/bot_sandbox_presets.json"

DEFAULT_CONFIG = {
    "voting_rules": {"max_opposite": 0, "max_none": 1, "master_rule": "FIX"},
    "indicators": {
        "swing_point": {"active": True, "module": "signals.swing_point", "group": "G1", "active_modes": ["ANY"], "params": {"period": 5}},
        "atr": {"active": True, "module": "signals.atr", "group": "G1", "active_modes": ["ANY"], "params": {"period": 14, "multiplier": 1.5}},
        "adx": {"active": True, "module": "signals.adx", "group": "G1", "active_modes": ["TREND", "BREAKOUT"], "params": {"period": 14, "weak": 18, "strong": 23}},
        "ema_single": {"active": True, "module": "signals.ema", "group": "G1", "active_modes": ["ANY"], "params": {"period": 50}},
        "pivot_points": {"active": False, "module": "signals.pivot_points", "group": "G3", "active_modes": ["ANY"], "params": {}},
        "ema_cross": {"active": False, "module": "signals.ema_cross", "group": "G2", "active_modes": ["TREND", "BREAKOUT"], "params": {"fast": 9, "slow": 21}},
        "volume": {"active": True, "module": "signals.volume", "group": "G2", "active_modes": ["BREAKOUT"], "params": {"period": 20, "std_dev": 2.0}},
        "supertrend": {"active": True, "module": "signals.supertrend", "group": "G2", "active_modes": ["TREND"], "params": {"period": 10, "multiplier": 3.0}},
        "psar": {"active": False, "module": "signals.psar", "group": "G2", "active_modes": ["TREND"], "params": {"step": 0.02, "max_step": 0.2}},
        "bollinger_bands": {"active": False, "module": "signals.bollinger_bands", "group": "G2", "active_modes": ["RANGE"], "params": {"period": 20, "std_dev": 2.0}},
        "fibonacci": {"active": False, "module": "signals.fibonacci", "group": "G2", "active_modes": ["RANGE", "EXHAUSTION"], "params": {"lookback": 50}},
        "rsi": {"active": False, "module": "signals.rsi", "group": "G2", "active_modes": ["RANGE"], "params": {"period": 14, "overbought": 70, "oversold": 30}},
        "stochastic": {"active": False, "module": "signals.stochastic", "group": "G2", "active_modes": ["RANGE"], "params": {"k_period": 14, "d_period": 3, "smooth": 3}},
        "macd": {"active": False, "module": "signals.macd", "group": "G2", "active_modes": ["EXHAUSTION"], "params": {"fast": 12, "slow": 26, "signal": 9}},
        "multi_candle": {"active": True, "module": "signals.multi_candle", "group": "G3", "active_modes": ["EXHAUSTION"], "params": {}}
    }
}

class BotStrategyUI(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("RAT - Kaiser Sandbox V3.0")
        self.geometry("900x650")
        self.grab_set()

        self.config = self._load_config()
        self.current_indicator = None
        self.param_entries = {}
        self.mode_vars = {}
        self.active_var = ctk.BooleanVar()

        self._build_ui()
        
        first_ind = list(self.config["indicators"].keys())[0]
        self._select_indicator(first_ind)

    def _load_config(self):
        os.makedirs("data", exist_ok=True)
        if not os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "w") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            return DEFAULT_CONFIG.copy()
        try:
            with open(CONFIG_PATH, "r") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_CONFIG.copy()

    def _save_config(self):
        self._cache_current_indicator()
        try:
            self.config["voting_rules"]["max_opposite"] = int(self.entry_max_opp.get())
            self.config["voting_rules"]["max_none"] = int(self.entry_max_none.get())
        except ValueError:
            messagebox.showerror("Error", "Rules values must be integers.")
            return
            
        self.config["voting_rules"]["master_rule"] = self.combo_master.get()

        with open(CONFIG_PATH, "w") as f:
            json.dump(self.config, f, indent=4)
        messagebox.showinfo("Saved", "Sandbox Configuration Saved Successfully!")

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=3)
        self.grid_rowconfigure(1, weight=1)

        top_frame = ctk.CTkFrame(self)
        top_frame.grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="ew")
        
        ctk.CTkLabel(top_frame, text="Max Opposite:").pack(side="left", padx=5)
        self.entry_max_opp = ctk.CTkEntry(top_frame, width=50)
        self.entry_max_opp.insert(0, str(self.config["voting_rules"].get("max_opposite", 0)))
        self.entry_max_opp.pack(side="left", padx=5)

        ctk.CTkLabel(top_frame, text="Max None:").pack(side="left", padx=5)
        self.entry_max_none = ctk.CTkEntry(top_frame, width=50)
        self.entry_max_none.insert(0, str(self.config["voting_rules"].get("max_none", 1)))
        self.entry_max_none.pack(side="left", padx=5)

        ctk.CTkLabel(top_frame, text="Master Rule:").pack(side="left", padx=5)
        self.combo_master = ctk.CTkOptionMenu(top_frame, values=["FIX", "SOFT", "PASS"], width=80)
        self.combo_master.set(self.config["voting_rules"].get("master_rule", "FIX"))
        self.combo_master.pack(side="left", padx=5)

        btn_save = ctk.CTkButton(top_frame, text="Save Sandbox", command=self._save_config, fg_color="green")
        btn_save.pack(side="right", padx=10)

        self.left_frame = ctk.CTkScrollableFrame(self, label_text="Lego Blocks")
        self.left_frame.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")

        self.right_frame = ctk.CTkFrame(self)
        self.right_frame.grid(row=1, column=1, padx=(0, 10), pady=(0, 10), sticky="nsew")

        self.lbl_ind_name = ctk.CTkLabel(self.right_frame, text="Select an Indicator", font=("Arial", 16, "bold"))
        self.lbl_ind_name.pack(pady=10)

        self.chk_active = ctk.CTkCheckBox(self.right_frame, text="Enable Indicator", variable=self.active_var)
        self.chk_active.pack(pady=10, anchor="w", padx=20)

        mode_frame = ctk.CTkFrame(self.right_frame)
        mode_frame.pack(fill="x", padx=20, pady=10)
        ctk.CTkLabel(mode_frame, text="Active Modes (Tags):").pack(anchor="w", padx=5, pady=5)
        
        self.mode_container = ctk.CTkFrame(mode_frame, fg_color="transparent")
        self.mode_container.pack(fill="x", padx=5, pady=5)
        
        modes = ["TREND", "RANGE", "BREAKOUT", "EXHAUSTION", "ANY"]
        for m in modes:
            var = ctk.StringVar(value="")
            chk = ctk.CTkCheckBox(self.mode_container, text=m, variable=var, onvalue=m, offvalue="")
            chk.pack(side="left", padx=10)
            self.mode_vars[m] = {"widget": chk, "var": var}

        self.params_frame = ctk.CTkScrollableFrame(self.right_frame, label_text="Dynamic Parameters")
        self.params_frame.pack(fill="both", expand=True, padx=20, pady=10)

        for ind in self.config["indicators"].keys():
            btn = ctk.CTkButton(self.left_frame, text=ind.upper(), command=lambda i=ind: self._select_indicator(i))
            btn.pack(pady=5, padx=5, fill="x")

    def _cache_current_indicator(self):
        if not self.current_indicator:
            return
        
        ind_data = self.config["indicators"][self.current_indicator]
        ind_data["active"] = self.active_var.get()
        
        active_modes = [m for m, d in self.mode_vars.items() if d["var"].get() == m]
        ind_data["active_modes"] = active_modes

        for p_name, entry in self.param_entries.items():
            val_str = entry.get()
            try:
                if "." in val_str:
                    ind_data["params"][p_name] = float(val_str)
                else:
                    ind_data["params"][p_name] = int(val_str)
            except ValueError:
                ind_data["params"][p_name] = val_str

    def _select_indicator(self, ind_name):
        self._cache_current_indicator()
        self.current_indicator = ind_name
        self.lbl_ind_name.configure(text=f"Settings: {ind_name.upper()}")
        
        ind_data = self.config["indicators"][ind_name]
        self.active_var.set(ind_data.get("active", False))

        active_modes = ind_data.get("active_modes", [])
        for m, d in self.mode_vars.items():
            d["var"].set(m if m in active_modes else "")

        for widget in self.params_frame.winfo_children():
            widget.destroy()
        
        self.param_entries.clear()
        
        for p_name, p_val in ind_data.get("params", {}).items():
            row = ctk.CTkFrame(self.params_frame, fg_color="transparent")
            row.pack(fill="x", pady=5)
            ctk.CTkLabel(row, text=p_name, width=150, anchor="w").pack(side="left", padx=5)
            entry = ctk.CTkEntry(row)
            entry.insert(0, str(p_val))
            entry.pack(side="left", fill="x", expand=True, padx=5)
            self.param_entries[p_name] = entry