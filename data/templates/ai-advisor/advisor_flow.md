# RAT6 AI Advisor Flow

This document is the business-flow map for the RAT6 advisor package. It helps an LLM understand the bot without receiving the full source code.

## Advisor Mission
Review RAT6 as a trader/risk-manager assistant. Diagnose performance, risk, module behavior, missed profit, bad exits, repeated blocks, config drift, and suspicious settings. Do not propose direct automatic order placement, do not claim web research, and do not ask the bot to edit config automatically.

## Package Reading Order
1. Read advisor_flow.md first.
2. Read user_context.md for the operator's current question and risk preference.
3. Read technical_settings.json for current config and runtime snapshots.
4. Read advisor_export.xlsx for trade evidence, summaries, events, and config changes.
5. If included, read advisor_response.md only as prior advice; verify it against current data.

## Package Files
- advisor_prompt.md: Opening instructions sent as API instructions or pasted into web chat.
- advisor_flow.md: Business flow and glossary.
- user_context.md: Human notes from the operator.
- technical_settings.json: Auto-generated config/state snapshot. Do not edit by hand.
- advisor_export.xlsx: Auto-generated trade/event/config workbook. Do not edit by hand.
- advisor_response.md: Latest saved LLM response.

## Config Layers
- settings.config_py: Static/default values imported from config.py.
- settings.active_global: Current global brain settings loaded from brain_settings.json.
- settings.active_by_symbol: Effective merged settings for each active symbol.
- settings.raw_sources: Raw snapshots of JSON/state files such as brain_settings.json, symbol_overrides.json, tsl_settings.json, presets_config.json, grid_settings.json, hedge_settings.json, bot_state.json, grid_state.json, hedge_state.json, live_signals.json, and system_meta.json.

Conflict rule: for symbol-specific review prefer active_by_symbol; for global review prefer active_global; for module-local review inspect raw source files; use config_py only as default/background.

## Advisor Workbook Sheets
- closed_trades: Trade result evidence including close reason, trigger, tactic, MAE/MFE, source type, module tags, and config snapshot id.
- open_trades: Current open trade evidence.
- config_snapshots: Stored config snapshots by id.
- config_changes: Diffs between snapshots.
- events: Advisor/system/module events.
- summary_daily, summary_symbol, summary_timeframe, summary_signal_group, summary_close_reason, summary_module: Aggregates for diagnosis.
- trade_config_map: Ticket-to-config-snapshot mapping.

## Core Trading Modes
- Manual: Operator-triggered orders using manual magic/comment classification.
- Bot: Signal-driven automatic order flow using safeguards, Entry/Exit, lot, SL/TP, TSL, DCA/PCA, REV_C.
- GRID: Isolated grid strategy with its own settings/state, magic, boundaries, levels, spacing, and safeguards.
- HEDGE: Isolated dual-leg hedge strategy with paired BUY/SELL entry, survivor protection, and post-leg TSL.

## Timeframe Groups
- G0: Macro/base timeframe.
- G1: Trend/context timeframe.
- G2: Execution/swing timeframe, often used for SL/TP references.
- G3: Fast confirmation timeframe.

## High-Level Bot Order Flow
1. Market data and indicators produce symbol context.
2. Signal engine evaluates configured groups and produces BUY/SELL/NONE.
3. Router decides whether entry, DCA, PCA, REV_C, GRID, HEDGE, or manual action should be considered.
4. Safeguards/checklists can block entry before lot/SL/TP are finalized.
5. Entry/Exit may run as preview-only or real entry gate.
6. SL, TP, lot, tactic labels, parent/child relation, session id, and comments are resolved.
7. MT5 order is sent and trade-open metadata/config snapshot is recorded.
8. Runtime managers apply TSL, BE, BE_CASH, REV_C, DCA/PCA, GRID basket logic, or HEDGE survivor logic.
9. Closed trades are exported into advisor_export.xlsx.

## Safeguards And Gates
Common blocks include market hours, re-entry locks, max daily loss, max open positions, max trades/day, max losing streak, ping, spread, cooldown, Entry/Exit WAIT/BLOCK, missing swing/ATR data, SL too tight, and strict minimum lot rejection.

Repeated SAFEGUARD_FAIL can mean risk gates are working. If good trades are missed, compare block reason frequency, market mode, spread/ping, cooldown, and Entry/Exit WAIT.

## Entry/Exit
Entry/Exit is a tactic layer. If preview-only, WAIT/BLOCK is not a real order block. If enabled and not preview-only, WAIT/BLOCK can prevent entry. Compare entry_exit_tactic with close reason, MAE/MFE, and signal group.

## SL, TP, Lot, And Risk
SL/TP can come from manual fields, swing-based logic, RR/percent/cash logic, HEDGE rules, or GRID TP-only behavior. Lot can be fixed, account-risk based, or module-specific. Compare lot size with symbol volatility, SL distance, account risk percent, max lot cap, DCA/PCA exposure, GRID total lot, and HEDGE max pairs.

## Runtime Modules
- TSL: General trailing stop layer.
- BE: Break-even stop behavior.
- BE_CASH: Cash/profit lock behavior.
- STEP_R: R-multiple step trailing.
- SWING: Swing-point trailing or SL/TP reference.
- PSAR_TRAIL: Parabolic SAR trailing.
- REV_C: Reverse/recovery close logic.
- DCA: Adds/averages into adverse basket by rule.
- PCA: Adds into winning/confirmed basket by rule.
- A.CUT or ANTI_CASH: Giveback/cash protection.
- GRID: Grid module.
- HEDGE: Hedge module.

## GRID Rules
GRID uses grid_magic, [GRID] comments, grid_state.json, and grid_settings.json. It does not write BOT/manual runtime counters. Boundaries use manual upper/lower first, otherwise swing high/low. Spacing can be ATR_DYNAMIC, ARITHMETIC, or GEOMETRIC. GRID V1 opens market orders with TP only; per-order SL is not part of V1.

GRID safeguards include MAX_GRID_ORDERS, MAX_TOTAL_LOT, MAX_BASKET_DRAWDOWN, GRID_MAX_DAILY_LOSS, GRID_MAX_TRADES_PER_DAY, BASKET_TP_USD, BASKET_SL_USD, CHECK_PING, and CHECK_SPREAD.

## HEDGE Rules
HEDGE owns hedge_state.json and hedge_settings.json. If signal/EntryExit filters are enabled, they must pass. HEDGE opens BUY and SELL together with same lot. While both legs are open, HEDGE does not run TSL on individual legs. After one leg closes, SURVIVOR_PROTECT runs before TSL on the remaining leg.

## MAE/MFE And Close Reasons
- MAE: Maximum adverse excursion in USD.
- MFE: Maximum favorable excursion in USD.
- High MFE with low final profit suggests exit/trailing/giveback issue.
- High MAE before profit suggests entry timing, SL distance, or DCA/PCA stress.
- Many SL closes after high MFE suggest trailing/BE/giveback issues.
- Many basket closes require GRID/HEDGE/DCA/PCA basket analysis.

## Recommended Answer Format
1. Executive summary.
2. Key evidence from sheets/fields.
3. Diagnosis by source type: BOT, MANUAL, GRID, HEDGE.
4. Risk issues.
5. Module review.
6. Suggested manual review actions, not automatic edits.
7. Uncertainty and missing evidence.
