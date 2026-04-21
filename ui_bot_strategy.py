# -*- coding: utf-8 -*-
# FILE: ui_bot_strategy.py
# V3.0: UNIFIED BOT STRATEGY UI - SINGLE SOURCE OF TRUTH (KAISER EDITION)

import customtkinter as ctk
import json
import os
import config
from tkinter import messagebox

BRAIN_SETTINGS_PATH = "data/brain_settings.json"

class BotStrategyUI(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("🧠 V3.0 Bot Strategy Sandbox (Brain Settings)")
        self.geometry("900x700")
        self.attributes("-topmost", True)
        self.focus_force()

        # Dữ liệu Gốc
        self.brain_data = self._load_brain_data()
        self.ind_widgets = {}

        self._build_ui()

    def _load_brain_data(self):
        """Ưu tiên đọc từ file JSON, nếu lỗi/thiếu thì lấy từ config.py"""
        base_data = {
            "voting_rules": getattr(config, "SANDBOX_CONFIG", {}).get("voting_rules", {}),
            "indicators": getattr(config, "SANDBOX_CONFIG", {}).get("indicators", {}),
            "dca_config": getattr(config, "DCA_CONFIG", {}),
            "pca_config": getattr(config, "PCA_CONFIG", {})
        }

        if os.path.exists(BRAIN_SETTINGS_PATH):
            try:
                with open(BRAIN_SETTINGS_PATH, "r", encoding="utf-8") as f:
                    saved_data = json.load(f)
                    # Merge data để tránh thiếu key do update config mới
                    for k in base_data.keys():
                        if k in saved_data:
                            base_data[k].update(saved_data[k])
            except Exception as e:
                print(f"[UI Sandbox] Lỗi đọc JSON: {e}. Dùng default config.")

        return base_data

    def _build_ui(self):
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_inds = self.tabview.add("Chỉ báo (Signals)")
        self.tab_rules = self.tabview.add("Luật Vote (Voting Rules)")
        self.tab_dca_pca = self.tabview.add("Nhồi Lệnh (DCA/PCA)")

        self._build_indicators_tab()
        self._build_voting_tab()
        self._build_dca_pca_tab()

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        save_btn = ctk.CTkButton(btn_frame, text="💾 LƯU CẤU HÌNH BRAIN", fg_color="#28a745", hover_color="#218838", command=self.save_strategy)
        save_btn.pack(side="right", padx=5)

    def _build_indicators_tab(self):
        scroll_frame = ctk.CTkScrollableFrame(self.tab_inds)
        scroll_frame.pack(fill="both", expand=True, padx=5, pady=5)

        headers = ["Chỉ báo", "Kích hoạt", "Nhóm (Group)", "Chế độ (Mode)"]
        for col, h in enumerate(headers):
            lbl = ctk.CTkLabel(scroll_frame, text=h, font=("Arial", 12, "bold"))
            lbl.grid(row=0, column=col, padx=15, pady=5, sticky="w")

        row = 1
        inds_data = self.brain_data.get("indicators", {})
        
        for ind_name, cfg in inds_data.items():
            # Tên
            ctk.CTkLabel(scroll_frame, text=ind_name.upper()).grid(row=row, column=0, padx=15, pady=5, sticky="w")
            
            # Active (Checkbox)
            active_var = ctk.BooleanVar(value=cfg.get("active", False))
            cb = ctk.CTkCheckBox(scroll_frame, text="ON", variable=active_var, width=50)
            cb.grid(row=row, column=1, padx=15, pady=5, sticky="w")
            
            # Group (Dropdown)
            group_var = ctk.StringVar(value=cfg.get("group", "G2"))
            grp_cb = ctk.CTkComboBox(scroll_frame, values=["G1", "G2", "G3"], variable=group_var, width=80)
            grp_cb.grid(row=row, column=2, padx=15, pady=5, sticky="w")
            
            # Active Modes (Lấy phần tử đầu tiên làm đại diện trên UI cho đơn giản)
            modes_list = cfg.get("active_modes", ["ANY"])
            mode_var = ctk.StringVar(value=modes_list[0] if modes_list else "ANY")
            mode_cb = ctk.CTkComboBox(scroll_frame, values=["ANY", "TREND", "RANGE", "BREAKOUT", "EXHAUSTION"], variable=mode_var, width=120)
            mode_cb.grid(row=row, column=3, padx=15, pady=5, sticky="w")

            self.ind_widgets[ind_name] = {
                "active_var": active_var,
                "group_var": group_var,
                "mode_var": mode_var,
                "params": cfg.get("params", {}) # Giữ nguyên params mặc định
            }
            row += 1

    def _build_voting_tab(self):
        rules = self.brain_data.get("voting_rules", {})
        
        frame = ctk.CTkFrame(self.tab_rules)
        frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(frame, text="Phiếu Nghịch Tối Đa (Max Opposite):").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.vote_max_opp = ctk.StringVar(value=str(rules.get("max_opposite", 0)))
        ctk.CTkEntry(frame, textvariable=self.vote_max_opp, width=100).grid(row=0, column=1, padx=10, pady=10)

        ctk.CTkLabel(frame, text="Phiếu Trắng Tối Đa (Max None):").grid(row=1, column=0, padx=10, pady=10, sticky="w")
        self.vote_max_none = ctk.StringVar(value=str(rules.get("max_none", 1)))
        ctk.CTkEntry(frame, textvariable=self.vote_max_none, width=100).grid(row=1, column=1, padx=10, pady=10)

        ctk.CTkLabel(frame, text="Master Rule (Khi lố max_none):").grid(row=2, column=0, padx=10, pady=10, sticky="w")
        self.vote_master = ctk.StringVar(value=rules.get("master_rule", "FIX"))
        ctk.CTkComboBox(frame, values=["FIX", "PASS"], variable=self.vote_master, width=100).grid(row=2, column=1, padx=10, pady=10)

    def _build_dca_pca_tab(self):
        dca_cfg = self.brain_data.get("dca_config", {})
        pca_cfg = self.brain_data.get("pca_config", {})

        # --- DCA ---
        dca_frame = ctk.CTkFrame(self.tab_dca_pca)
        dca_frame.pack(fill="x", padx=10, pady=10)
        
        self.dca_active = ctk.BooleanVar(value=dca_cfg.get("ENABLED", False))
        ctk.CTkCheckBox(dca_frame, text="Kích hoạt AUTO DCA (Gồng lỗ/Bắt đáy)", variable=self.dca_active, font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(dca_frame, text="Max Steps (Số lệnh):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.dca_steps = ctk.StringVar(value=str(dca_cfg.get("MAX_STEPS", 3)))
        ctk.CTkEntry(dca_frame, textvariable=self.dca_steps, width=100).grid(row=1, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(dca_frame, text="Step Multiplier (Lot * x):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.dca_mult = ctk.StringVar(value=str(dca_cfg.get("STEP_MULTIPLIER", 1.5)))
        ctk.CTkEntry(dca_frame, textvariable=self.dca_mult, width=100).grid(row=2, column=1, padx=10, pady=5)

        # --- PCA ---
        pca_frame = ctk.CTkFrame(self.tab_dca_pca)
        pca_frame.pack(fill="x", padx=10, pady=10)

        self.pca_active = ctk.BooleanVar(value=pca_cfg.get("ENABLED", False))
        ctk.CTkCheckBox(pca_frame, text="Kích hoạt AUTO PCA (Nhồi thuận Trend)", variable=self.pca_active, font=("Arial", 14, "bold")).grid(row=0, column=0, columnspan=2, padx=10, pady=10, sticky="w")
        
        ctk.CTkLabel(pca_frame, text="Max Steps (Số lệnh):").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.pca_steps = ctk.StringVar(value=str(pca_cfg.get("MAX_STEPS", 2)))
        ctk.CTkEntry(pca_frame, textvariable=self.pca_steps, width=100).grid(row=1, column=1, padx=10, pady=5)
        
        ctk.CTkLabel(pca_frame, text="Step Multiplier (Lot * x):").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.pca_mult = ctk.StringVar(value=str(pca_cfg.get("STEP_MULTIPLIER", 0.5)))
        ctk.CTkEntry(pca_frame, textvariable=self.pca_mult, width=100).grid(row=2, column=1, padx=10, pady=5)

    def save_strategy(self):
        try:
            # 1. Thu thập Indicator config
            new_inds = {}
            for ind_name, widgets in self.ind_widgets.items():
                mode_val = widgets["mode_var"].get()
                new_inds[ind_name] = {
                    "active": widgets["active_var"].get(),
                    "group": widgets["group_var"].get(),
                    "active_modes": [mode_val] if mode_val != "ANY" else ["ANY"], 
                    "params": widgets["params"] # Pass default params back
                }

            # 2. Thu thập Voting rules
            new_voting = {
                "max_opposite": int(self.vote_max_opp.get() or 0),
                "max_none": int(self.vote_max_none.get() or 1),
                "master_rule": self.vote_master.get()
            }

            # 3. Thu thập DCA/PCA config
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

            # 4. Đóng gói Flat JSON
            output_data = {
                "voting_rules": new_voting,
                "indicators": new_inds,
                "dca_config": new_dca,
                "pca_config": new_pca,
                # Giữ nguyên một số thông số nền tảng nếu có
                "trend_timeframe": "1h",
                "entry_timeframe": "15m",
                "NUM_H1_BARS": 70,
                "NUM_M15_BARS": 70
            }

            os.makedirs(os.path.dirname(BRAIN_SETTINGS_PATH), exist_ok=True)
            with open(BRAIN_SETTINGS_PATH, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=4)

            messagebox.showinfo("Thành công", f"Đã lưu cấu hình Bot V3.0 vào\n{BRAIN_SETTINGS_PATH}\n(Daemon sẽ tự động Hot-Reload)")
            self.destroy()

        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể lưu cấu hình:\n{e}")