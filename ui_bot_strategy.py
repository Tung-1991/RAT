# -*- coding: utf-8 -*-
# FILE: ui_bot_strategy.py
# V4.3: UNIFIED BOT STRATEGY UI - DYNAMIC MACRO, SCALPING & STRICT RISK (KAISER EDITION)

import customtkinter as ctk
import json
import os
import config
from tkinter import messagebox, filedialog
from ui_indicators_config import open_indicator_config_popup

BRAIN_SETTINGS_PATH = "data/brain_settings.json"
TEMPLATE_DIR = "data/templates"


class BotStrategyUI(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title(
            "🧠 V4.4 Bot Strategy Sandbox (Professional Template & Advanced TSL)"
        )
        self.geometry("1150x800")
        self.attributes("-topmost", True)
        self.focus_force()

        os.makedirs(TEMPLATE_DIR, exist_ok=True)

        self.brain_data = self._load_brain_data()
        self.ind_widgets = {}
        self.vote_widgets = {}
        self.risk_widgets = {}
        self.tf_vars = {}

        self._build_ui()

    def _load_brain_data(self):
        base_data = {
            "MASTER_EVAL_MODE": getattr(config, "MASTER_EVAL_MODE", "VETO"),
            "MIN_MATCHING_VOTES": getattr(config, "MIN_MATCHING_VOTES", 3),
            "FORCE_ANY_MODE": getattr(
                config, "FORCE_ANY_MODE", False
            ),  # [NEW]: Chế độ Scalping
            "G0_TIMEFRAME": getattr(config, "G0_TIMEFRAME", "1d"),
            "G1_TIMEFRAME": getattr(config, "G1_TIMEFRAME", "1h"),
            "G2_TIMEFRAME": getattr(config, "G2_TIMEFRAME", "15m"),
            "G3_TIMEFRAME": getattr(config, "G3_TIMEFRAME", "15m"),
            "voting_rules": {
                "G0": {"max_opposite": 0, "max_none": 0, "master_rule": "PASS"},
                "G1": {"max_opposite": 0, "max_none": 0, "master_rule": "FIX"},
                "G2": {"max_opposite": 0, "max_none": 1, "master_rule": "FIX"},
                "G3": {"max_opposite": 0, "max_none": 1, "master_rule": "IGNORE"},
            },
            "risk_tsl": {
                "base_risk": getattr(config, "BOT_RISK_PERCENT", 0.3),
                "base_sl": "G2",
                "sl_atr_multiplier": getattr(config, "sl_atr_multiplier", 0.2),
                "tsl_mode": getattr(config, "TSL_LOGIC_MODE", "STATIC"),
                "bot_tsl": getattr(config, "BOT_DEFAULT_TSL", "BE+STEP_R+SWING"),
                "mode_multipliers": {
                    "TREND": 1.0,
                    "RANGE": 0.5,
                    "BREAKOUT": 1.5,
                    "EXHAUSTION": 1.0,
                    "ANY": 1.0,
                },
                "strict_risk": getattr(
                    config, "STRICT_RISK_CALC", False
                ),  # [NEW]: Trừ phí
            },
            "indicators": getattr(config, "SANDBOX_CONFIG", {}).get("indicators", {}),
            "dca_config": getattr(config, "DCA_CONFIG", {}),
            "pca_config": getattr(config, "PCA_CONFIG", {}),
        }

        if os.path.exists(BRAIN_SETTINGS_PATH):
            try:
                with open(BRAIN_SETTINGS_PATH, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)

                    for key in [
                        "MASTER_EVAL_MODE",
                        "MIN_MATCHING_VOTES",
                        "FORCE_ANY_MODE",
                        "G0_TIMEFRAME",
                        "G1_TIMEFRAME",
                        "G2_TIMEFRAME",
                        "G3_TIMEFRAME",
                    ]:
                        if key in saved_data:
                            base_data[key] = saved_data[key]

                    if "voting_rules" in saved_data:
                        for grp in ["G0", "G1", "G2", "G3"]:
                            if grp in saved_data["voting_rules"]:
                                base_data["voting_rules"][grp] = saved_data[
                                    "voting_rules"
                                ][grp]

                    if "risk_tsl" in saved_data:
                        base_data["risk_tsl"].update(saved_data["risk_tsl"])

                    if "indicators" in saved_data:
                        for k, v in saved_data["indicators"].items():
                            if k not in base_data["indicators"]:
                                base_data["indicators"][k] = {}
                            base_data["indicators"][k].update(v)
                            # Tương thích ngược: Đổi 'group' cũ thành 'groups' mảng
                            if "group" in v and "groups" not in v:
                                base_data["indicators"][k]["groups"] = [v["group"]]

                    if "dca_config" in saved_data:
                        base_data["dca_config"].update(saved_data["dca_config"])
                    if "pca_config" in saved_data:
                        base_data["pca_config"].update(saved_data["pca_config"])
            except Exception as e:
                print(f"[UI Sandbox] Lỗi đọc JSON: {e}")

        return base_data

    def _build_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_inds = self.tabview.add("Chỉ báo (Signals)")
        self.tab_rules = self.tabview.add("Cấu trúc & Luật Vote (4-Tier)")
        self.tab_risk = self.tabview.add("Risk & TSL")
        self.tab_dca_pca = self.tabview.add("Nhồi Lệnh (DCA/PCA)")

        self._build_indicators_tab()
        self._build_voting_tab()
        self._build_risk_tab()
        self._build_dca_pca_tab()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkButton(
            btn_frame,
            text="📂 LOAD TEMPLATE",
            fg_color="#1565C0",
            hover_color="#0D47A1",
            command=self.load_template,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="💾 SAVE AS TEMPLATE",
            fg_color="#455A64",
            hover_color="#37474F",
            command=self.save_as_template,
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            btn_frame,
            text="🚀 LƯU & ÁP DỤNG (HOT-RELOAD)",
            fg_color="#00C853",
            hover_color="#009624",
            font=("Roboto", 13, "bold"),
            height=40,
            command=self.save_strategy,
        ).pack(side="right", padx=5)

    def _build_indicators_tab(self):
        scroll_frame = ctk.CTkScrollableFrame(self.tab_inds)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Cập nhật Header theo Rule V4.2 mới
        headers = [
            "Chỉ báo",
            "ON",
            "Nhóm (Đa chọn)",
            "Tính Trend",
            "Vai trò Macro",
            "Chạy khi (Mode)",
            "Trigger Mode",
            "Thông số",
        ]
        for col, h in enumerate(headers):
            ctk.CTkLabel(scroll_frame, text=h, font=("Roboto", 12, "bold")).grid(
                row=0, column=col, padx=5, pady=5, sticky="w"
            )

        row = 1
        inds_data = self.brain_data.get("indicators", {})

        for ind_name, cfg in inds_data.items():
            # [FIX UX]: Biến Tên chỉ báo thành Nút bấm (Row Toggle)
            btn_name = ctk.CTkButton(
                scroll_frame,
                text=ind_name.upper(),
                font=("Roboto", 12, "bold"),
                text_color="#90CAF9",
                fg_color="transparent",
                hover_color="#333333",
                anchor="w",
                width=80,
            )
            btn_name.grid(row=row, column=0, padx=5, pady=5, sticky="w")

            # Kích hoạt
            active_var = ctk.BooleanVar(value=cfg.get("active", False))
            ctk.CTkCheckBox(scroll_frame, text="", variable=active_var, width=30).grid(
                row=row, column=1, padx=5, pady=5, sticky="w"
            )

            # Multi-Group Checkboxes (G0-G3)
            f_groups = ctk.CTkFrame(scroll_frame, fg_color="transparent")
            f_groups.grid(row=row, column=2, padx=5, pady=5, sticky="w")

            grp_vars = {}
            saved_groups = cfg.get("groups", [cfg.get("group", "G2")])
            for g in ["G0", "G1", "G2", "G3"]:
                g_var = ctk.BooleanVar(value=(g in saved_groups))
                ctk.CTkCheckBox(
                    f_groups, text=g, variable=g_var, width=40, font=("Roboto", 11)
                ).pack(side="left", padx=2)
                grp_vars[g] = g_var

            # Tính Trend (La bàn xu hướng)
            is_trend_var = ctk.BooleanVar(value=cfg.get("is_trend", False))
            ctk.CTkCheckBox(
                scroll_frame,
                text="Trend",
                variable=is_trend_var,
                width=50,
                text_color="#FFD700",
            ).grid(row=row, column=3, padx=5, pady=5, sticky="w")

            # Gắn lệnh Toggle cho Nút Tên Chỉ Báo (Bắt trạng thái để lật công tắc)
            def toggle_row_state(a_var=active_var, g_vars=grp_vars, t_var=is_trend_var):
                target_state = not a_var.get()
                a_var.set(target_state)
                for var in g_vars.values():
                    var.set(target_state)
                t_var.set(target_state)

            btn_name.configure(command=toggle_row_state)

            # Vai trò Macro
            macro_role_var = ctk.StringVar(value=cfg.get("macro_role", "NONE"))
            ctk.CTkComboBox(
                scroll_frame,
                values=["NONE", "BASE", "BREAKOUT", "EXHAUSTION"],
                variable=macro_role_var,
                width=110,
            ).grid(row=row, column=4, padx=5, pady=5, sticky="w")

            # Mode hoạt động
            modes_list = cfg.get("active_modes", ["ANY"])
            mode_var = ctk.StringVar(value=modes_list[0] if modes_list else "ANY")
            ctk.CTkComboBox(
                scroll_frame,
                values=["ANY", "TREND", "RANGE", "BREAKOUT", "EXHAUSTION"],
                variable=mode_var,
                width=100,
            ).grid(row=row, column=5, padx=5, pady=5, sticky="w")

            # Trigger Mode
            trigger_mode_var = ctk.StringVar(
                value=cfg.get("trigger_mode", "STRICT_CLOSE")
            )
            ctk.CTkComboBox(
                scroll_frame,
                values=["STRICT_CLOSE", "REALTIME_TICK"],
                variable=trigger_mode_var,
                width=120,
            ).grid(row=row, column=6, padx=5, pady=5, sticky="w")

            # Nút Cài đặt Thông số
            btn_cfg = ctk.CTkButton(
                scroll_frame,
                text="⚙️ Cài đặt",
                width=70,
                fg_color="#424242",
                hover_color="#616161",
                command=lambda n=ind_name: self.open_ind_setting(n),
            )
            btn_cfg.grid(row=row, column=7, padx=5, pady=5)

            self.ind_widgets[ind_name] = {
                "active_var": active_var,
                "grp_vars": grp_vars,
                "is_trend_var": is_trend_var,
                "macro_role_var": macro_role_var,
                "mode_var": mode_var,
                "trigger_mode_var": trigger_mode_var,
                "params": cfg.get("params", {}),
            }
            row += 1

    def open_ind_setting(self, ind_name):
        current_params = self.ind_widgets[ind_name]["params"]

        def on_save_params(new_params):
            self.ind_widgets[ind_name]["params"] = new_params

        open_indicator_config_popup(self, ind_name, current_params, on_save_params)

    def _build_voting_tab(self):
        top_frame = ctk.CTkFrame(self.tab_rules, fg_color="transparent")
        top_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(
            top_frame, text="Chế độ phân xử (Master Mode):", font=("Roboto", 12, "bold")
        ).grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.master_eval_var = ctk.StringVar(
            value=self.brain_data.get("MASTER_EVAL_MODE", "VETO")
        )
        ctk.CTkComboBox(
            top_frame,
            values=["VETO", "VOTING"],
            variable=self.master_eval_var,
            width=100,
        ).grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(
            top_frame, text="Min Votes (Dùng cho VOTING):", font=("Roboto", 12, "bold")
        ).grid(row=0, column=2, padx=20, pady=5, sticky="w")
        self.min_votes_var = ctk.StringVar(
            value=str(self.brain_data.get("MIN_MATCHING_VOTES", 3))
        )
        ctk.CTkEntry(
            top_frame, textvariable=self.min_votes_var, width=60, justify="center"
        ).grid(row=0, column=3, padx=5, pady=5)

        tf_frame = ctk.CTkFrame(self.tab_rules, fg_color="#1E1E1E", corner_radius=8)
        tf_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            tf_frame,
            text="⏱ CẤU HÌNH KHUNG THỜI GIAN (TIMEFRAMES):",
            font=("Roboto", 13, "bold"),
            text_color="#29B6F6",
        ).grid(row=0, column=0, columnspan=8, pady=5, sticky="w", padx=10)

        tfs_options = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
        for idx, grp in enumerate(["G0", "G1", "G2", "G3"]):
            ctk.CTkLabel(tf_frame, text=f"{grp}:").grid(
                row=1, column=idx * 2, padx=(15, 2), pady=10, sticky="e"
            )
            tf_var = ctk.StringVar(
                value=str(self.brain_data.get(f"{grp}_TIMEFRAME", "15m"))
            )
            ctk.CTkComboBox(
                tf_frame, values=tfs_options, variable=tf_var, width=70
            ).grid(row=1, column=idx * 2 + 1, padx=5, pady=10)
            self.tf_vars[grp] = tf_var

        scroll_rules = ctk.CTkScrollableFrame(self.tab_rules)
        scroll_rules.pack(fill="both", expand=True, padx=10, pady=5)

        rules = self.brain_data.get("voting_rules", {})
        titles = {
            "G0": "G0: LA BÀN VĨ MÔ (MACRO)",
            "G1": "G1: BỘ LỌC XU HƯỚNG",
            "G2": "G2: ĐIỂM NỔ (TRIGGER)",
            "G3": "G3: QUYỀN PHỦ QUYẾT (VETO)",
        }
        colors = {"G0": "#AB47BC", "G1": "#00E676", "G2": "#00B0FF", "G3": "#FF3D00"}

        for grp in ["G0", "G1", "G2", "G3"]:
            grp_data = rules.get(
                grp,
                {
                    "max_opposite": 0,
                    "max_none": 1 if grp != "G0" else 0,
                    "master_rule": "FIX" if grp != "G0" else "PASS",
                },
            )

            frame = ctk.CTkFrame(scroll_rules, fg_color="#2b2b2b", corner_radius=8)
            frame.pack(fill="x", padx=10, pady=5)

            ctk.CTkLabel(
                frame,
                text=titles[grp],
                font=("Roboto", 13, "bold"),
                text_color=colors[grp],
            ).grid(row=0, column=0, columnspan=4, pady=5, sticky="w", padx=10)

            ctk.CTkLabel(frame, text="Max Opposite (Nghịch):").grid(
                row=1, column=0, padx=10, pady=5, sticky="w"
            )
            max_opp_var = ctk.StringVar(value=str(grp_data.get("max_opposite", 0)))
            ctk.CTkEntry(
                frame, textvariable=max_opp_var, width=60, justify="center"
            ).grid(row=1, column=1, padx=10, pady=5)

            ctk.CTkLabel(frame, text="Max None (Trắng):").grid(
                row=1, column=2, padx=10, pady=5, sticky="w"
            )
            max_none_var = ctk.StringVar(value=str(grp_data.get("max_none", 1)))
            ctk.CTkEntry(
                frame, textvariable=max_none_var, width=60, justify="center"
            ).grid(row=1, column=3, padx=10, pady=5)

            ctk.CTkLabel(frame, text="Master Rule:").grid(
                row=2, column=0, padx=10, pady=5, sticky="w"
            )
            master_rule_var = ctk.StringVar(value=grp_data.get("master_rule", "FIX"))
            ctk.CTkComboBox(
                frame,
                values=["FIX", "PASS", "IGNORE"],
                variable=master_rule_var,
                width=100,
            ).grid(row=2, column=1, padx=10, pady=5)

            self.vote_widgets[grp] = {
                "max_opp": max_opp_var,
                "max_none": max_none_var,
                "master_rule": master_rule_var,
            }

    def _build_risk_tab(self):
        risk_data = self.brain_data.get("risk_tsl", {})

        # --- [NEW] CỤM OPTIONS NÂNG CAO (SCALPING & STRICT RISK) ---
        f_adv = ctk.CTkFrame(self.tab_risk, fg_color="#2b2b2b", corner_radius=8)
        f_adv.pack(fill="x", padx=20, pady=(10, 10))

        self.var_force_any = ctk.BooleanVar(
            value=self.brain_data.get("FORCE_ANY_MODE", False)
        )
        ctk.CTkCheckBox(
            f_adv,
            text="Force ANY Mode (Scalping)",
            variable=self.var_force_any,
            font=("Roboto", 13, "bold"),
            text_color="#FF9800",
        ).grid(row=0, column=0, padx=15, pady=10, sticky="w")

        self.var_strict_risk = ctk.BooleanVar(value=risk_data.get("strict_risk", False))
        ctk.CTkCheckBox(
            f_adv,
            text="Strict Risk (Trừ Phí)",
            variable=self.var_strict_risk,
            font=("Roboto", 13, "bold"),
            text_color="#F44336",
        ).grid(row=0, column=1, padx=15, pady=10, sticky="w")

        # [FIX V4.4] TÍCH HỢP TÍNH NĂNG CLOSE ON REVERSE VÀO SANDBOX
        import os, json

        safe_cfg = {}
        try:
            _cfg_path = os.path.join("data", "brain_settings.json")
            if os.path.exists(_cfg_path):
                with open(_cfg_path, "r", encoding="utf-8") as _f:
                    safe_cfg = json.load(_f).get("bot_safeguard", {})
        except:
            pass

        self.var_close_rev = ctk.BooleanVar(
            value=safe_cfg.get("CLOSE_ON_REVERSE", False)
        )
        ctk.CTkCheckBox(
            f_adv,
            text="Close on Reverse (Đảo chiều cắt lệnh)",
            variable=self.var_close_rev,
            font=("Roboto", 13, "bold"),
            text_color="#00E676",
        ).grid(row=1, column=0, padx=15, pady=10, sticky="w")

        f_rev_time = ctk.CTkFrame(f_adv, fg_color="transparent")
        f_rev_time.grid(row=1, column=1, padx=15, pady=10, sticky="w")
        ctk.CTkLabel(f_rev_time, text="Min Hold Time (s):").pack(side="left")
        self.var_rev_time = ctk.StringVar(
            value=str(safe_cfg.get("CLOSE_ON_REVERSE_MIN_TIME", 180))
        )
        ctk.CTkEntry(
            f_rev_time, textvariable=self.var_rev_time, width=60, justify="center"
        ).pack(side="left", padx=5)

        self.var_close_rev_pnl = ctk.BooleanVar(
            value=safe_cfg.get("CLOSE_ON_REVERSE_USE_PNL", True)
        )
        ctk.CTkCheckBox(
            f_rev_time,
            text="Use PnL Check",
            variable=self.var_close_rev_pnl,
            font=("Roboto", 12),
        ).pack(side="left", padx=(15, 5))

        ctk.CTkLabel(f_rev_time, text="Min Profit ($):").pack(side="left")
        self.var_rev_profit = ctk.StringVar(
            value=str(safe_cfg.get("REV_CLOSE_MIN_PROFIT", 0.0))
        )
        ctk.CTkEntry(
            f_rev_time, textvariable=self.var_rev_profit, width=50, justify="center"
        ).pack(side="left", padx=5)

        ctk.CTkLabel(f_rev_time, text="Max Loss ($):").pack(side="left", padx=(10, 0))
        self.var_rev_loss = ctk.StringVar(
            value=str(safe_cfg.get("REV_CLOSE_MAX_LOSS", 0.0))
        )
        ctk.CTkEntry(
            f_rev_time, textvariable=self.var_rev_loss, width=50, justify="center"
        ).pack(side="left", padx=5)
        # -------------------------------------------------------------

        f_base = ctk.CTkFrame(self.tab_risk, fg_color="transparent")
        f_base.pack(fill="x", padx=20, pady=(5, 5))
        ctk.CTkLabel(
            f_base,
            text="BOT BASE RISK (% Cắt lỗ/Lệnh):",
            font=("Roboto", 13, "bold"),
            text_color="#E040FB",
        ).pack(side="left")
        self.var_base_risk = ctk.StringVar(value=str(risk_data.get("base_risk", 0.3)))
        ctk.CTkEntry(
            f_base, textvariable=self.var_base_risk, width=80, justify="center"
        ).pack(side="left", padx=15)

        f_base_sl = ctk.CTkFrame(self.tab_risk, fg_color="transparent")
        f_base_sl.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(
            f_base_sl,
            text="NGUỒN CẮM SL:",
            font=("Roboto", 13, "bold"),
            text_color="#FF3D00",
        ).pack(side="left")

        cur_sl = risk_data.get("base_sl", "G2")
        if cur_sl == "entry":
            cur_sl = "G2"
        self.var_base_sl = ctk.StringVar(value=cur_sl)
        # [NEW] Thêm Option DYNAMIC vào Base SL
        ctk.CTkComboBox(
            f_base_sl,
            values=["G0", "G1", "G2", "G3", "DYNAMIC-G1/G2"],
            variable=self.var_base_sl,
            width=140,
        ).pack(side="left", padx=15)

        # [NEW] ATR Multiplier cho Bot SL
        f_sl_mult = ctk.CTkFrame(self.tab_risk, fg_color="transparent")
        f_sl_mult.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(
            f_sl_mult,
            text="SL ATR MULTIPLIER:",
            font=("Roboto", 13, "bold"),
            text_color="#29B6F6",
        ).pack(side="left")
        self.var_sl_mult = ctk.StringVar(value=str(risk_data.get("sl_atr_multiplier", 0.2)))
        ctk.CTkEntry(
            f_sl_mult, textvariable=self.var_sl_mult, width=80, justify="center"
        ).pack(side="left", padx=15)

        ctk.CTkLabel(
            self.tab_risk,
            text="BOT TSL TACTICS:",
            font=("Roboto", 13, "bold"),
            text_color="#00C853",
        ).pack(anchor="w", padx=20, pady=(10, 0))
        f_tactic_btns = ctk.CTkFrame(self.tab_risk, fg_color="transparent")
        f_tactic_btns.pack(fill="x", padx=20, pady=5)

        self.bot_tactic_vars = {}
        current_tactic_str = risk_data.get("bot_tsl", "BE+STEP_R+SWING")

        # [NEW V4.4] Bổ sung thêm BE_CASH và PSAR_TRAIL vào danh sách chiến thuật Bot
        for t in ["BE", "PNL", "STEP_R", "SWING", "BE_CASH", "PSAR_TRAIL", "ANTI_CASH"]:
            is_active = t in current_tactic_str
            var = ctk.BooleanVar(value=is_active)
            ctk.CTkCheckBox(
                f_tactic_btns,
                text=t,
                variable=var,
                font=("Roboto", 12, "bold"),
                width=80,
            ).pack(side="left", padx=10)
            self.bot_tactic_vars[t] = var

        f_tsl = ctk.CTkFrame(self.tab_risk, fg_color="transparent")
        f_tsl.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(
            f_tsl,
            text="TSL LOGIC MODE (Bám đuôi):",
            font=("Roboto", 13, "bold"),
            text_color="#29B6F6",
        ).pack(side="left")
        self.var_tsl_mode = ctk.StringVar(value=risk_data.get("tsl_mode", "STATIC"))
        ctk.CTkComboBox(
            f_tsl,
            values=["STATIC", "DYNAMIC", "AGGRESSIVE"],
            variable=self.var_tsl_mode,
            width=130,
        ).pack(side="left", padx=20)

        ctk.CTkFrame(self.tab_risk, height=2, fg_color="#333").pack(
            fill="x", padx=20, pady=15
        )
        ctk.CTkLabel(
            self.tab_risk,
            text="DYNAMIC RISK MULTIPLIERS (Hệ số rủi ro theo Market Mode)",
            font=("Roboto", 13, "bold"),
            text_color="#FFB300",
        ).pack(anchor="w", padx=20, pady=5)

        f_mult = ctk.CTkFrame(self.tab_risk, fg_color="#2b2b2b", corner_radius=8)
        f_mult.pack(fill="x", padx=20)

        mults = risk_data.get("mode_multipliers", {})
        modes = ["ANY", "TREND", "RANGE", "BREAKOUT", "EXHAUSTION"]
        self.mult_vars = {}

        for i, mode in enumerate(modes):
            ctk.CTkLabel(f_mult, text=f"{mode}:").grid(
                row=i // 3, column=(i % 3) * 2, padx=15, pady=10, sticky="e"
            )
            var = ctk.StringVar(value=str(mults.get(mode, 1.0)))
            ctk.CTkEntry(f_mult, textvariable=var, width=60, justify="center").grid(
                row=i // 3, column=(i % 3) * 2 + 1, padx=5, pady=10, sticky="w"
            )
            self.mult_vars[mode] = var

    def _build_dca_pca_tab(self):
        dca_cfg = self.brain_data.get("dca_config", {})
        pca_cfg = self.brain_data.get("pca_config", {})

        # --- DCA FRAME ---
        dca_frame = ctk.CTkFrame(self.tab_dca_pca, fg_color="#2b2b2b", corner_radius=8)
        dca_frame.pack(fill="x", padx=10, pady=10)

        self.dca_active = ctk.BooleanVar(value=dca_cfg.get("ENABLED", False))
        ctk.CTkCheckBox(
            dca_frame,
            text="Kích hoạt AUTO DCA (Gồng lỗ/Bắt đáy thuận nến)",
            variable=self.dca_active,
            font=("Roboto", 13, "bold"),
            text_color="#FFAB00",
        ).grid(row=0, column=0, columnspan=6, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(dca_frame, text="Max Steps:").grid(
            row=1, column=0, padx=10, pady=5, sticky="w"
        )
        self.dca_steps = ctk.StringVar(value=str(dca_cfg.get("MAX_STEPS", 3)))
        ctk.CTkEntry(dca_frame, textvariable=self.dca_steps, width=70).grid(
            row=1, column=1, padx=10, pady=5
        )

        ctk.CTkLabel(dca_frame, text="Vol Multiplier (x):").grid(
            row=1, column=2, padx=10, pady=5, sticky="w"
        )
        self.dca_mult = ctk.StringVar(value=str(dca_cfg.get("STEP_MULTIPLIER", 1.5)))
        ctk.CTkEntry(dca_frame, textvariable=self.dca_mult, width=70).grid(
            row=1, column=3, padx=10, pady=5
        )

        # [NEW] ATR Distance cho DCA
        ctk.CTkLabel(dca_frame, text="ATR Distance:").grid(
            row=1, column=4, padx=10, pady=5, sticky="w"
        )
        self.dca_atr = ctk.StringVar(value=str(dca_cfg.get("DISTANCE_ATR_R", 1.0)))
        ctk.CTkEntry(dca_frame, textvariable=self.dca_atr, width=70).grid(
            row=1, column=5, padx=10, pady=5
        )

        # --- PCA FRAME ---
        pca_frame = ctk.CTkFrame(self.tab_dca_pca, fg_color="#2b2b2b", corner_radius=8)
        pca_frame.pack(fill="x", padx=10, pady=10)

        self.pca_active = ctk.BooleanVar(value=pca_cfg.get("ENABLED", False))
        ctk.CTkCheckBox(
            pca_frame,
            text="Kích hoạt AUTO PCA (Nhồi thuận Trend mạnh)",
            variable=self.pca_active,
            font=("Roboto", 13, "bold"),
            text_color="#00C853",
        ).grid(row=0, column=0, columnspan=6, padx=10, pady=10, sticky="w")

        ctk.CTkLabel(pca_frame, text="Max Steps:").grid(
            row=1, column=0, padx=10, pady=5, sticky="w"
        )
        self.pca_steps = ctk.StringVar(value=str(pca_cfg.get("MAX_STEPS", 2)))
        ctk.CTkEntry(pca_frame, textvariable=self.pca_steps, width=70).grid(
            row=1, column=1, padx=10, pady=5
        )

        ctk.CTkLabel(pca_frame, text="Vol Multiplier (x):").grid(
            row=1, column=2, padx=10, pady=5, sticky="w"
        )
        self.pca_mult = ctk.StringVar(value=str(pca_cfg.get("STEP_MULTIPLIER", 0.5)))
        ctk.CTkEntry(pca_frame, textvariable=self.pca_mult, width=70).grid(
            row=1, column=3, padx=10, pady=5
        )

        # [NEW] ATR Distance cho PCA
        ctk.CTkLabel(pca_frame, text="ATR Distance:").grid(
            row=1, column=4, padx=10, pady=5, sticky="w"
        )
        self.pca_atr = ctk.StringVar(value=str(pca_cfg.get("DISTANCE_ATR_R", 1.5)))
        ctk.CTkEntry(pca_frame, textvariable=self.pca_atr, width=70).grid(
            row=1, column=5, padx=10, pady=5
        )

        # --- COOLDOWN FRAME ---
        cd_frame = ctk.CTkFrame(self.tab_dca_pca, fg_color="#2b2b2b", corner_radius=8)
        cd_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            cd_frame,
            text="DCA/PCA Cooldown (giây):",
            font=("Roboto", 12, "bold"),
            text_color="#29B6F6",
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.dca_pca_cooldown = ctk.StringVar(value=str(dca_cfg.get("COOLDOWN", 60)))
        ctk.CTkEntry(cd_frame, textvariable=self.dca_pca_cooldown, width=70).grid(
            row=0, column=1, padx=10, pady=10
        )

    def _pack_data(self):
        new_inds = {}
        for ind_name, widgets in self.ind_widgets.items():
            mode_val = widgets["mode_var"].get()
            # Trích xuất mảng các Group được chọn
            selected_groups = [g for g, var in widgets["grp_vars"].items() if var.get()]

            new_inds[ind_name] = {
                "active": widgets["active_var"].get(),
                "groups": selected_groups,
                "is_trend": widgets["is_trend_var"].get(),
                "macro_role": widgets["macro_role_var"].get(),
                "active_modes": [mode_val] if mode_val != "ANY" else ["ANY"],
                "trigger_mode": widgets["trigger_mode_var"].get(),
                "params": widgets["params"],
            }

        new_voting = {}
        for grp in ["G0", "G1", "G2", "G3"]:
            new_voting[grp] = {
                "max_opposite": int(self.vote_widgets[grp]["max_opp"].get() or 0),
                "max_none": int(self.vote_widgets[grp]["max_none"].get() or 1),
                "master_rule": self.vote_widgets[grp]["master_rule"].get(),
            }

        selected_tactics = [k for k, v in self.bot_tactic_vars.items() if v.get()]
        bot_tsl_str = "+".join(selected_tactics) if selected_tactics else "OFF"

        new_risk_tsl = {
            "base_risk": float(self.var_base_risk.get() or 0.3),
            "base_sl": self.var_base_sl.get(),
            "sl_atr_multiplier": float(self.var_sl_mult.get() or 0.2), # [NEW]
            "tsl_mode": self.var_tsl_mode.get(),
            "bot_tsl": bot_tsl_str,
            "mode_multipliers": {
                mode: float(var.get() or 1.0) for mode, var in self.mult_vars.items()
            },
            "strict_risk": self.var_strict_risk.get(),  # [NEW]
        }

        # [FIX V4.4] Trích xuất config Close on Reverse
        self.temp_close_rev = self.var_close_rev.get()
        self.temp_rev_time = float(self.var_rev_time.get() or 180)

        # [NEW] Thêm Distance ATR R
        new_dca = {
            "ENABLED": self.dca_active.get(),
            "MAX_STEPS": int(self.dca_steps.get() or 3),
            "STEP_MULTIPLIER": float(self.dca_mult.get() or 1.5),
            "DISTANCE_ATR_R": float(self.dca_atr.get() or 1.0),
            "COOLDOWN": int(self.dca_pca_cooldown.get() or 60),
        }
        new_pca = {
            "ENABLED": self.pca_active.get(),
            "MAX_STEPS": int(self.pca_steps.get() or 2),
            "STEP_MULTIPLIER": float(self.pca_mult.get() or 0.5),
            "DISTANCE_ATR_R": float(self.pca_atr.get() or 1.5),
            "CONFIRM_ADX": getattr(config, "PCA_CONFIG", {}).get("CONFIRM_ADX", 23),
        }

        return {
            "MASTER_EVAL_MODE": self.master_eval_var.get(),
            "MIN_MATCHING_VOTES": int(self.min_votes_var.get() or 3),
            "FORCE_ANY_MODE": self.var_force_any.get(),  # [NEW]
            "G0_TIMEFRAME": self.tf_vars["G0"].get(),
            "G1_TIMEFRAME": self.tf_vars["G1"].get(),
            "G2_TIMEFRAME": self.tf_vars["G2"].get(),
            "G3_TIMEFRAME": self.tf_vars["G3"].get(),
            "voting_rules": new_voting,
            "risk_tsl": new_risk_tsl,
            "indicators": new_inds,
            "dca_config": new_dca,
            "pca_config": new_pca,
        }

    def save_strategy(self):
        try:
            output_data = self._pack_data()
            os.makedirs(os.path.dirname(BRAIN_SETTINGS_PATH), exist_ok=True)

            # [FIX] Keep existing non-strategy keys like bot_safeguard, BOT_ACTIVE_SYMBOLS, symbol_configs
            existing_data = {}
            if os.path.exists(BRAIN_SETTINGS_PATH):
                try:
                    with open(BRAIN_SETTINGS_PATH, "r", encoding="utf-8") as f:
                        existing_data = json.load(f)
                except Exception:
                    pass

            # [FIX]: Cập nhật gia tăng thay vì ghi đè thô bạo
            existing_data.update(output_data)

            # [FIX V4.4] Cập nhật Close on Reverse vào bot_safeguard khi Sandbox bấm lưu
            if "bot_safeguard" not in existing_data:
                existing_data["bot_safeguard"] = {}
            existing_data["bot_safeguard"]["CLOSE_ON_REVERSE"] = self.temp_close_rev
            existing_data["bot_safeguard"]["CLOSE_ON_REVERSE_MIN_TIME"] = (
                self.temp_rev_time
            )
            existing_data["bot_safeguard"]["CLOSE_ON_REVERSE_USE_PNL"] = self.var_close_rev_pnl.get()
            existing_data["bot_safeguard"]["REV_CLOSE_MIN_PROFIT"] = float(self.var_rev_profit.get() or 0.0)
            existing_data["bot_safeguard"]["REV_CLOSE_MAX_LOSS"] = float(self.var_rev_loss.get() or 0.0)

            with open(BRAIN_SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=4)

            # [HOT-FIX]: Đồng bộ ngay vào config Runtime của UI Main
            if hasattr(self.master, "reload_config_from_json"):
                self.master.reload_config_from_json()
            else:
                # Fallback nếu gọi từ nơi khác
                config.MASTER_EVAL_MODE = output_data["MASTER_EVAL_MODE"]
                config.MIN_MATCHING_VOTES = output_data["MIN_MATCHING_VOTES"]
                config.BOT_RISK_PERCENT = output_data["risk_tsl"]["base_risk"]
                config.TSL_LOGIC_MODE = output_data["risk_tsl"]["tsl_mode"]
                config.FORCE_ANY_MODE = output_data["FORCE_ANY_MODE"]
                config.STRICT_RISK_CALC = output_data["risk_tsl"]["strict_risk"]
                config.DCA_CONFIG = output_data["dca_config"]
                config.PCA_CONFIG = output_data["pca_config"]

            # Tự động đóng cửa sổ mượt mà
            self.destroy()
        except Exception as e:
            messagebox.showerror("Lỗi hệ thống", f"Lỗi ghi file cấu hình:\n{e}")

    def load_template(self):
        file_path = filedialog.askopenfilename(
            initialdir=TEMPLATE_DIR,
            title="Chọn Template",
            filetypes=[("JSON files", "*.json")],
        )
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.brain_data = json.load(f)

                # [FIX]: Reset tracking dictionaries trước khi build lại UI
                self.ind_widgets = {}
                self.vote_widgets = {}
                self.risk_widgets = {}
                self.tf_vars = {}

                for widget in self.winfo_children():
                    widget.destroy()
                self._build_ui()
                messagebox.showinfo(
                    "Thành công",
                    "Đã nạp Template thành công. Hãy bấm LƯU & ÁP DỤNG để kích hoạt!",
                )
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể đọc Template:\n{e}")

    def save_as_template(self):
        try:
            output_data = self._pack_data()
            file_path = filedialog.asksaveasfilename(
                initialdir=TEMPLATE_DIR,
                title="Lưu Template",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json")],
            )
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, indent=4)
                messagebox.showinfo("Thành công", f"Đã lưu Template tại:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi lưu Template:\n{e}")
