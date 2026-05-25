# -*- coding: utf-8 -*-
"""HEDGE Dual V1 manager.

This module owns HEDGE state only. It does not write BOT/manual/GRID state.
"""

import copy
import time
from datetime import datetime

import MetaTrader5 as mt5

from core.market_hours import is_symbol_trade_window_open
from core.position_classifier import is_hedge_position
from core.storage_manager import append_trade_log, get_magic_numbers, get_today_str

from .hedge_executor import HedgeExecutor
from .hedge_storage import load_hedge_settings, load_hedge_state, save_hedge_settings, save_hedge_state


class HedgeManager:
    def __init__(self, connector=None, data_engine=None, signal_generator=None, log_callback=None):
        self.connector = connector
        self.data_engine = data_engine
        self.signal_generator = signal_generator
        self.log_callback = log_callback
        self.executor = HedgeExecutor(connector=connector, log_callback=log_callback)
        self._decision_log_cache = {}

    def log(self, message, error=False):
        if self.log_callback:
            self.log_callback(f"[HEDGE] {message}", error=error, target="hedge")

    def reload(self):
        return {"settings": load_hedge_settings(), "state": load_hedge_state()}

    def _ensure_hedge_state(self, state):
        today = get_today_str()
        if state.get("date") != today:
            state["date"] = today
            state["hedge_pnl_today"] = 0.0
            state["hedge_sessions_today"] = 0
            state["hedge_daily_loss_count"] = 0
        state.setdefault("active_sessions", {})
        state.setdefault("last_decision", {})
        state.setdefault("last_decision_log_keys", {})
        state.setdefault("last_close_times", {})
        state.setdefault("last_loss_times", {})
        state.setdefault("global_cooldown_until", 0.0)
        state.setdefault("consecutive_losses", 0)
        state.setdefault("hedge_active_tickets", [])
        state.setdefault("hedge_pnl_today", 0.0)
        state.setdefault("hedge_sessions_today", 0)
        state.setdefault("hedge_daily_loss_count", 0)

    def _daily_safety(self, state, settings):
        max_daily_loss = float(settings.get("HEDGE_MAX_DAILY_LOSS", 0.0) or 0.0)
        if max_daily_loss > 0 and float(state.get("hedge_pnl_today", 0.0) or 0.0) <= -abs(max_daily_loss):
            return False, "HEDGE_DAILY_LOSS"
        max_day = int(settings.get("MAX_SESSIONS_PER_DAY", 0) or 0)
        if max_day > 0 and int(state.get("hedge_sessions_today", 0) or 0) >= max_day:
            return False, "MAX_SESSIONS_PER_DAY"
        return True, "OK"

    def settings_for_symbol(self, symbol, settings=None):
        base = copy.deepcopy(settings or load_hedge_settings())
        overrides = base.get("SYMBOL_OVERRIDES") or {}
        symbol_cfg = overrides.get(symbol, {}) if isinstance(overrides, dict) else {}
        if isinstance(symbol_cfg, dict):
            for key, value in symbol_cfg.items():
                if key != "SYMBOL_OVERRIDES":
                    base[key] = value
        return base

    def evaluate_entry_gate(self, symbol, context=None, settings=None):
        cfg = self.settings_for_symbol(symbol, settings)
        context = self._prepare_hedge_context(symbol, context or {}, cfg)
        reasons = []

        signal_on = bool(cfg.get("USE_SIGNAL_FILTER", False))
        latest_signal = int(context.get("latest_signal", 0) or 0)
        if signal_on and latest_signal == 0:
            reasons.append("SIGNAL_NONE")
        signal_status = "OFF" if not signal_on else ("PASS" if latest_signal != 0 else "WAIT")

        swing_on = bool(cfg.get("USE_SWING_FILTER", True))
        swing_status = "OFF"
        nearest_side = "---"
        if swing_on:
            price = float(context.get("hedge_current_price", context.get("current_price", 0.0)) or 0.0)
            group = str(cfg.get("SWING_GROUP", "G2") or "G2").upper()
            high = context.get("hedge_swing_high", context.get(f"swing_high_{group}", context.get("swing_high")))
            low = context.get("hedge_swing_low", context.get(f"swing_low_{group}", context.get("swing_low")))
            atr = context.get("hedge_atr", context.get(f"atr_{group}", context.get("atr")))
            try:
                high = float(high)
                low = float(low)
                atr = float(atr)
            except (TypeError, ValueError):
                high = low = atr = 0.0
            tolerance = atr * float(cfg.get("SWING_TOLERANCE_ATR", 0.2) or 0.2)
            near_high = price > 0 and high > 0 and atr > 0 and abs(price - high) <= tolerance
            near_low = price > 0 and low > 0 and atr > 0 and abs(price - low) <= tolerance
            if near_high or near_low:
                swing_status = "PASS"
                nearest_side = "HIGH" if near_high else "LOW"
            elif price <= 0 or high <= 0 or low <= 0 or atr <= 0:
                swing_status = "WAIT"
                reasons.append("NO_SWING_DATA")
            else:
                swing_status = "WAIT"
                reasons.append("SWING_NOT_NEAR")

        permission = not reasons
        return {
            "permission": permission,
            "status": "READY" if permission else "WAIT",
            "reason": "OK" if permission else "+".join(reasons),
            "signal": latest_signal,
            "signal_status": signal_status,
            "swing_status": swing_status,
            "nearest_swing": nearest_side,
            "tactic": str(cfg.get("TACTIC", "BASKET") or "BASKET").upper(),
            "swing_timeframe": cfg.get("SWING_TIMEFRAME", "---"),
        }

    def _prepare_hedge_context(self, symbol, context, settings):
        cfg_tf = str(settings.get("SWING_TIMEFRAME", "") or "").lower()
        if not cfg_tf or not self.data_engine:
            return context
        try:
            brain = self.data_engine._get_brain_settings(symbol)
            inds_config = brain.get("indicators", {})
            tsl_config = brain.get("TSL_CONFIG", {})
            num_bars = int(brain.get("NUM_H1_BARS", 100) or 100)
            df = self.data_engine._fetch_bars(symbol, cfg_tf, num_bars, inds_config, tsl_config)
            if df is None or df.empty:
                return context
            swing_lookback = int(inds_config.get("swing_point", {}).get("params", {}).get("lookback", 50))
            atr_period = int(inds_config.get("atr", {}).get("params", {}).get("period", 14))
            sh, sl = self.data_engine._calc_swings(df, lookback=swing_lookback)
            atr = self.data_engine._calc_atr(df, period=atr_period)
            context = dict(context)
            context["hedge_current_price"] = float(df["close"].iloc[-1])
            context["hedge_swing_high"] = float(sh)
            context["hedge_swing_low"] = float(sl)
            context["hedge_atr"] = float(atr)
            context["hedge_swing_timeframe"] = cfg_tf
        except Exception as e:
            self.log(f"Swing timeframe fetch fallback {symbol}: {e}", error=True)
        return context

    def clear_session_block(self, symbol=None):
        state = load_hedge_state()
        self._ensure_hedge_state(state)
        for sym, session in list(state.get("active_sessions", {}).items()):
            if symbol and sym != symbol:
                continue
            if isinstance(session, dict) and session.get("status") in {"STOP_NEW", "BLOCK"}:
                session["status"] = "PAIR_OPEN"
                session.pop("stop_reason", None)
                session.pop("last_block_reason", None)
                session["updated_at"] = time.time()
        if symbol:
            state.get("last_decision", {}).pop(symbol, None)
            state.setdefault("last_loss_times", {}).pop(symbol, None)
        else:
            state["last_decision"] = {}
            state["last_loss_times"] = {}
            state["global_cooldown_until"] = 0.0
            state["consecutive_losses"] = 0
        save_hedge_state(state)
        return "SUCCESS"

    def stop_session(self, symbol=None):
        state = load_hedge_state()
        self._ensure_hedge_state(state)
        changed = 0
        for sym, session in list(state.get("active_sessions", {}).items()):
            if symbol and sym != symbol:
                continue
            if isinstance(session, dict):
                session["status"] = "STOP_NEW"
                session["stop_reason"] = "USER_STOP_SESSION"
                session["updated_at"] = time.time()
                changed += 1
        save_hedge_state(state)
        return f"SUCCESS|{changed}"

    def start_manual_session(self, symbol, context=None):
        settings = load_hedge_settings()
        state = load_hedge_state()
        self._ensure_hedge_state(state)
        result = self._start_pair_session(symbol, context or {}, settings, state, source="MANUAL")
        save_hedge_state(state)
        return result

    def _start_pair_session(self, symbol, context, settings, state, source="MANUAL"):
        cfg = self.settings_for_symbol(symbol, settings)
        ok_daily, daily_reason = self._daily_safety(state, cfg)
        if not ok_daily:
            self._record_decision(state, symbol, None, "BLOCK", daily_reason)
            return f"HEDGE_BLOCK|{daily_reason}"
        global_until = float(state.get("global_cooldown_until", 0.0) or 0.0)
        if global_until > time.time():
            self._record_decision(state, symbol, None, "WAIT", "GLOBAL_LOSS_COOLDOWN")
            return "HEDGE_BLOCK|GLOBAL_LOSS_COOLDOWN"
        gate = self.evaluate_entry_gate(symbol, context or {}, settings)
        if not gate["permission"]:
            self._record_decision(state, symbol, None, "WAIT", gate["reason"], gate=gate)
            return f"HEDGE_BLOCK|{gate['reason']}"

        ok, reason = self._hard_safety(symbol, cfg)
        if not ok:
            self._record_decision(state, symbol, None, "BLOCK", reason, gate=gate)
            return f"HEDGE_BLOCK|{reason}"

        existing = self._hedge_positions(symbol)
        max_pairs = int(cfg.get("MAX_PAIRS_PER_SYMBOL", 1) or 1)
        if len(existing) >= max_pairs * 2:
            self._record_decision(state, symbol, None, "BLOCK", "MAX_PAIRS_PER_SYMBOL", gate=gate)
            return "HEDGE_BLOCK|MAX_PAIRS_PER_SYMBOL"

        cooldown = float(cfg.get("COOLDOWN_AFTER_CLOSE_SECONDS", 900) or 0)
        last_close = float(state.get("last_close_times", {}).get(symbol, 0.0) or 0.0)
        if cooldown > 0 and time.time() - last_close < cooldown:
            self._record_decision(state, symbol, None, "WAIT", "COOLDOWN_AFTER_CLOSE", gate=gate)
            return "HEDGE_BLOCK|COOLDOWN_AFTER_CLOSE"

        loss_cooldown = float(cfg.get("COOLDOWN_AFTER_LOSS_SECONDS", 0) or 0)
        last_loss = float(state.get("last_loss_times", {}).get(symbol, 0.0) or 0.0)
        if loss_cooldown > 0 and time.time() - last_loss < loss_cooldown:
            self._record_decision(state, symbol, None, "WAIT", "COOLDOWN_AFTER_LOSS", gate=gate)
            return "HEDGE_BLOCK|COOLDOWN_AFTER_LOSS"

        lot = float(cfg.get("FIXED_LOT", 0.1) or 0.1)
        session_id = f"HEDGE_{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        hedge_magic = get_magic_numbers().get("hedge_magic", 99888)
        buy_result = self.executor.place_hedge_leg(symbol, "BUY", lot, hedge_magic, session_id)
        if "SUCCESS" not in buy_result:
            self._record_decision(state, symbol, None, "BLOCK", buy_result, gate=gate)
            return buy_result
        buy_ticket = int(buy_result.split("|", 1)[1])
        sell_result = self.executor.place_hedge_leg(symbol, "SELL", lot, hedge_magic, session_id)
        if "SUCCESS" not in sell_result:
            buy_pos = self._position_by_ticket(buy_ticket)
            if buy_pos:
                self.executor.close_position(buy_pos, "PAIR_FAIL")
            self._record_decision(state, symbol, None, "BLOCK", "PAIR_OPEN_FAILED", gate=gate)
            return f"HEDGE_FAIL|PAIR_OPEN_FAILED|{sell_result}"
        sell_ticket = int(sell_result.split("|", 1)[1])

        session = {
            "session_id": session_id,
            "symbol": symbol,
            "source": source,
            "status": "PAIR_OPEN",
            "tactic": str(cfg.get("TACTIC", "BASKET") or "BASKET").upper(),
            "buy_ticket": buy_ticket,
            "sell_ticket": sell_ticket,
            "created_at": time.time(),
            "updated_at": time.time(),
            "entry_gate": gate,
            "mfe": 0.0,
            "mae": 0.0,
            "closed_leg_pnl": 0.0,
        }
        state.setdefault("active_sessions", {})[symbol] = session
        state["hedge_sessions_today"] = int(state.get("hedge_sessions_today", 0) or 0) + 1
        self._record_decision(state, symbol, session, "OPEN", "PAIR_OPENED", gate=gate)
        return f"SUCCESS|{session_id}"

    def scan(self, symbols=None, contexts=None):
        settings = load_hedge_settings()
        state = load_hedge_state()
        self._ensure_hedge_state(state)
        actions = []
        if settings.get("ENABLED", False):
            scan_symbols = list(symbols or settings.get("WATCHLIST") or [])
            if not scan_symbols:
                self._record_decision(state, "---", None, "WAIT", "WATCHLIST_EMPTY")
            for symbol in scan_symbols:
                if symbol in (state.get("active_sessions") or {}):
                    continue
                context = (contexts or {}).get(symbol, {}) if isinstance(contexts, dict) else {}
                result = self._start_pair_session(symbol, context, settings, state, source="AUTO")
                if result.startswith("SUCCESS"):
                    actions.append(f"HEDGE_OPEN|{symbol}|AUTO")
        for symbol, session in list(state.get("active_sessions", {}).items()):
            actions.extend(self._manage_session(symbol, session, self.settings_for_symbol(symbol, settings), state))
        self._sync_hedge_history(state)
        save_hedge_state(state)
        return {"status": "OK", "actions": actions}

    def _hard_safety(self, symbol, settings):
        if not self.connector or not getattr(self.connector, "_is_connected", False):
            return False, "NO_CONNECTION"
        is_open, reason = is_symbol_trade_window_open(symbol)
        if not is_open:
            return False, f"MARKET_CLOSED:{reason}"
        if settings.get("CHECK_PING", True):
            try:
                ping_ms = mt5.terminal_info().ping_last / 1000
            except Exception:
                ping_ms = 0
            if ping_ms > int(settings.get("MAX_PING_MS", 150) or 150):
                return False, f"PING:{ping_ms:.0f}"
        if settings.get("CHECK_SPREAD", True):
            tick = mt5.symbol_info_tick(symbol)
            info = mt5.symbol_info(symbol)
            if tick and info and getattr(info, "point", 0) > 0:
                spread_points = (tick.ask - tick.bid) / info.point
                if spread_points > int(settings.get("MAX_SPREAD_POINTS", 150) or 150):
                    return False, f"SPREAD:{spread_points:.0f}"
        return True, "OK"

    def _hedge_positions(self, symbol=None):
        magics = get_magic_numbers()
        positions = self.connector.get_all_open_positions() if self.connector else []
        return [p for p in positions if is_hedge_position(p, magics) and (symbol is None or getattr(p, "symbol", None) == symbol)]

    def _position_by_ticket(self, ticket):
        for pos in self._hedge_positions():
            try:
                if int(pos.ticket) == int(ticket):
                    return pos
            except Exception:
                pass
        return None

    def _pos_pnl(self, pos):
        return float(getattr(pos, "profit", 0.0) or 0.0) + float(getattr(pos, "swap", 0.0) or 0.0) + float(getattr(pos, "commission", 0.0) or 0.0)

    def _manage_session(self, symbol, session, settings, state):
        if session.get("status") == "STOP_NEW":
            return []
        positions = {int(p.ticket): p for p in self._hedge_positions(symbol)}
        session_positions = [positions[t] for t in (session.get("buy_ticket"), session.get("sell_ticket"), session.get("recovery_ticket")) if t in positions]
        if not session_positions:
            state.setdefault("last_close_times", {})[symbol] = time.time()
            state.get("active_sessions", {}).pop(symbol, None)
            self._record_decision(state, symbol, session, "CLOSE", "SESSION_DONE")
            return ["HEDGE_CLOSE|SESSION_DONE"]

        pnl = sum(self._pos_pnl(p) for p in session_positions) + float(session.get("closed_leg_pnl", 0.0) or 0.0)
        session["mfe"] = max(float(session.get("mfe", 0.0) or 0.0), pnl)
        session["mae"] = min(float(session.get("mae", 0.0) or 0.0), pnl)
        session["updated_at"] = time.time()

        age = time.time() - float(session.get("created_at", time.time()) or time.time())
        if float(settings.get("MAX_HOLD_SECONDS", 1800) or 0) > 0 and age >= float(settings.get("MAX_HOLD_SECONDS", 1800) or 0):
            return self._close_session_positions(symbol, session, session_positions, "MAX_HOLD", state)
        if age >= float(settings.get("NO_MOVE_TIMEOUT_SECONDS", 300) or 0) and session.get("mfe", 0.0) < float(settings.get("NO_MOVE_MIN_MFE_USD", 1.0) or 1.0):
            return self._close_session_positions(symbol, session, session_positions, "NO_MOVE_TIMEOUT", state)

        tactic = str(session.get("tactic", settings.get("TACTIC", "BASKET")) or "BASKET").upper()
        if tactic == "LEG_OUT":
            return self._manage_leg_out(symbol, session, positions, settings, state)

        if pnl >= abs(float(settings.get("PAIR_TP_USD", 5.0) or 5.0)):
            return self._close_session_positions(symbol, session, session_positions, "BASKET_TP", state)
        if pnl <= -abs(float(settings.get("PAIR_SL_USD", 10.0) or 10.0)):
            return self._close_session_positions(symbol, session, session_positions, "BASKET_SL", state)
        self._record_decision(state, symbol, session, "WAIT", "BASKET_HOLD", pnl=pnl)
        return []

    def _manage_leg_out(self, symbol, session, positions, settings, state):
        buy_pos = positions.get(int(session.get("buy_ticket", 0) or 0))
        sell_pos = positions.get(int(session.get("sell_ticket", 0) or 0))
        recovery_ticket = int(session.get("recovery_ticket", 0) or 0)
        recovery_pos = positions.get(recovery_ticket) if recovery_ticket else None

        if session.get("status") == "PAIR_OPEN" and buy_pos and sell_pos:
            buy_pnl = self._pos_pnl(buy_pos)
            sell_pnl = self._pos_pnl(sell_pos)
            loss_limit = -abs(float(settings.get("LOSING_LEG_SL_USD", 5.0) or 5.0))
            losing, recovery = (buy_pos, sell_pos) if buy_pnl <= loss_limit else (sell_pos, buy_pos) if sell_pnl <= loss_limit else (None, None)
            if losing and recovery:
                closed_pnl = self._pos_pnl(losing)
                result = self.executor.close_position(losing, "LEG_OUT")
                if "SUCCESS" in result:
                    session["status"] = "RECOVERY"
                    session["recovery_ticket"] = int(recovery.ticket)
                    session["closed_leg_pnl"] = float(session.get("closed_leg_pnl", 0.0) or 0.0) + closed_pnl
                    session["recovery_best_pnl"] = self._pos_pnl(recovery)
                    self._record_decision(state, symbol, session, "OPEN", "LEG_OUT_RECOVERY", pnl=closed_pnl)
                    return [result]

        if session.get("status") == "RECOVERY":
            recovery_pos = recovery_pos or (buy_pos if buy_pos else sell_pos)
            if not recovery_pos:
                state.get("active_sessions", {}).pop(symbol, None)
                return ["HEDGE_CLOSE|RECOVERY_DONE"]
            recovery_pnl = self._pos_pnl(recovery_pos)
            best = max(float(session.get("recovery_best_pnl", recovery_pnl) or recovery_pnl), recovery_pnl)
            session["recovery_best_pnl"] = best
            total = recovery_pnl + float(session.get("closed_leg_pnl", 0.0) or 0.0)
            if total >= float(settings.get("RECOVERY_TARGET_USD", 2.0) or 2.0):
                return self._close_session_positions(symbol, session, [recovery_pos], "RECOVERY_TARGET", state)
            giveback = float(settings.get("RECOVERY_GIVEBACK_USD", 2.0) or 2.0)
            if giveback > 0 and best - recovery_pnl >= giveback:
                return self._close_session_positions(symbol, session, [recovery_pos], "RECOVERY_GIVEBACK", state)
            self._record_decision(state, symbol, session, "WAIT", "RECOVERY_HOLD", pnl=total)
            return []

        self._record_decision(state, symbol, session, "WAIT", "LEG_OUT_HOLD")
        return []

    def _close_session_positions(self, symbol, session, positions, reason, state):
        actions = []
        total_pnl = sum(self._pos_pnl(p) for p in positions) + float(session.get("closed_leg_pnl", 0.0) or 0.0)
        for pos in positions:
            actions.append(self.executor.close_position(pos, reason))
        state.setdefault("last_close_times", {})[symbol] = time.time()
        if total_pnl < 0:
            state.setdefault("last_loss_times", {})[symbol] = time.time()
            state["consecutive_losses"] = int(state.get("consecutive_losses", 0) or 0) + 1
            max_losses = int(settings.get("MAX_CONSECUTIVE_LOSSES", 0) or 0)
            if max_losses > 0 and state["consecutive_losses"] >= max_losses:
                state["global_cooldown_until"] = time.time() + float(settings.get("GLOBAL_COOLDOWN_SECONDS", 3600) or 3600)
        else:
            state["consecutive_losses"] = 0
        session["status"] = "CLOSED"
        state.get("active_sessions", {}).pop(symbol, None)
        self._record_decision(state, symbol, session, "CLOSE", reason, pnl=total_pnl)
        return actions

    def _record_decision(self, state, symbol, session, status, reason, gate=None, **extra):
        decision = {
            "status": status,
            "reason": reason,
            "symbol": symbol,
            "tactic": (session or {}).get("tactic", "BASKET") if isinstance(session, dict) else "BASKET",
            "source": (session or {}).get("source", "MANUAL") if isinstance(session, dict) else "MANUAL",
            "time": time.time(),
        }
        if gate:
            decision["gate"] = gate
        decision.update(extra)
        state.setdefault("last_decision", {})[symbol] = decision
        log_key = f"{symbol}|{status}|{reason}|{decision.get('tactic')}|{round(float(extra.get('pnl', 0.0) or 0.0), 2)}"
        last_logs = state.setdefault("last_decision_log_keys", {})
        prev = self._decision_log_cache.get(symbol) or last_logs.get(symbol, {})
        now = time.time()
        repeat_cooldown = 60.0 if status in {"OPEN", "CLOSE"} else 300.0
        if prev.get("key") != log_key or now - float(prev.get("time", 0) or 0) >= repeat_cooldown or status in {"OPEN", "CLOSE"}:
            parts = [symbol, f"status={status}", f"reason={reason}", f"tactic={decision.get('tactic')}", f"source={decision.get('source')}"]
            if "pnl" in extra:
                parts.append(f"pnl={float(extra['pnl']):+.2f}")
            self.log("DECISION " + " ".join(parts))
            cache_item = {"key": log_key, "time": now}
            self._decision_log_cache[symbol] = cache_item
            last_logs[symbol] = cache_item

    def _sync_hedge_history(self, state):
        current_tickets = {int(p.ticket) for p in self._hedge_positions()}
        previous_tickets = {int(t) for t in state.get("hedge_active_tickets", []) if str(t).isdigit()}
        closed_tickets = previous_tickets - current_tickets
        for ticket in closed_tickets:
            try:
                deals = mt5.history_deals_get(position=ticket)
                if not deals:
                    continue
                deal_out = [d for d in deals if d.entry == mt5.DEAL_ENTRY_OUT]
                if not deal_out:
                    continue
                d_out = deal_out[0]
                deal_in = [d for d in deals if d.entry == mt5.DEAL_ENTRY_IN]
                d_in = deal_in[0] if deal_in else None
                real_pnl = d_out.profit + d_out.commission + d_out.swap
                pos_type = "BUY" if d_out.type == mt5.DEAL_TYPE_SELL else "SELL"
                open_time_str = datetime.fromtimestamp(d_in.time).strftime("%Y-%m-%d %H:%M:%S") if d_in else ""
                append_trade_log(
                    ticket,
                    d_out.symbol,
                    pos_type,
                    d_out.volume,
                    d_in.price if d_in else 0.0,
                    0.0,
                    0.0,
                    -(abs(d_out.commission) + abs(d_out.swap)),
                    real_pnl,
                    "HEDGE_Close",
                    market_mode="HEDGE",
                    trigger_signal=d_in.comment if d_in else "HEDGE",
                    session_id="HEDGE",
                    open_time_str=open_time_str,
                    mae_usd=min(real_pnl, 0.0),
                    mfe_usd=max(real_pnl, 0.0),
                )
                state["hedge_pnl_today"] = float(state.get("hedge_pnl_today", 0.0) or 0.0) + real_pnl
                if real_pnl < 0:
                    state["hedge_daily_loss_count"] = int(state.get("hedge_daily_loss_count", 0) or 0) + 1
                self.log(f"Closed {pos_type} {d_out.symbol} #{ticket} PnL={real_pnl:+.2f}")
            except Exception as e:
                self.log(f"History sync failed for #{ticket}: {e}", error=True)
        state["hedge_active_tickets"] = sorted(current_tickets)
