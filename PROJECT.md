# Project: Quantitative Execution Force and Telegram Redesign

## Architecture
This project enhances the quantitative trading engines across two synchronized repositories:
1. **Primary (`bot de trading`)**: 24/7 Binance spot trading engine with hybrid crypto/stock evaluation.
2. **Secondary (`bot_ibkr_trading`)**: Interactive Brokers (IBKR) & yfinance equity execution engine (#MSFT, #AAPL, #NVDA, #TSLA, #META).

### System Data & Control Flow
- **Execution & Risk Layer**:
  - `RiskManager.can_trade()` and `RiskManager.sync_day()` enforce capital preservation.
  - Equity resolution now auto-initializes `day_start_equity` to safe fallback equity (`max(equity, cash, initial_balance, 10000.0)`) whenever equity is `<= 0.0` or unavailable during broker startup/standby, permanently eradicating `invalid_day_start_equity`.
  - `load_optimal_config()` preserves existing `RiskManager` state instead of recreating it every step.
- **Strategy & Signal Layer**:
  - `HybridStrategy.generate()` evaluates indicators and market regime.
  - Cascading Multi-Strategy Fallback: When the primary strategy returns `*_no_edge`, the engine cascades through alternative strategies and evaluates an **Active Momentum / Trend Continuation** trigger (`_active_momentum_signal`), entering on positive volume flow and trend momentum without freezing in `hold`.
  - Auto-Tuning Immunity: `_build_autotune_grid()` and `load_optimal_config()` clamp thresholds (`min_entry_quality <= 0.55`, `min_confidence <= 0.50`) preventing auto-tuning from locking assets in passive modes.
- **Telemetry & Communications Layer**:
  - `AutoTrafficPublisher`: Scheduled cadence set to 720 minutes (12 hours / 2 times per day) emitting consolidated executive portfolio & market digests.
  - Alert Dispatchers: Real-time Telegram alerts restricted strictly to actual order executions (`live_buy`, `live_sell`).
  - Human Natural Language Formatter: Elimination of cryptic technical phrases (*"protocolo de protección"*, *"invalid_day_start_equity"*, *"Operaciones pausadas temporalmente"*). Inactivity is expressed purely in institutional Spanish market terms (*«se mantiene sin operar debido a [factor de mercado]»*).

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Equity Auto-Init & Elimination of `invalid_day_start_equity` | Auto-initialize `day_start_equity` with safe fallback in `bot/risk.py` and `bot/main.py` in both repos; preserve risk state in `load_optimal_config` | M1 | Survey (E1, E2, E3) |
| 2 | Active Momentum / Trend Continuation Trigger | Add `_active_momentum_signal` in `bot/strategy.py` evaluating positive trend continuation, RSI 46-78, volume flow | M2 | Survey (E2) |
| 3 | Cascading Multi-Strategy Fallback Engine | Evaluate alternative strategies when assigned strategy returns `*_no_edge` instead of locking into `hold` | M2 | Survey (E2) |
| 4 | Auto-Tuning Safe Immunity & Threshold Clamping | Clamp `min_entry_quality` (<=0.55) and `min_confidence` (<=0.50) in `_build_autotune_grid` and `load_optimal_config` | M2 | Survey (E2) |
| 5 | Strict 12-Hour Executive Telegram Digests | Configure `AutoTrafficPublisher` for 720 min (12h) interval with consolidated executive digest | M3 | Survey (E3) |
| 6 | Real Executions Only in Telegram Alert Dispatch | Restrict real-time Telegram alerts to `live_buy` and `live_sell`, completely suppressing individual `risk_pause` / `live_guard` alerts | M3 | Survey (E3) |
| 7 | Human Natural Language Inactivity Formatter | Eradicate cryptic pause jargon; translate no-trade factors into professional Spanish market explanations | M3 | Survey (E3) |
| 8 | Multi-Repo Stock Synchronization (#MSFT) | Ensure `bot_ibkr_trading` runs clean without `#MSFT` pause alerts under broker standby or zero balance | M4 | Survey (E1, E3) |
| 9 | 100% Comprehensive Test Suite & Zero Regressions | Unit, integration, and E2E verification across both repos with >=304 tests in primary and >=89 tests in secondary | M5 | Survey (E1, E2, E3) |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Equity Auto-Init & Risk Unblock | `bot/risk.py`, `bot/main.py` in `bot de trading` and `bot_ibkr_trading` | none | DONE (worker_m1, approved by reviewer_m1_1 and reviewer_m1_2) |
| M2 | Proactive Multi-Strategy & Active Momentum & Auto-Tuning Immunity | `bot/strategy.py`, `bot/main.py`, `.env` in both repos | M1 | DONE (worker_m2, approved by reviewer_m2_1 and reviewer_m2_2) |
| M3 | Telegram Redesign & Human Inactivity Engine | `bot/growth_traffic_engine.py`, `bot/telemetry.py`, `bot/main.py` in both repos | M1 | DONE (worker_m3, approved by reviewer_m3_1 and reviewer_m3_2) |
| M4 | IBKR Stock Synchronization & #MSFT Verification | Full verification and background event cleanup in `bot_ibkr_trading` | M1, M2, M3 | DONE (worker_m4_gen2) |
| M5 | Test Suite Execution & Final Forensic Verification | Full test suite execution, adversarial challenge, and forensic audit across both repos | M1, M2, M3, M4 | DONE (approved by challenger_final, audited CLEAN by auditor_final) |

## Interface Contracts
### `bot/risk.py` ↔ `bot/main.py` (`RiskManager`)
- Method: `can_trade(now: datetime, equity: float) -> tuple[bool, str]`
  - Contract: When `equity <= 0.0` or unavailable, auto-initialize `self.state.day_start_equity` to `max(equity, fallback_equity, 10000.0)`. Never return `(False, "invalid_day_start_equity")`. Always allow trade evaluation if no genuine drawdown limit breached.
- Method: `sync_day(now: datetime, equity: float) -> None`
  - Contract: Preserve previous day start equity or resolve positive safe floor if incoming `equity <= 0.0`.

### `bot/strategy.py` ↔ `bot/main.py` (`HybridStrategy`)
- Method: `generate_from_features(fx: dict, regime: MarketRegime) -> Signal`
  - Contract: When assigned mode returns `*_no_edge`, invoke cascading evaluation over available strategies + `_active_momentum_signal(fx, regime)`. Only return `hold` if all strategies reject entry.

### `bot/main.py` ↔ Telegram Telemetry
- Real-time alert filter: `if event_name in {"live_buy", "live_sell", "ibkr_buy", "ibkr_sell"}: telemetry.alert(...)`
- Formatting function: `_format_live_alert(symbol: str, event: dict) -> str`
  - Contract: Zero occurrences of `"protocolo de protección"`, `"invalid_day_start_equity"`, `"Operaciones pausadas temporalmente"`. Inactivity reasons formatted via `translate_inactivity_reason(reason)`.

## Code Layout
- `C:\Users\USUARIO\bot de trading`:
  - `bot/risk.py`: Risk management, equity tracking, circuit breaker.
  - `bot/strategy.py`: Technical indicators, market regimes, entry signals, active momentum.
  - `bot/main.py`: LiveTrader, auto-tuning grid, telemetry dispatch, alert formatters.
  - `bot/growth_traffic_engine.py`: AutoTrafficPublisher (12h digest loop).
  - `bot/telemetry.py`: TelegramNotifier, HTML sanitization.
  - `tests/`: Primary unit and integration test suite.
- `C:\Users\USUARIO\bot_ibkr_trading`:
  - Symmetrical files for IBKR equities execution: `bot/risk.py`, `bot/strategy.py`, `bot/main.py`, `bot/growth_traffic_engine.py`, `bot/telemetry.py`, `tests/`.
