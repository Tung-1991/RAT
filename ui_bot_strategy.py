# -*- coding: utf-8 -*-
# FILE: ui_bot_strategy.py
# V3.0: UNIFIED BOT STRATEGY UI - 2-TIER VOTING & TEMPLATES (KAISER EDITION)

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
        self.title("🧠 V3.0 Bot Strategy Sandbox (Brain Settings)")
        self.geometry("1000x750")
        self.attributes("-topmost", True)
        #self.transient(master)
        self.focus_force()

        os.makedirs(TEMPLATE_DIR, exist_ok=True)
        
        self.brain_data = self._load_brain_data()
        self.ind_widgets = {}
        self.vote_widgets = {}
        self.risk_widgets = {}

        self._build_ui()

    def _load_brain_data(self):
        """Khởi tạo cấu trúc 2-Tier Voting và Dynamic Risk mới nhất"""
        base_data = {
            "voting_rules": {
                "G1": {"max_opposite": 0, "max_none": 0, "master_rule": "FIX"},
                "G2": {"max_opposite": 0, "max_none": 1, "master_rule": "FIX"},
                "G3": {"max_opposite": 0, "max_none": 1, "master_rule": "IGNORE"}
            },
            "risk_tsl": {
                "base_risk": getattr(config, "BOT_RISK_PERCENT", 0.3),
                "tsl_mode": getattr(config, "TSL_LOGIC_MODE", "STATIC"),
                "mode_multipliers": {"TREND": 1.0, "RANGE": 0.5, "BREAKOUT": 1.5, "EXHAUSTION": 1.0, "ANY": 1.0}
            },
            "indicators": getattr(config, "SANDBOX_CONFIG", {}).get("indicators", {}),
            "dca_config": getattr(config, "DCA_CONFIG", {}),
            "pca_config": getattr(config, "PCA_CONFIG", {})
        }

        if os.path.exists(BRAIN_SETTINGS_PATH):
            try:
                with open(BRAIN_SETTINGS_PATH, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)
                    
                    # Merge thông minh để không ghi đè mất cấu trúc mới
                    if "voting_rules" in saved_data:
                        if "G1" in saved_data["voting_rules"]:
                            base_data["voting_rules"] = saved_data["voting_rules"]
                    
                    if "risk_tsl" in saved_data:
                        base_data["risk_tsl"].update(saved_data["risk_tsl"])
                        
                    if "indicators" in saved_data:
                        for k, v in saved_data["indicators"].items():
                            if k in base_data["indicators"]:
                                base_data["indicators"][k].update(v)
                                
                    if "dca_config" in saved_data: base_data["dca_config"].update(saved_data["dca_config"])
                    if "pca_config" in saved_data: base_data["pca_config"].update(saved_data["pca_config"])
            except Exception as e:
                print(f"[UI Sandbox] Lỗi đọc JSON: {e}. Dùng default config.")

        return base_data

    def _build_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=5)

        self.tab_inds = self.tabview.add("Chỉ báo (Signals)")
        self.tab_rules = self.tabview.add("Luật Vote (2-Tier)")
        self.tab_risk = self.tabview.add("Risk & TSL")
        self.tab_dca_pca = self.tabview.add("Nhồi Lệnh (DCA/PCA)")

        self._build_indicators_tab()
        self._build_voting_tab()
        self._build_risk_tab()
        self._build_dca_pca_tab()

        # Bottom Action Bar
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(btn_frame, text="📂 LOAD TEMPLATE", fg_color="#1565C0", hover_color="#0D47A1", command=self.load_template).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="💾 SAVE AS TEMPLATE", fg_color="#424242", hover_color="#616161", command=self.save_as_template).pack(side="left", padx=5)
        
        ctk.CTkButton(btn_frame, text="🚀 LƯU & ÁP DỤNG (HOT-RELOAD)", fg_color="#00C853", hover_color="#009624", font=("Roboto", 13, "bold"), height=40, command=self.save_strategy).pack(side="right", padx=5)

    def _build_indicators_tab(self):
        scroll_frame = ctk.CTkScrollableFrame(self.tab_inds)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        headers = ["Chỉ báo", "Kích hoạt", "Nhóm (Group)", "Chế độ (Mode)", "Thông số"]
        for col, h in enumerate(headers):
            ctk.CTkLabel(scroll_frame, text=h, font=("Roboto", 13, "bold")).grid(row=0, column=col, padx=15, pady=5, sticky="w")

        row = 1
        inds_data = self.brain_data.get("indicators", {})
        
        for ind_name, cfg in inds_data.items():
            ctk.CTkLabel(scroll_frame, text=ind_name.upper(), font=("Roboto", 12, "bold"), text_color="#90CAF9").grid(row=row, column=0, padx=15, pady=5, sticky="w")
            
            active_var = ctk.BooleanVar(value=cfg.get("active", False))
            ctk.CTkCheckBox(scroll_frame, text="ON", variable=active_var, width=50).grid(row=row, column=1, padx=15, pady=5, sticky="w")
            
            group_var = ctk.StringVar(value=cfg.get("group", "G2"))
            ctk.CTkComboBox(scroll_frame, values=["G1", "G2", "G3"], variable=group_var, width=70).grid(row=row, column=2, padx=15, pady=5, sticky="w")
            
            modes_list = cfg.get("active_modes", ["ANY"])
            mode_var = ctk.StringVar(value=modes_list[0] if modes_list else "ANY")
            ctk.CTkComboBox(scroll_frame, values=["ANY", "TREND", "RANGE", "BREAKOUT", "EXHAUSTION"], variable=mode_var, width=120).grid(row=row, column=3, padx=15, pady=5, sticky="w")

            # Nút Mở Config Động
            btn_cfg = ctk.CTkButton(scroll_frame, text="⚙️ Cài đặt", width=80, fg_color="#424242", hover_color="#616161",
                                    command=lambda n=ind_name: self.open_ind_setting(n))
            btn_cfg.grid(row=row, column=4, padx=15, pady=5)

            self.ind_widgets[ind_name] = {
                "active_var": active_var,
                "group_var": group_var,
                "mode_var": mode_var,
                "params": cfg.get("params", {}) 
            }
            row += 1

    def open_ind_setting(self, ind_name):
        current_params = self.ind_widgets[ind_name]["params"]
        
        def on_save_params(new_params):
            self.ind_widgets[ind_name]["params"] = new_params
            
        open_indicator_config_popup(self, ind_name, current_params, on_save_params)

    def _build_voting_tab(self):
        rules = self.brain_data.get("voting_rules", {})
        
        for idx, grp in enumerate(["G1", "G2", "G3"]):
            grp_data = rules.get(grp, {"max_opposite": 0, "max_none": 1, "master_rule": "FIX"})
            
            frame = ctk.CTkFrame(self.tab_rules, fg_color="#2b2b2b", corner_radius=8)
            frame.pack(fill="x", padx=20, pady=10)
            
            lbl_title = "G1: BỘ LỌC XU HƯỚNG" if grp == "G1" else ("G2: ĐIỂM NỔ (TRIGGER)" if grp == "G2" else "G3: QUYỀN PHỦ QUYẾT (VETO)")
            ctk.CTkLabel(frame, text=lbl_title, font=("Roboto", 13, "bold"), text_color="#00E676" if grp!="G3" else "#FF3D00").grid(row=0, column=0, columnspan=4, pady=10, sticky="w", padx=10)

            ctk.CTkLabel(frame, text="Max Opposite (Phiếu nghịch):").grid(row=1, column=0, padx=10, pady=10, sticky="w")
            max_opp_var = ctk.StringVar(value=str(grp_data.get("max_opposite", 0)))
            ctk.CTkEntry(frame, textvariable=max_opp_var, width=60, justify="center").grid(row=1, column=1, padx=10, pady=10)

            ctk.CTkLabel(frame, text="Max None (Phiếu trắng):").grid(row=1, column=2, padx=10, pady=10, sticky="w")
            max_none_var = ctk.StringVar(value=str(grp_data.get("max_none", 1)))
            ctk.CTkEntry(frame, textvariable=max_none_var, width=60, justify="center").grid(row=1, column=3, padx=10, pady=10)

            ctk.CTkLabel(frame, text="Master Rule (Quyền sinh sát):").grid(row=2, column=0, padx=10, pady=10, sticky="w")
            master_rule_var = ctk.StringVar(value=grp_data.get("master_rule", "FIX"))
            ctk.CTkComboBox(frame, values=["FIX", "PASS", "IGNORE"], variable=master_rule_var, width=100).grid(row=2, column=1, padx=10, pady=10)
            
            ctk.CTkLabel(frame, text="(FIX: Ép đồng thuận | PASS: Bỏ qua None | IGNORE: Vô hiệu Group)", font=("Roboto", 11, "italic"), text_color="gray").grid(row=2, column=2, columnspan=2, sticky="w")

            self.vote_widgets[grp] = {
                "max_opp": max_opp_var,
                "max_none": max_none_var,
                "master_rule": master_rule_var
            }

    def _build_risk_tab(self):
        risk_data = self.brain_data.get("risk_tsl", {})
        
        # 1. Base Risk
        f_base = ctk.CTkFrame(self.tab_risk, fg_color="transparent")
        f_base.pack(fill="x", padx=20, pady=(15, 5))
        ctk.CTkLabel(f_base, text="BOT BASE RISK (% Cắt lỗ/Lệnh):", font=("Roboto", 13, "bold"), text_color="#E040FB").pack(side="left")
        self.var_base_risk = ctk.StringVar(value=str(risk_data.get("base_risk", 0.3)))
        ctk.CTkEntry(f_base, textvariable=self.var_base_risk, width=80, justify="center").pack(side="left", padx=15)

        # 2. TSL Mode
        f_tsl = ctk.CTkFrame(self.tab_risk, fg_color="transparent")
        f_tsl.pack(fill="x", padx=20, pady=5)
        ctk.CTkLabel(f_tsl, text="TSL LOGIC MODE (Bám đuôi):", font=("Roboto", 13, "bold"), text_color="#29B6F6").pack(side="left")
        self.var_tsl_mode = ctk.StringVar(value=risk_data.get("tsl_mode", "STATIC"))
        ctk.CTkComboBox(f_tsl, values=["STATIC", "DYNAMIC", "AGGRESSIVE"], variable=self.var_tsl_mode, width=130).pack(side="left", padx=20)

        # 3. Dynamic Risk Multipliers
        ctk.CTkFrame(self.tab_risk, height=2, fg_color="#333").pack(fill="x", padx=20, pady=15)
        ctk.CTkLabel(self.tab_risk, text="DYNAMIC RISK MULTIPLIERS (Hệ số rủi ro theo Market Mode)", font=("Roboto", 13, "bold"), text_color="#FFB300").pack(anchor="w", padx=20, pady=5)
        ctk.CTkLabel(self.tab_risk, text="(Vol thực tế = Base Risk * Hệ số tương ứng. Ví dụ: Đánh mạnh khi Breakout, đánh nhẹ khi Range)", font=("Roboto", 11, "italic"), text_color="gray").pack(anchor="w", padx=20, pady=(0,10))

        f_mult = ctk.CTkFrame(self.tab_risk, fg_color="#2b2b2b", corner_radius=8)
        f_mult.pack(fill="x", padx=20)
        
        mults = risk_data.get("mode_multipliers", {})
        modes = ["ANY", "TREND", "RANGE", "BREAKOUT", "EXHAUSTION"]
        self.mult_vars = {}
        
        for i, mode in enumerate(modes):
            ctk.CTkLabel(f_mult, text=f"{mode}:").grid(row=i//3, column=(i%3)*2, padx=15, pady=10, sticky="e")
            var = ctk.StringVar(value=str(mults.get(mode, 1.0)))
            ctk.CTkEntry(f_mult, textvariable=var, width=60, justify="center").grid(row=i//3, column=(i%3)*2+1, padx=5, pady=10, sticky="w")
            self.mult_vars[mode] = var

    def _build_dca_pca_tab(self):
        dca_cfg = self.brain_data.get("dca_config", {})
        pca_cfg = self.brain_data.get("pca_config", {})

        # --- DCA ---
        dca_frame = ctk.CTkFrame(self.tab_dca_pca, fg_color="#2b2b2b", corner_radius=8)
        dca_frame.pack(fill="x", padx=10, pady=10)
        
        self.dca_active = ctk.BooleanVar(value=dca_cfg.get("ENABLED", False))
        ctk.CTkCheckBox(dca_frame, text="Kích hoạt AUTO DCA (Gồng lỗ/Bắt đáy thuận nến)", variable=self.dca_active, font=("Roboto", 13, "bold"), text_color="#FFAB00").grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(dca_frame, text="Max Steps (Lệnh):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.dca_steps = ctk.StringVar(value=str(dca_cfg.get("MAX_STEPS", 3)))
        ctk.CTkEntry(dca_frame, textvariable=self.dca_steps, width=70).grid(row=1, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(dca_frame, text="Vol Multiplier (x):").grid(row=1, column=2, padx=10, pady=5, sticky="w")
        self.dca_mult = ctk.StringVar(value=str(dca_cfg.get("STEP_MULTIPLIER", 1.5)))
        ctk.CTkEntry(dca_frame, textvariable=self.dca_mult, width=70).grid(row=1, column=3, padx=10, pady=5)

        # --- PCA ---
        pca_frame = ctk.CTkFrame(self.tab_dca_pca, fg_color="#2b2b2b", corner_radius=8)
        pca_frame.pack(fill="x", padx=10, pady=10)

        self.pca_active = ctk.BooleanVar(value=pca_cfg.get("ENABLED", False))
        ctk.CTkCheckBox(pca_frame, text="Kích hoạt AUTO PCA (Nhồi thuận Trend mạnh)", variable=self.pca_active, font=("Roboto", 13, "bold"), text_color="#00C853").grid(row=0, column=0, columnspan=4, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(pca_frame, text="Max Steps (Lệnh):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.pca_steps = ctk.StringVar(value=str(pca_cfg.get("MAX_STEPS", 2)))
        ctk.CTkEntry(pca_frame, textvariable=self.pca_steps, width=70).grid(row=1, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(pca_frame, text="Vol Multiplier (x):").grid(row=1, column=2, padx=10, pady=5, sticky="w")
        self.pca_mult = ctk.StringVar(value=str(pca_cfg.get("STEP_MULTIPLIER", 0.5)))
        ctk.CTkEntry(pca_frame, textvariable=self.pca_mult, width=70).grid(row=1, column=3, padx=10, pady=5)

    def _pack_data(self):
        """Gom toàn bộ dữ liệu từ UI thành Dictionary chuẩn"""
        new_inds = {}
        for ind_name, widgets in self.ind_widgets.items():
            mode_val = widgets["mode_var"].get()
            new_inds[ind_name] = {
                "active": widgets["active_var"].get(),
                "group": widgets["group_var"].get(),
                "active_modes": [mode_val] if mode_val != "ANY" else ["ANY"], 
                "params": widgets["params"]
            }

        new_voting = {}
        for grp in ["G1", "G2", "G3"]:
            new_voting[grp] = {
                "max_opposite": int(self.vote_widgets[grp]["max_opp"].get() or 0),
                "max_none": int(self.vote_widgets[grp]["max_none"].get() or 1),
                "master_rule": self.vote_widgets[grp]["master_rule"].get()
            }
            
        new_risk_tsl = {
            "base_risk": float(self.var_base_risk.get() or 0.3),
            "tsl_mode": self.var_tsl_mode.get(),
            "mode_multipliers": {mode: float(var.get() or 1.0) for mode, var in self.mult_vars.items()}
        }

        new_dca = {
            "ENABLED": self.dca_active.get(),
            "MAX_STEPS": int(self.dca_steps.get() or 3),
            "STEP_MULTIPLIER": float(self.dca_mult.get() or 1.5),
            "DISTANCE_ATR_R": getattr(config, "DCA_CONFIG", {}).get("DISTANCE_ATR_R", 1.0)
        }
        
        new_pca = {
            "ENABLED": self.pca_active.get(),
            "MAX_STEPS": int(self.pca_steps.get() or 2),
            "STEP_MULTIPLIER": float(self.pca_mult.get() or 0.5),
            "CONFIRM_ADX": getattr(config, "PCA_CONFIG", {}).get("CONFIRM_ADX", 23)
        }

        return {
            "voting_rules": new_voting,
            "risk_tsl": new_risk_tsl,
            "indicators": new_inds,
            "dca_config": new_dca,
            "pca_config": new_pca,
            "trend_timeframe": getattr(config, "trend_timeframe", "1h"),
            "entry_timeframe": getattr(config, "entry_timeframe", "15m"),
            "NUM_H1_BARS": getattr(config, "NUM_H1_BARS", 70),
            "NUM_M15_BARS": getattr(config, "NUM_M15_BARS", 70)
        }

    def save_strategy(self):
        try:
            output_data = self._pack_data()
            os.makedirs(os.path.dirname(BRAIN_SETTINGS_PATH), exist_ok=True)
            with open(BRAIN_SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=4)

            # Cập nhật ngược lại config.py RAM cho UI xài tạm trước khi reload
            config.BOT_RISK_PERCENT = output_data["risk_tsl"]["base_risk"]
            config.TSL_LOGIC_MODE = output_data["risk_tsl"]["tsl_mode"]

            messagebox.showinfo("Thành công", f"Đã lưu Brain Settings.\nBot Daemon sẽ tự động Hot-Reload!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu cấu hình:\n{e}")

    def load_template(self):
        file_path = filedialog.askopenfilename(initialdir=TEMPLATE_DIR, title="Chọn Template", filetypes=[("JSON files", "*.json")])
        if file_path:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.brain_data = json.load(f)
                
                # Re-render UI
                for widget in self.winfo_children():
                    widget.destroy()
                self._build_ui()
                messagebox.showinfo("Thành công", "Đã nạp Template thành công. Hãy bấm LƯU & ÁP DỤNG để kích hoạt!")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể đọc Template:\n{e}")

    def save_as_template(self):
        try:
            output_data = self._pack_data()
            file_path = filedialog.asksaveasfilename(initialdir=TEMPLATE_DIR, title="Lưu Template", defaultextension=".json", filetypes=[("JSON files", "*.json")])
            if file_path:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, indent=4)
                messagebox.showinfo("Thành công", f"Đã lưu Template tại:\n{file_path}")
        except Exception as e:
            messagebox.showerror("Lỗi", f"Lỗi lưu Template:\n{e}")