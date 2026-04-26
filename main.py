# -*- coding: utf-8 -*-
# FILE: main.py
# V6.9.3: REFACTORED CORE - UI CONTEXT SYNC HOTFIX (KAISER EDITION)

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox, Menu
import threading
import time
import sys
import json
import os
import subprocess
from datetime import datetime
import MetaTrader5 as mt5
import logging
from core.logger_setup import setup_logging  # [NEW V4.3] Import hệ thống Log 3 lớp
import config
from core.exness_connector import ExnessConnector
from core.checklist_manager import ChecklistManager
from core.trade_manager import TradeManager
from core.storage_manager import load_state, save_state
from core.signal_listener import SignalListener

import ui_panels
import ui_popups

# [V3.0] Import giao diện Strategy Sandbox
from ui_bot_strategy import BotStrategyUI

TSL_SETTINGS_FILE = "data/tsl_settings.json"
PRESETS_FILE = "data/presets_config.json"
BRAIN_SETTINGS_FILE = "data/brain_settings.json"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

FONT_MAIN = ("Roboto", 13)
FONT_BOLD = ("Roboto", 13, "bold")
FONT_EQUITY = ("Roboto", 36, "bold")
FONT_PNL = ("Roboto", 18, "bold")
FONT_SECTION = ("Roboto", 12, "bold")
FONT_BIG_VAL = ("Consolas", 20, "bold")
FONT_PRICE = ("Roboto", 32, "bold")
FONT_FEE = ("Roboto", 13, "bold")

COL_GREEN = "#00C853"
COL_RED = "#D50000"
COL_BLUE_ACCENT = "#1565C0"
COL_GRAY_BTN = "#424242"
COL_WARN = "#FFAB00"
COL_BOT_TAG = "#E040FB"


class Suppress10025Filter(logging.Filter):
    def filter(self, record):
        return "Retcode: 10025" not in record.getMessage()


main_logger = logging.getLogger("ExnessBot")
main_logger.addFilter(Suppress10025Filter())


class BotUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("RiceAutoTrading - Master Control V6.9.3 (Kaiser Edition)")
        self.geometry("1650x950")

        self.var_auto_trade = tk.BooleanVar(value=False)
        self.var_assist_math_sl = tk.BooleanVar(value=False)
        self.var_assist_preset_tp = tk.BooleanVar(value=False)
        self.var_assist_dca = tk.BooleanVar(value=False)
        self.var_assist_pca = tk.BooleanVar(value=False)

        self.var_strict_mode = tk.BooleanVar(value=config.STRICT_MODE_DEFAULT)
        self.var_confirm_close = tk.BooleanVar(value=True)
        self.var_account_type = tk.StringVar(value=config.DEFAULT_ACCOUNT_TYPE)

        self.var_manual_lot = tk.StringVar(value="")
        self.var_manual_tp = tk.StringVar(value="")
        self.var_manual_sl = tk.StringVar(value="")
        self.var_bypass_checklist = tk.BooleanVar(
            value=config.MANUAL_CONFIG["BYPASS_CHECKLIST"]
        )
        self.var_direction = tk.StringVar(value="BUY")

        self.tactic_states = {
            "BE": True,
            "PNL": False,
            "STEP_R": True,
            "SWING": True,
            "AUTO_DCA": False,
            "AUTO_PCA": False,
        }
        self.running = True
        self.tsl_states_map = {}
        self.last_price_val = 0.0
        self.latest_market_context = {}

        self.brain_status = "CHỜ KẾT NỐI..."
        self.brain_wakeup_time = 0
        self.brain_active_symbols = []

        self.daemon_process = None

        self.load_settings()
        setattr(config, "UI_ACTIVE_SYMBOL", config.DEFAULT_SYMBOL)

        self.connector = ExnessConnector()
        self.connector.connect()
        self.checklist_mgr = ChecklistManager(self.connector)
        self.trade_mgr = TradeManager(
            self.connector, self.checklist_mgr, log_callback=self.log_message
        )

        self.grid_columnconfigure(0, weight=0, minsize=420)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frm_left = ctk.CTkScrollableFrame(
            self, width=400, corner_radius=0, label_text=""
        )
        self.frm_left.grid(row=0, column=0, sticky="nswe")
        self.frm_left.grid_columnconfigure(0, weight=1)

        self.frm_right = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.frm_right.grid(row=0, column=1, sticky="nswe", padx=10, pady=10)

        ui_panels.setup_left_panel(self, self.frm_left)
        ui_panels.setup_right_panel(self, self.frm_right)

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.start_daemon_process()
        self.thread = threading.Thread(target=self.bg_update_loop, daemon=True)
        self.thread.start()

        self.signal_listener = SignalListener(
            trade_manager=self.trade_mgr,
            get_auto_trade_cb=lambda: self.var_auto_trade.get(),
            get_preset_cb=lambda: self.cbo_preset.get(),
            get_tsl_mode_cb=self.get_current_tactic_string,
            ui_heartbeat_cb=self.update_brain_heartbeat,
            log_cb=lambda msg, error=False: self.log_message(
                msg, error=error, target="bot"
            ),
        )
        self.signal_listener.start()

        self.log_message(
            "Hệ thống V6.9.3 (Đã tích hợp Sandbox V3.0 & Fix UI Sync) sẵn sàng."
        )

    def start_daemon_process(self):
        try:
            self.daemon_process = subprocess.Popen([sys.executable, "bot_daemon.py"])
            self.log_message("🚀 Đã kích hoạt Bot Daemon ngầm.", target="bot")
        except Exception as e:
            self.log_message(f"❌ Lỗi kích hoạt Daemon: {e}", error=True, target="bot")

    def on_closing(self):
        self.running = False
        if hasattr(self, "signal_listener"):
            self.signal_listener.stop()
        if self.daemon_process:
            self.daemon_process.terminate()
            self.daemon_process.wait()
        try:
            mt5.shutdown()
        except:
            pass
        self.destroy()
        sys.exit(0)

    def _save_brain_live_config(self):
        os.makedirs("data", exist_ok=True)

        # 1. Đọc dữ liệu JSON hiện tại (để giữ lại cấu hình Sandbox)
        existing_data = {}
        try:
            if os.path.exists(BRAIN_SETTINGS_FILE):
                with open(BRAIN_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
        except:
            pass

        # 2. Merge dữ liệu từ config hiện tại (của Main UI)
        for k in dir(config):
            if not k.startswith("__") and k != "COIN_LIST":
                val = getattr(config, k)
                if isinstance(val, (int, float, str, bool, list, dict)):
                    # [FIX]: CẤM ghi đè các cụm Key thuộc thẩm quyền của Sandbox
                    if k not in [
                        "indicators",
                        "voting_rules",
                        "risk_tsl",
                        "dca_config",
                        "pca_config",
                    ]:
                        existing_data[k] = val

        # 3. Ghi lại vào file
        try:
            with open(BRAIN_SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, indent=4)
        except Exception as e:
            self.log_message(f"Lỗi đồng bộ cấu hình (Hot-Reload): {e}", error=True)

    def update_brain_heartbeat(self, heartbeat: dict):
        self.brain_status = heartbeat.get("status", "UNKNOWN")
        self.brain_wakeup_time = heartbeat.get("wakeup_time", 0)
        self.brain_active_symbols = heartbeat.get("active_symbols", [])

        contexts = heartbeat.get("contexts", {})
        if contexts:
            self.latest_market_context = contexts

    def on_auto_trade_toggle(self):
        # [FIX] Ép lưu cấu hình ngay lập tức để Daemon ngầm nhận được tín hiệu
        config.AUTO_TRADE_ENABLED = self.var_auto_trade.get()
        self._save_brain_live_config()

        if self.var_auto_trade.get():
            self.ind_auto_light.configure(fg_color=COL_GREEN)
            self.log_message(
                "🟢 AUTO-TRADE DAEMON ĐÃ BẬT. Bot sẽ tự động bắn lệnh.", target="bot"
            )
        else:
            self.ind_auto_light.configure(fg_color=COL_RED)
            self.log_message(
                "🔴 AUTO-TRADE DAEMON ĐÃ TẮT. Chuyển về chế độ bắn tay (Manual).",
                target="bot",
            )

    def get_current_tactic_string(self):
        active = [k for k, v in self.tactic_states.items() if v]
        base_tactic = "+".join(active) if active else "OFF"
        if self.var_assist_dca.get() and "AUTO_DCA" not in base_tactic:
            base_tactic += "+AUTO_DCA"
        if self.var_assist_pca.get() and "AUTO_PCA" not in base_tactic:
            base_tactic += "+AUTO_PCA"
        return base_tactic

    def toggle_tactic(self, mode):
        self.tactic_states[mode] = not self.tactic_states[mode]
        self.update_tactic_buttons_ui()

    def update_tactic_buttons_ui(self):
        def set_btn(btn, is_active):
            btn.configure(fg_color=COL_BLUE_ACCENT if is_active else COL_GRAY_BTN)

        set_btn(self.btn_tactic_be, self.tactic_states["BE"])
        set_btn(self.btn_tactic_pnl, self.tactic_states["PNL"])
        set_btn(self.btn_tactic_step, self.tactic_states["STEP_R"])
        set_btn(self.btn_tactic_swing, self.tactic_states["SWING"])

        if hasattr(self, "btn_tactic_dca"):
            set_btn(self.btn_tactic_dca, self.tactic_states["AUTO_DCA"])
        if hasattr(self, "btn_tactic_pca"):
            set_btn(self.btn_tactic_pca, self.tactic_states["AUTO_PCA"])

    def on_symbol_change(self, new_symbol):
        config.UI_ACTIVE_SYMBOL = new_symbol
        self._save_brain_live_config()
        self.lbl_dashboard_price.configure(text="Đang nạp...", text_color="gray")
        threading.Thread(target=lambda: mt5.symbol_select(new_symbol, True)).start()

    def on_direction_change(self, value):
        self.var_direction.set(value)
        sym = self.cbo_symbol.get()
        if value == "BUY":
            self.btn_action.configure(
                text=f"VÀO LỆNH MUA {sym}", fg_color=COL_GREEN, hover_color="#009624"
            )
        else:
            self.btn_action.configure(
                text=f"VÀO LỆNH BÁN {sym}", fg_color=COL_RED, hover_color="#B71C1C"
            )

    # ==========================================
    # CÁC HÀM MỞ POPUP & GIAO DIỆN PHỤ
    # ==========================================
    def open_bot_setting_popup(self):
        ui_popups.open_bot_setting_popup(self)

    def open_preset_config_popup(self):
        ui_popups.open_preset_config_popup(self)

    def open_tsl_popup(self):
        ui_popups.open_tsl_popup(self)

    def open_edit_popup(self, ticket):
        ui_popups.open_edit_popup(self, ticket)

    def show_history_popup(self):
        ui_popups.show_history_popup(self)

    # [V3.0] Hàm gọi Strategy Sandbox
    def open_strategy_sandbox(self):
        sandbox_window = BotStrategyUI(self)

        def on_sandbox_close():
            self._save_brain_live_config()
            self.log_message(
                "📡 [V3.0] Đã đóng Sandbox. Daemon sẽ tự động nạp cấu hình mới (Hot-Reload).",
                error=False,
            )
            sandbox_window.destroy()

        sandbox_window.protocol("WM_DELETE_WINDOW", on_sandbox_close)

    # ==========================================

    def load_settings(self):
        if os.path.exists(TSL_SETTINGS_FILE):
            try:
                with open(TSL_SETTINGS_FILE, "r") as f:
                    config.TSL_CONFIG.update(json.load(f))
            except:
                pass
        if os.path.exists(PRESETS_FILE):
            try:
                with open(PRESETS_FILE, "r") as f:
                    config.PRESETS.update(json.load(f))
            except:
                pass
        if os.path.exists(BRAIN_SETTINGS_FILE):
            try:
                with open(BRAIN_SETTINGS_FILE, "r") as f:
                    bs = json.load(f)
                    for k, v in bs.items():
                        if hasattr(config, k) and k != "COIN_LIST":
                            setattr(config, k, v)
            except:
                pass

    def save_settings(self):
        try:
            os.makedirs("data", exist_ok=True)
            with open(TSL_SETTINGS_FILE, "w") as f:
                json.dump(config.TSL_CONFIG, f, indent=4)
            with open(PRESETS_FILE, "w") as f:
                json.dump(config.PRESETS, f, indent=4)
        except:
            pass

    def get_fee_config(self, symbol):
        acc_type = self.cbo_account_type.get()
        if acc_type in ["PRO", "STANDARD"]:
            return 0.0
        specific_rate = config.COMMISSION_RATES.get(symbol, -1)
        if specific_rate != -1:
            return specific_rate
        acc_cfg = config.ACCOUNT_TYPES_CONFIG.get(
            acc_type, config.ACCOUNT_TYPES_CONFIG["STANDARD"]
        )
        return acc_cfg.get("COMMISSION_PER_LOT", 0.0)

    def bg_update_loop(self):
        while self.running:
            try:
                sym = self.cbo_symbol.get()
                new_map = self.trade_mgr.update_running_trades(
                    self.cbo_account_type.get(), self.latest_market_context
                )
                self.tsl_states_map.update(new_map)

                acc = self.connector.get_account_info()
                tick = mt5.symbol_info_tick(sym)
                bot_magic = getattr(config, "BOT_MAGIC_NUMBER", 9999)
                manual_magic = getattr(config, "MANUAL_MAGIC_NUMBER", 8888)
                pos = [
                    p
                    for p in self.connector.get_all_open_positions()
                    if p.magic in (bot_magic, manual_magic)
                ]
                self.after(
                    0,
                    self.update_ui,
                    acc,
                    self.trade_mgr.state,
                    self.checklist_mgr.run_pre_trade_checks(
                        acc, self.trade_mgr.state, sym, self.var_strict_mode.get()
                    ),
                    tick,
                    self.cbo_preset.get(),
                    sym,
                    pos,
                )
            except:
                pass
            time.sleep(config.LOOP_SLEEP_SECONDS)

    def update_ui(self, acc, state, check_res, tick, preset, sym, positions):
        sym_count = len(self.brain_active_symbols)
        if "SLEEPING" in self.brain_status:
            rem = int(self.brain_wakeup_time - time.time())
            if rem > 0:
                self.lbl_brain_status.configure(
                    text=f"🧠 BRAIN: SLEEP ({rem}s) [{sym_count} Sym]",
                    text_color="#2196F3",
                )
            else:
                self.lbl_brain_status.configure(
                    text=f"🧠 BRAIN: SYNC... [{sym_count} Sym]", text_color=COL_WARN
                )
        elif self.brain_status in ["HEALTHY", "MONITORING"]:
            self.lbl_brain_status.configure(
                text=f"🧠 BRAIN: ONLINE [{sym_count} Sym]", text_color=COL_GREEN
            )
        else:
            self.lbl_brain_status.configure(
                text=f"🧠 BRAIN: {self.brain_status}", text_color=COL_RED
            )

        sym_ctx = self.latest_market_context.get(sym, {})

        if sym_ctx:
            # 1. Đọc khung thời gian Ngài đang chọn xem trên Dashboard
            selected_tf = getattr(
                self, "var_dashboard_tf", tk.StringVar(value="G1")
            ).get()

            # 2. Lấy dữ liệu kỹ thuật theo khung đó
            sh = sym_ctx.get(f"swing_high_{selected_tf}", "--")
            sl = sym_ctx.get(f"swing_low_{selected_tf}", "--")
            atr = sym_ctx.get(f"atr_{selected_tf}", "--")

            # Ép UI chỉ đọc Trend của Group đang được chọn ở ComboBox
            tr = sym_ctx.get(f"trend_{selected_tf}", "NONE")

            mode = sym_ctx.get("market_mode", "ANY")
            mode_src = sym_ctx.get("mode_source", "NONE")

            # 3. Đổ dữ liệu vào DÒNG 1
            m_color = (
                COL_GREEN if tr == "UP" else (COL_RED if tr == "DOWN" else "#78909C")
            )
            self.lbl_market_mode.configure(
                text=f"Mode: {mode} (by {mode_src}) | Trend: {tr}", text_color=m_color
            )

            # 4. Đổ dữ liệu vào DÒNG 2: Thông số (Cái Label lbl_market_context)
            if tr == "UP":
                ctx_color = COL_GREEN
            elif tr == "DOWN":
                ctx_color = COL_RED
            else:
                ctx_color = "white"

            if atr == 0.0 or atr == "--":
                self.lbl_market_context.configure(
                    text="Syncing Data...", text_color="#FFA500"
                )
            else:
                sh_str = f"{sh:.2f}" if isinstance(sh, (int, float)) else "--"
                sl_str = f"{sl:.2f}" if isinstance(sl, (int, float)) else "--"
                atr_str = f"{atr:.2f}" if isinstance(atr, (int, float)) else "--"

                self.lbl_market_context.configure(
                    text=f"H: {sh_str} | L: {sl_str} | ATR: {atr_str}",
                    text_color=ctx_color,
                )
        else:
            # [FIX CORE UI]: Làm sạch nhãn nếu không có dữ liệu (Ví dụ đổi sang đồng Coin không có trong Watchlist)
            self.lbl_market_mode.configure(
                text=f"Mode: -- | Trend: --", text_color="gray"
            )
            self.lbl_market_context.configure(
                text="H: -- | L: -- | ATR: --", text_color="gray"
            )

        d = self.seg_direction.get()
        self.var_direction.set(d)
        cur_tactic_str = self.get_current_tactic_string()

        balance = acc["balance"] if acc else 1.0
        if balance == 0:
            balance = 1.0

        if acc:
            self.lbl_equity.configure(text=f"${acc['equity']:,.2f}")
            self.lbl_acc_info.configure(
                text=f"ID: {acc['login']}\nServer: {acc['server']}"
            )
        pnl = state["pnl_today"]
        self.lbl_stats.configure(
            text=f"PNL: ${pnl:.2f}",
            text_color=COL_GREEN if pnl >= 0 else COL_RED,
        )

        cur_price, c_size, point = 0.0, 1.0, 0.00001
        if tick:
            cur_price = tick.ask if d == "BUY" else tick.bid
            self.lbl_dashboard_price.configure(
                text=f"{cur_price:.2f}",
                text_color=COL_GREEN if cur_price >= self.last_price_val else COL_RED,
            )
            self.last_price_val = cur_price
            s_info = mt5.symbol_info(sym)
            if s_info:
                c_size, point = s_info.trade_contract_size, s_info.point

        for item in check_res["checks"]:
            name, stt, msg = item["name"], item["status"], item["msg"]
            if name in self.check_labels:
                self.check_labels[name].configure(
                    text=f"{'✔' if stt == 'OK' else '✖'} {name}: {msg}",
                    text_color=COL_GREEN
                    if stt == "OK"
                    else (COL_WARN if stt == "WARN" else COL_RED),
                )

        if tick and acc:
            params = config.PRESETS.get(preset, config.PRESETS["SCALPING"])
            current_risk_pct = params.get("RISK_PERCENT", 0.3)
            sl_pct_display = params.get("SL_PERCENT", 0.0)
            tp_r_display = params.get("TP_RR_RATIO", 0.0)

            self.lbl_head_sl.configure(text=f"STOPLOSS ({sl_pct_display}%)")
            self.lbl_head_tp.configure(text=f"TARGET ({tp_r_display}R)")

            try:
                mlot = float(self.var_manual_lot.get() or 0)
            except:
                mlot = 0.0

            f_lot = mlot if mlot > 0 else 0
            # --- [V4.3] TÍNH TOÁN LOT PREVIEW CHÍNH XÁC ---
            if f_lot == 0:
                risk_usd = acc["equity"] * (current_risk_pct / 100)
                sl_dist = cur_price * (params["SL_PERCENT"] / 100)

                # Tính phí nếu Preset bật STRICT_RISK
                strict_fee = 0.0
                if params.get("STRICT_RISK", False):
                    comm_rate = self.get_fee_config(sym)
                    spread_cost_per_lot = (tick.ask - tick.bid) * c_size
                    strict_fee = comm_rate + spread_cost_per_lot

                if sl_dist > 0:
                    # Mức lỗ trên 1 lot (Profit âm)
                    loss_per_lot = sl_dist * c_size
                    # Lot = Risk / (Lỗ do giá + Phí sàn)
                    raw_calc = risk_usd / (loss_per_lot + strict_fee)
                    f_lot = round(raw_calc / config.LOT_STEP) * config.LOT_STEP

            if f_lot < config.MIN_LOT_SIZE:
                self.lbl_prev_lot.configure(
                    text=f"LOT: KHÔNG HỢP LỆ (Min {config.MIN_LOT_SIZE})",
                    text_color=COL_RED,
                )
                f_lot = config.MIN_LOT_SIZE
            else:
                f_lot = min(f_lot, config.MAX_LOT_SIZE)
                self.lbl_prev_lot.configure(
                    text=f"{'(TAY)' if mlot > 0 else '(TỰ ĐỘNG)'} VOL: {f_lot:.2f}",
                    text_color="white" if mlot == 0 else "#FFD700",
                )

            comm_rate = self.get_fee_config(sym)
            comm_total = comm_rate * f_lot
            spread_cost = (tick.ask - tick.bid) * f_lot * c_size

            acc_type = self.cbo_account_type.get()
            if acc_type in ["PRO", "STANDARD"]:
                self.lbl_fee_info.configure(
                    text=f"Chi phí (Spread): -${spread_cost:.2f}"
                )
            else:
                self.lbl_fee_info.configure(text=f"Chi phí (Comm): -${comm_total:.2f}")

            try:
                msl, mtp = (
                    float(self.var_manual_sl.get() or 0),
                    float(self.var_manual_tp.get() or 0),
                )
            except:
                msl, mtp = 0, 0

            auto_sl_dist = cur_price * (params["SL_PERCENT"] / 100)
            p_sl = (
                msl
                if msl > 0
                else (
                    cur_price - auto_sl_dist if d == "BUY" else cur_price + auto_sl_dist
                )
            )
            p_tp = (
                mtp
                if mtp > 0
                else (
                    cur_price + abs(cur_price - p_sl) * params["TP_RR_RATIO"]
                    if d == "BUY"
                    else cur_price - abs(cur_price - p_sl) * params["TP_RR_RATIO"]
                )
            )

            is_valid_sl = True
            if d == "BUY" and p_sl >= cur_price:
                is_valid_sl = False
            if d == "SELL" and p_sl <= cur_price:
                is_valid_sl = False

            if is_valid_sl:
                self.lbl_prev_sl.configure(text=f"{p_sl:.2f}", text_color=COL_RED)
                loss_dist = abs(cur_price - p_sl)
                loss_val = loss_dist * f_lot * c_size
                loss_pct = (loss_val / balance) * 100
                self.lbl_prev_risk.configure(
                    text=f"-${loss_val:.2f} ({loss_pct:.2f}%)", text_color=COL_RED
                )
            else:
                self.lbl_prev_sl.configure(text="LỖI", text_color=COL_WARN)
                self.lbl_prev_risk.configure(text="$ ---", text_color=COL_WARN)

            is_valid_tp = True
            if d == "BUY" and p_tp <= cur_price:
                is_valid_tp = False
            if d == "SELL" and p_tp >= cur_price:
                is_valid_tp = False

            if is_valid_tp:
                self.lbl_prev_tp.configure(text=f"{p_tp:.2f}", text_color=COL_GREEN)
                prof_dist = abs(p_tp - cur_price)
                prof_val = prof_dist * f_lot * c_size
                prof_pct = (prof_val / balance) * 100
                self.lbl_prev_rew.configure(
                    text=f"+${prof_val:.2f} ({prof_pct:.2f}%)", text_color=COL_GREEN
                )
            else:
                self.lbl_prev_tp.configure(text="LỖI", text_color=COL_WARN)
                self.lbl_prev_rew.configure(text="$ ---", text_color=COL_WARN)

            if cur_tactic_str == "OFF":
                self.lbl_tsl_preview.configure(text="TSL: OFF")
            else:
                milestones = []
                one_r_dist = abs(cur_price - p_sl)
                is_buy = d == "BUY"
                t_cfg = config.TSL_CONFIG

                if "BE" in cur_tactic_str and one_r_dist > 0:
                    trig_r = t_cfg.get("BE_OFFSET_RR", 0.8)
                    trig_p = (
                        cur_price + (one_r_dist * trig_r)
                        if is_buy
                        else cur_price - (one_r_dist * trig_r)
                    )
                    fee_d = (
                        (comm_total + spread_cost) / (f_lot * c_size)
                        if (f_lot * c_size) > 0
                        else 0
                    )
                    mode = t_cfg.get("BE_MODE", "SOFT")
                    base = (
                        cur_price - fee_d
                        if (is_buy and mode == "SOFT")
                        else (
                            cur_price + fee_d
                            if (is_buy and mode == "SMART")
                            else cur_price
                        )
                    )
                    if not is_buy:
                        base = (
                            cur_price + fee_d
                            if mode == "SOFT"
                            else (cur_price - fee_d if mode == "SMART" else cur_price)
                        )
                    be_sl = (
                        base + (t_cfg.get("BE_OFFSET_POINTS", 0) * point)
                        if is_buy
                        else base - (t_cfg.get("BE_OFFSET_POINTS", 0) * point)
                    )
                    milestones.append(
                        (abs(cur_price - trig_p), f"BE | {trig_p:.2f} -> {be_sl:.2f}")
                    )

                if "STEP_R" in cur_tactic_str and one_r_dist > 0:
                    sz, rt = (
                        t_cfg.get("STEP_R_SIZE", 1.0),
                        t_cfg.get("STEP_R_RATIO", 0.8),
                    )
                    n_trig = (
                        cur_price + (sz * one_r_dist)
                        if is_buy
                        else cur_price - (sz * one_r_dist)
                    )
                    n_sl = (
                        cur_price + (sz * one_r_dist * rt)
                        if is_buy
                        else cur_price - (sz * one_r_dist * rt)
                    )
                    milestones.append(
                        (
                            abs(cur_price - n_trig),
                            f"Step 1 | {n_trig:.2f} -> {n_sl:.2f}",
                        )
                    )

                if "PNL" in cur_tactic_str and t_cfg.get("PNL_LEVELS") and acc:
                    lvl = t_cfg["PNL_LEVELS"][0]
                    req_profit_usd = acc["balance"] * (lvl[0] / 100.0)
                    trig_p = (
                        cur_price + (req_profit_usd / (f_lot * c_size))
                        if is_buy
                        else cur_price - (req_profit_usd / (f_lot * c_size))
                    )
                    milestones.append(
                        (abs(cur_price - trig_p), f"PnL {lvl[0]}% | {trig_p:.2f}")
                    )

                if "SWING" in cur_tactic_str and sym_ctx:
                    brain = self.trade_mgr._get_brain_settings()
                    trail_group = brain.get("risk_tsl", {}).get("base_sl", "G2")
                    market_mode = sym_ctx.get("market_mode", "ANY")
                    if trail_group == "DYNAMIC":
                        trail_group = "G1" if market_mode in ["TREND", "BREAKOUT"] else "G2"
                        
                    sh, sl, atr_val = (
                        sym_ctx.get(f"swing_high_{trail_group}", "--"),
                        sym_ctx.get(f"swing_low_{trail_group}", "--"),
                        sym_ctx.get(f"atr_{trail_group}", "--"),
                    )
                    if sh != "--" and sl != "--" and atr_val != "--":
                        t_buf = getattr(config, "trail_atr_buffer", 0.2)
                        swing_sl = (
                            float(sl) - (t_buf * float(atr_val))
                            if is_buy
                            else float(sh) + (t_buf * float(atr_val))
                        )
                        milestones.append((0, f"SWING | Đợi mốc ➔ {swing_sl:.2f}"))

                if milestones:
                    closest = sorted(milestones, key=lambda x: x[0])[0][1]
                    self.lbl_tsl_preview.configure(text=f"TSL: {closest}")
                else:
                    self.lbl_tsl_preview.configure(text="TSL: Đang theo dõi...")

        existing_items = self.tree.get_children()
        current_tickets_on_chart = []
        child_to_parent = self.trade_mgr.state.get("child_to_parent", {})

        for p in positions:
            ticket_str = str(p.ticket)
            current_tickets_on_chart.append(ticket_str)

            p_tick = mt5.symbol_info_tick(p.symbol)
            p_sym_info = mt5.symbol_info(p.symbol)
            p_c_size = p_sym_info.trade_contract_size if p_sym_info else 1.0
            swap_val = getattr(p, "swap", 0.0)

            current_spread = (p_tick.ask - p_tick.bid) if p_tick else 0.0
            spread_cost_usd = current_spread * p.volume * p_c_size
            comm_rate = self.get_fee_config(p.symbol)
            comm_total_usd = comm_rate * p.volume

            acc_type = self.cbo_account_type.get()
            if acc_type in ["PRO", "STANDARD"]:
                fee_str = f"Spr: -${spread_cost_usd:.2f} | Sw: ${swap_val:.2f}"
            else:
                fee_str = f"Com: -${comm_total_usd:.2f} | Sw: ${swap_val:.2f}"

            time_str = datetime.fromtimestamp(p.time).strftime("%d/%m %H:%M")
            is_buy = p.type == mt5.ORDER_TYPE_BUY
            icon = "🟢" if is_buy else "🔴"
            side_txt = "BUY" if is_buy else "SELL"

            display_ticket = f"#{ticket_str}"
            is_child = ticket_str in child_to_parent

            if is_child:
                display_ticket = f" ┗━ #{ticket_str}"

            origin_tag = "[UI]"
            if "[BOT]" in p.comment:
                origin_tag = "[BOT]"
            elif "_Child" in p.comment:
                origin_tag = "[UI+BOT]"

            order_str = f"{origin_tag} {icon} {side_txt} {p.volume:.2f} {p.symbol} @ {p.price_open:.2f}"

            sl_txt = f"{p.sl:.2f}" if p.sl > 0 else "---"
            tp_txt = f"{p.tp:.2f}" if p.tp > 0 else "---"
            targets_str = f"{sl_txt}  |  {tp_txt}"

            risk_usd = abs(p.price_open - p.sl) * p.volume * p_c_size if p.sl > 0 else 0
            rew_usd = abs(p.price_open - p.tp) * p.volume * p_c_size if p.tp > 0 else 0
            risk_pct = (risk_usd / balance * 100) if balance > 0 else 0
            rew_pct = (rew_usd / balance * 100) if balance > 0 else 0

            is_sl_in_profit = False
            if is_buy and p.sl > p.price_open:
                is_sl_in_profit = True
            if not is_buy and p.sl > 0 and p.sl < p.price_open:
                is_sl_in_profit = True

            if p.sl == 0:
                risk_str = "No SL"
            elif is_sl_in_profit:
                risk_str = f"+${risk_usd:.1f} ({risk_pct:.1f}%)"
            else:
                risk_str = f"-${risk_usd:.1f} ({risk_pct:.1f}%)"

            rew_str = f"+${rew_usd:.1f} ({rew_pct:.1f}%)" if p.tp > 0 else "No TP"
            rr_str = f"{risk_str}  |  {rew_str}"

            stt_txt = self.tsl_states_map.get(p.ticket, "Running")
            tactic_info = self.trade_mgr.get_trade_tactic(p.ticket)
            stt_extras = []
            if "AUTO_DCA" in tactic_info:
                stt_extras.append("DCA")
            if "AUTO_PCA" in tactic_info:
                stt_extras.append("PCA")
            if stt_extras:
                stt_txt += f" | +{'/'.join(stt_extras)}"

            values_data = (
                display_ticket,
                time_str,
                order_str,
                targets_str,
                fee_str,
                rr_str,
                f"${p.profit:.2f}",
                stt_txt,
                "❌",
            )
            tag_to_apply = "buy_row" if is_buy else "sell_row"

            if ticket_str in existing_items:
                self.tree.item(ticket_str, values=values_data, tags=(tag_to_apply,))
            else:
                self.tree.insert(
                    "", "end", iid=ticket_str, values=values_data, tags=(tag_to_apply,)
                )

        for item in existing_items:
            if item not in current_tickets_on_chart:
                self.tree.delete(item)

    def on_click_trade(self):
        d, s, p, t = (
            self.seg_direction.get(),
            self.cbo_symbol.get(),
            self.cbo_preset.get(),
            self.get_current_tactic_string(),
        )
        try:
            ml, mt, ms = (
                float(self.var_manual_lot.get() or 0),
                float(self.var_manual_tp.get() or 0),
                float(self.var_manual_sl.get() or 0),
            )
        except:
            ml = mt = ms = 0.0

        if ms == 0.0 and self.var_assist_math_sl.get():
            target_sym_ctx = self.latest_market_context.get(s, {})
            if d == "BUY":
                sl_val = target_sym_ctx.get(
                    "swing_low_entry", target_sym_ctx.get("swing_low")
                )
            else:
                sl_val = target_sym_ctx.get(
                    "swing_high_entry", target_sym_ctx.get("swing_high")
                )

            atr_val = target_sym_ctx.get("atr_entry", target_sym_ctx.get("atr"))

            if sl_val and atr_val:
                sl_mult = getattr(config, "sl_atr_multiplier", 0.2)
                ms = (
                    float(sl_val) - (float(atr_val) * sl_mult)
                    if d == "BUY"
                    else float(sl_val) + (float(atr_val) * sl_mult)
                )
                self.log_message(f"🧠 Auto-Math SL: {ms:.2f}", error=False)

        def run_trade_thread():
            result = self.trade_mgr.execute_manual_trade(
                d,
                p,
                s,
                self.var_strict_mode.get(),
                ml,
                mt,
                ms,
                self.var_bypass_checklist.get(),
                t,
            )
            if "SUCCESS" not in result:
                self.log_message(f"❌ THẤT BẠI: {result}", error=True)

        threading.Thread(target=run_trade_thread).start()

    def log_message(self, msg, error=False, target="manual"):
        if "Retcode: 10025" in msg:
            return

        ts = time.strftime("%H:%M:%S")
        txt = f"[{ts}] {msg}\n"

        if "PnL: +$" in msg or "SUCCESS" in msg or "Húp" in msg:
            tag = "SUCCESS"
        elif "PnL: $-" in msg or error or "ERR" in msg or "FAIL" in msg:
            tag = "ERROR"
        elif "Đóng lệnh" in msg:
            tag = "INFO"
        elif "BUY" in msg:
            tag = "SUCCESS"
        elif "SELL" in msg:
            tag = "ERROR"
        else:
            tag = "INFO"

        self.after(0, lambda: self._write_log(txt, tag, target))

    def _write_log(self, txt, tag, target="manual"):
        widget = self.txt_log_bot if target == "bot" else self.txt_log_manual
        if widget.winfo_exists():
            widget.configure(state="normal")
            widget.insert("end", txt, tag)
            widget.see("end")
            widget.configure(state="disabled")

    def reset_daily_stats(self):
        if messagebox.askyesno("Xác nhận", "Reset thống kê ngày?"):
            self.trade_mgr.state.update(
                {
                    "pnl_today": 0.0,
                    "trades_today_count": 0,
                    "daily_loss_count": 0,
                    "daily_history": [],
                }
            )
            save_state(self.trade_mgr.state)

    def close_all_trades(self):
        items = self.tree.get_children()
        if not items:
            return
        if self.var_confirm_close.get() and not messagebox.askyesno(
            "Xác nhận", "ĐÓNG TOÀN BỘ LỆNH?"
        ):
            return
        for item in items:
            p = next(
                (
                    p
                    for p in self.connector.get_all_open_positions()
                    if p.ticket == int(item)
                ),
                None,
            )
            if p:
                threading.Thread(
                    target=lambda: self.connector.close_position(p)
                ).start()

    def close_selected_trades(self):
        selected = self.tree.selection()
        if not selected:
            return
        if self.var_confirm_close.get() and not messagebox.askyesno(
            "Xác nhận", f"Đóng {len(selected)} lệnh đã chọn?"
        ):
            return
        for item in selected:
            p = next(
                (
                    p
                    for p in self.connector.get_all_open_positions()
                    if p.ticket == int(item)
                ),
                None,
            )
            if p:
                threading.Thread(
                    target=lambda: self.connector.close_position(p)
                ).start()

    def on_tree_click(self, event):
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            col = self.tree.identify_column(event.x)
            row_id = self.tree.identify_row(event.y)
            if row_id and col == "#9":
                if self.var_confirm_close.get() and not messagebox.askyesno(
                    "Xác nhận", f"Đóng lệnh #{row_id}?"
                ):
                    return
                p = next(
                    (
                        p
                        for p in self.connector.get_all_open_positions()
                        if p.ticket == int(row_id)
                    ),
                    None,
                )
                if p:
                    threading.Thread(
                        target=lambda: self.connector.close_position(p)
                    ).start()

    def on_tree_right_click(self, event):
        row_id = self.tree.identify_row(event.y)
        selected = self.tree.selection()
        menu = Menu(self, tearoff=0)

        if len(selected) > 1:
            menu.add_command(
                label=f"❌ Đóng {len(selected)} Lệnh Đã Chọn",
                command=self.close_selected_trades,
            )
        else:
            if row_id:
                self.tree.selection_set(row_id)
                ticket = int(row_id)
                menu.add_command(
                    label=f"📝 Sửa lệnh #{ticket}",
                    command=lambda: self.open_edit_popup(ticket),
                )
                menu.add_separator()
                menu.add_command(
                    label="❌ Đóng Lệnh Này",
                    command=lambda: self.close_selected_trades(),
                )

        menu.post(event.x_root, event.y_root)


if __name__ == "__main__":
    # Khởi tạo hệ thống Log 3 Lớp trước khi bật App
    # data/logs/sẽ tự động được tạo ra
    setup_logging(debug_mode=getattr(config, "ENABLE_DEBUG_LOGGING", False))

    try:
        app = BotUI()
        app.mainloop()
    except KeyboardInterrupt:
        sys.exit(0)
