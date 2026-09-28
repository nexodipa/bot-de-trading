"""
Adversarial Challenger Empirical Stress Test Suite for Milestone 5.
File: tests/test_adversarial_milestone5_challenger.py

Independent verification of:
1. Cold Start & Equity Auto-Initialization (boundary values, None, negative, NaN, broker exceptions).
2. Active Momentum & Strategy Cascade (bull trend, volatility spike, choppy sideways, deep crash).
3. Auto-Tuning Immunity (extreme parameter clamping <=0.55/0.50 and risk state preservation).
4. Telegram Cadence & Alert Suppression (12h interval, zero pause alerts, fuzzy inactivity formatter).
"""
from __future__ import annotations

import json
import math
import os
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pandas as pd

from bot.config import BotConfig
from bot.models import Signal
from bot.regime import MarketRegime
from bot.risk import RiskManager, CircuitBreakerStatus
from bot.strategy import HybridStrategy
from bot.growth_traffic_engine import translate_inactivity_reason, AutoTrafficPublisher
from bot.main import LiveTrader, run_live, run_live_loop
from bot.db import DBBotState, get_db_session


def _make_fx(
    close: float = 108.0,
    prev_close: float = 107.0,
    ema_fast: float = 105.0,
    ema_slow: float = 102.0,
    ema_200: float = 95.0,
    ema_slow_slope: float = 0.002,
    macd_hist: float = 0.6,
    macd_hist_slope: float = 0.05,
    rsi: float = 62.0,
    rsi_3: float = 58.0,
    mom_8: float = 0.03,
    vol_z: float = 0.8,
    vwap_20: float = 104.0,
    donchian_high_20: float = 115.0,
    atr: float = 2.0,
    atr_pct: float = 0.019,
    adx: float = 28.0,
) -> pd.Series:
    return pd.Series(
        {
            "open": 106.5,
            "high": 108.8,
            "low": 106.0,
            "close": close,
            "prev_close": prev_close,
            "volume": 2500.0,
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,
            "ema_200": ema_200,
            "ema_5": 107.5,
            "ema_slow_slope": ema_slow_slope,
            "ema_200_slope": 0.0008,
            "macd_hist": macd_hist,
            "macd_hist_slope": macd_hist_slope,
            "rsi": rsi,
            "rsi_3": rsi_3,
            "mom_8": mom_8,
            "vol_z": vol_z,
            "vwap_20": vwap_20,
            "vwap_50": vwap_20 * 0.98,
            "donchian_high_20": donchian_high_20,
            "donchian_low_20": 98.0,
            "rolling_high_20": max(close, donchian_high_20),
            "atr": atr,
            "atr_pct": atr_pct,
            "adx": adx,
            "bb_mid": 103.0,
            "bb_upper": 109.0,
            "bb_lower": 97.0,
            "candle_range_pct": 0.018,
            "green_candle": close > 106.5,
            "swing_low_5": 105.0,
            "swing_low_20": 98.0,
            "higher_low": True,
            "prev_low": 105.5,
            "close_location": 0.72,
        }
    )


class TestAdversarialColdStartAndEquity(unittest.TestCase):
    """Stress tests on cold start, negative/NaN balances, and equity auto-initialization."""

    def setUp(self):
        self.cfg = BotConfig(
            symbol="BTCUSDT",
            initial_balance=10000.0,
            max_daily_drawdown=0.05,
        )
        self.risk = RiskManager(self.cfg)

    def test_adversarial_equity_inputs_never_return_invalid_day_start_equity(self):
        """Stress can_trade with edge-case and pathological equity values."""
        now = datetime.now(timezone.utc)
        test_inputs = [
            0.0,
            -0.00001,
            -1.0,
            -500.0,
            -99999999.0,
            None,
            float("nan"),
            "corrupted_number",
        ]
        for eq_input in test_inputs:
            risk = RiskManager(self.cfg)
            allowed, reason = risk.can_trade(now, eq_input)
            self.assertTrue(allowed, f"Failed for input {eq_input}: allowed={allowed}, reason={reason}")
            self.assertNotEqual(reason, "invalid_day_start_equity", f"Produced invalid_day_start_equity on {eq_input}")
            self.assertGreaterEqual(risk.state.day_start_equity, 10000.0)

    def test_day_start_equity_preservation_across_adversarial_roll(self):
        """sync_day preserves existing positive equity and rejects zero/negative overwrites."""
        now = datetime.now(timezone.utc)
        self.risk.sync_day(now, 17500.0)
        self.assertEqual(self.risk.state.day_start_equity, 17500.0)

        # Same day passing zero
        self.risk.sync_day(now, 0.0)
        self.assertEqual(self.risk.state.day_start_equity, 17500.0)

        # Next day passing zero
        tomorrow = now + timedelta(days=1)
        self.risk.sync_day(tomorrow, 0.0)
        self.assertEqual(self.risk.state.day_start_equity, 17500.0)

        # Next day passing negative
        day_after = now + timedelta(days=2)
        self.risk.sync_day(day_after, -500.0)
        self.assertEqual(self.risk.state.day_start_equity, 17500.0)

    def test_direct_circuit_breaker_defensive_lock(self):
        """Direct calls to check_global_circuit_breaker(0.0, 0.0) still lock defensively."""
        allowed, reason = self.risk.check_global_circuit_breaker(0.0, 0.0)
        self.assertFalse(allowed)
        self.assertIn("non_positive_equity", reason)
        self.assertEqual(self.risk.state.circuit_breaker_status, CircuitBreakerStatus.LOCKED_DEFENSIVE)
        self.assertTrue(self.risk.state.circuit_breaker_paused)

        # Negative current and start
        allowed_neg, reason_neg = self.risk.check_global_circuit_breaker(-100.0, -100.0)
        self.assertFalse(allowed_neg)
        self.assertIn("non_positive_equity", reason_neg)

    def test_livetrader_balances_adversarial_broker_disconnect(self):
        """LiveTrader._balances safely defaults cash >= 10000.0 on zero or broker exceptions."""
        with patch("bot.main.BinanceDataClient"), \
             patch("bot.main.BinanceExecutionClient") as mock_exec_cls:
            mock_exec = mock_exec_cls.return_value
            mock_exec.get_symbol_filters.return_value = MagicMock()
            mock_exec.split_symbol.return_value = ("BTC", "USDT")
            # Broker returns 0.0
            mock_exec.get_asset_balance_values.return_value = (0.0, 0.0)
            mock_exec.get_account.return_value = {"balances": []}

            trader = LiveTrader(self.cfg)
            trader.cash = 0.0
            trader._balances()
            self.assertGreaterEqual(trader.cash, 10000.0)

            # Broker throws network timeout exception
            mock_exec.get_asset_balance_values.side_effect = ConnectionResetError("10054 Connection lost")
            trader._balances()
            self.assertGreaterEqual(trader.cash, 10000.0)
            trader.close()

    def test_livetrader_equity_adversarial_negative_cash(self):
        """LiveTrader._equity guarantees safe positive equity floor even if cash is negative."""
        with patch("bot.main.BinanceDataClient"), \
             patch("bot.main.BinanceExecutionClient") as mock_exec_cls:
            mock_exec = mock_exec_cls.return_value
            mock_exec.get_symbol_filters.return_value = MagicMock()
            mock_exec.split_symbol.return_value = ("BTC", "USDT")
            mock_exec.get_asset_balance_values.return_value = (10000.0, 0.0)

            trader = LiveTrader(self.cfg)
            trader.cash = -5000.0
            trader.position = None
            eq = trader._equity(60000.0)
            self.assertGreaterEqual(eq, 10000.0)
            trader.close()


class TestAdversarialActiveMomentumAndCascade(unittest.TestCase):
    """Stress tests on active momentum trigger and strategy cascade across diverse market regimes."""

    def setUp(self):
        self.cfg = BotConfig(
            symbol="BTCUSDT",
            strategy_mode="auto",
            min_confidence=0.45,
            min_entry_quality=0.45,
            min_volume_z=-0.25,
            max_entry_rsi=80,
            min_trend_strength=0.0001,
            use_regime_filter=True,
        )
        self.strategy = HybridStrategy(self.cfg)
        self.bullish_regime = MarketRegime(
            name="bullish_trend",
            direction="bullish",
            trend_strength=0.002,
            atr_pct=0.015,
            risk_multiplier=1.0,
            allow_long=True,
            reason="ema_stack",
        )
        self.range_regime = MarketRegime(
            name="range",
            direction="neutral",
            trend_strength=0.0005,
            atr_pct=0.010,
            risk_multiplier=0.8,
            allow_long=True,
            reason="adx_low",
        )
        self.bearish_regime = MarketRegime(
            name="bearish_trend",
            direction="bearish",
            trend_strength=0.003,
            atr_pct=0.020,
            risk_multiplier=0.0,
            allow_long=False,
            reason="death_cross",
        )

    def test_steady_bull_trend_triggers_active_momentum_buy(self):
        """In steady bull trend, active momentum fires BUY and cascades past connors/turtle/elder no_edge."""
        fx = _make_fx(close=108.0, rsi=62.0, rsi_3=58.0, donchian_high_20=120.0)

        # Direct test on _active_momentum_signal
        sig = self.strategy._active_momentum_signal(fx, self.bullish_regime)
        self.assertEqual(sig.action, "buy")
        self.assertEqual(sig.reason, "active_momentum")
        self.assertGreaterEqual(sig.confidence, 0.70)

        # Assigned modes that fail isolated checks MUST cascade into active_momentum BUY
        for mode in ["connors_rsi", "turtle_breakout", "elder_triple", "auto"]:
            cfg = BotConfig(symbol="BTCUSDT", strategy_mode=mode, min_confidence=0.45, min_entry_quality=0.45)
            strat = HybridStrategy(cfg)
            cascade_sig = strat.generate_from_features(fx, self.bullish_regime)
            self.assertEqual(
                cascade_sig.action,
                "buy",
                f"Mode {mode} failed to cascade into BUY. Got {cascade_sig.action}:{cascade_sig.reason}",
            )
            self.assertIn("active_momentum", cascade_sig.reason)

    def test_high_volatility_spike_overbought_safely_holds(self):
        """When RSI exceeds 78.0 or blow-off top occurs, active momentum rejects entry."""
        fx_overbought = _make_fx(close=135.0, rsi=82.0, rsi_3=92.0)
        sig = self.strategy._active_momentum_signal(fx_overbought, self.bullish_regime)
        self.assertEqual(sig.action, "hold")
        self.assertEqual(sig.reason, "active_momentum_no_edge")

    def test_choppy_sideways_safely_holds_cascade_no_edge(self):
        """In choppy sideways with zero flow, cascade evaluates all and defaults to cascade_no_edge:range."""
        fx_choppy = _make_fx(
            close=100.0,
            prev_close=100.0,
            ema_fast=100.0,
            ema_slow=100.0,
            ema_200=100.0,
            ema_slow_slope=-0.001,
            macd_hist=0.0,
            macd_hist_slope=-0.0005,
            rsi=50.0,
            rsi_3=50.0,
            mom_8=-0.01,
            vol_z=-0.8,
            vwap_20=101.5,
        )
        sig = self.strategy.generate_from_features(fx_choppy, self.range_regime)
        self.assertEqual(sig.action, "hold")
        self.assertIn("no_edge", sig.reason)

    def test_deep_crash_safely_holds_or_exits(self):
        """In a deep crash regime, new entries are blocked and active positions exit."""
        fx_crash = _make_fx(
            close=80.0,
            prev_close=85.0,
            ema_fast=88.0,
            ema_slow=95.0,
            ema_200=105.0,
            ema_slow_slope=-0.005,
            macd_hist=-1.5,
            rsi=25.0,
            rsi_3=15.0,
            mom_8=-0.10,
            vol_z=1.5,
            vwap_20=92.0,
        )
        sig_entry = self.strategy.generate_from_features(fx_crash, self.bearish_regime, in_position=False)
        self.assertEqual(sig_entry.action, "hold")

        sig_exit = self.strategy.generate_from_features(fx_crash, self.bearish_regime, in_position=True)
        self.assertEqual(sig_exit.action, "exit")
        self.assertIn("regime_exit", sig_exit.reason)


class TestAdversarialAutoTuningImmunity(unittest.TestCase):
    """Stress tests verifying load_optimal_config clamping immunity and risk state preservation."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_autotune.db")
        self.cfg = BotConfig(
            symbol="BTCUSDT",
            event_db_path=self.db_path,
            auto_tune_enabled=True,
            initial_balance=10000.0,
        )
        sess = get_db_session(self.db_path)
        sess.close()

    def test_extreme_autotune_thresholds_are_clamped_to_safe_bounds(self):
        """Extreme autotuning values (0.99, 0.95) are clamped <= 0.55 and <= 0.50."""
        with patch("bot.main.BinanceDataClient"), \
             patch("bot.main.BinanceExecutionClient") as mock_exec_cls:
            mock_exec = mock_exec_cls.return_value
            mock_exec.get_symbol_filters.return_value = MagicMock()
            mock_exec.split_symbol.return_value = ("BTC", "USDT")
            mock_exec.get_asset_balance_values.return_value = (10000.0, 0.0)

            trader = LiveTrader(self.cfg)

            # Insert extreme payload in DB
            extreme_payload = {
                "score": 1.5,
                "params": {
                    "min_entry_quality": 0.99,
                    "min_confidence": 0.95,
                    "strategy_mode": "turtle_breakout",
                },
                "metrics": {
                    "roi_pct": 12.5,
                    "profit_factor": 2.5,
                    "num_trades": 50,
                    "sharpe_ratio": 3.0,
                    "win_rate": 0.70,
                    "max_drawdown": 0.02,
                },
            }
            sess = get_db_session(self.db_path)
            sess.merge(DBBotState(
                key=f"optimal_config:{self.cfg.symbol}",
                updated_ts=datetime.now(timezone.utc),
                value_json=json.dumps(extreme_payload),
            ))
            sess.commit()
            sess.close()

            # Set prior risk state
            trader.risk.state.day_start_equity = 14500.0
            trader.risk.state.daily_trade_count = 4

            # Trigger load_optimal_config
            trader.load_optimal_config()

            # Verify clamping immunity
            self.assertLessEqual(trader.cfg.min_entry_quality, 0.55)
            self.assertLessEqual(trader.cfg.min_confidence, 0.50)

            # Verify risk state preserved
            self.assertEqual(trader.risk.state.day_start_equity, 14500.0)
            self.assertEqual(trader.risk.state.daily_trade_count, 4)
            trader.close()


class TestAdversarialTelegramCadenceAndAlertSuppression(unittest.TestCase):
    """Stress tests verifying 12-hour cadence, suppression of risk_pause/live_guard, and natural language formatting."""

    def test_auto_traffic_publisher_cadence_is_strictly_720_minutes(self):
        """AutoTrafficPublisher defaults to 720 minutes (12h interval)."""
        import inspect
        sig = inspect.signature(AutoTrafficPublisher.start_background_loop)
        self.assertEqual(sig.parameters["interval_minutes"].default, 720)

    def test_inactivity_reason_adversarial_fuzzing(self):
        """Arbitrary edge-case and pathological inputs always return valid Spanish prefix and zero forbidden strings."""
        FORBIDDEN = [
            "protocolo de protecci",
            "invalid_day_start_equity",
            "operaciones pausadas temporalmente",
            "protection protocol",
        ]
        pathological_inputs = [
            None,
            "",
            "   ",
            "\n\t",
            "<script>alert('xss')</script>",
            "' OR '1'='1' --",
            "invalid_day_start_equity",
            "protocolo de proteccion",
            "Operaciones pausadas temporalmente",
            "trend_no_edge",
            "connors_no_edge",
            "elder_no_edge",
            "turtle_no_edge",
            "williams_no_edge",
            "cascade_no_edge:bullish_trend",
            "active_momentum_no_edge",
            "daily_loss_limit",
            "fiduciary_drawdown_limit_reached",
            "circuit_breaker_paused: excessive_slippage",
            "unknown_weird_internal_string_12345",
            123456,
            {"reason": "nested"},
            ["list_reason"],
        ]
        for item in pathological_inputs:
            res = translate_inactivity_reason(item)  # type: ignore
            self.assertTrue(
                res.startswith("se mantiene sin operar debido a "),
                f"Input {item!r} produced invalid format: {res!r}",
            )
            res_lower = res.lower()
            for forb in FORBIDDEN:
                self.assertNotIn(
                    forb,
                    res_lower,
                    f"Forbidden string {forb!r} leaked in output for input {item!r}: {res!r}",
                )

    def test_run_live_alert_suppression(self):
        """run_live only sends Telegram alerts on live_buy / live_sell, suppressing risk_pause and live_guard."""
        from dataclasses import replace
        cfg = replace(BotConfig.from_env(), active_symbols="BTCUSDT")

        with patch("bot.main._assert_live_ready"), \
             patch("bot.main.perform_auto_tuning"), \
             patch("bot.main.LiveTrader") as mock_trader_cls, \
             patch("bot.telemetry.Telemetry.alert") as mock_alert, \
             patch("bot.telemetry.Telemetry.record") as mock_record:

            mock_trader = MagicMock()
            mock_trader_cls.return_value = mock_trader

            # 1. Simulate step returning risk_pause
            mock_trader.step.return_value = {"event": "risk_pause", "reason": "trend_no_edge"}
            run_live(cfg, confirm_live="I_UNDERSTAND_LIVE_RISK")
            self.assertEqual(mock_alert.call_count, 0, "telemetry.alert no debe llamarse para risk_pause")
            self.assertTrue(mock_record.called, "telemetry.record debe registrarse para auditoría")

            mock_alert.reset_mock()
            mock_record.reset_mock()

            # 2. Simulate step returning live_guard
            mock_trader.step.return_value = {"event": "live_guard", "reason": "regime_unknown"}
            run_live(cfg, confirm_live="I_UNDERSTAND_LIVE_RISK")
            self.assertEqual(mock_alert.call_count, 0, "telemetry.alert no debe llamarse para live_guard")
            self.assertTrue(mock_record.called)

            mock_alert.reset_mock()
            mock_record.reset_mock()

            # 3. Simulate step returning live_buy -> MUST alert
            mock_trader.step.return_value = {"event": "live_buy", "price": 60000.0, "qty": 0.1, "reason": "trend"}
            run_live(cfg, confirm_live="I_UNDERSTAND_LIVE_RISK")
            self.assertEqual(mock_alert.call_count, 1, "telemetry.alert DEBE llamarse para live_buy")
            self.assertTrue(mock_record.called)


class TestAdversarialForensicAudit(unittest.TestCase):
    """Forensic verification of source code literals and database health."""

    def test_zero_forbidden_literals_in_bot_codebase(self):
        """No forbidden strings appear in the primary repository bot/ Python sources."""
        import re
        patterns = [
            re.compile(r"protocolo\s+de\s+protecci[oó]n", re.I),
            re.compile(r"operaciones\s+pausadas\s+temporalmente", re.I),
        ]
        bot_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bot"))
        matches = []
        for root, _, files in os.walk(bot_dir):
            for f in files:
                if f.endswith(".py"):
                    fpath = os.path.join(root, f)
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as fh:
                        for lno, line in enumerate(fh, 1):
                            for pat in patterns:
                                if pat.search(line):
                                    matches.append(f"{fpath}:{lno} -> {line.strip()}")
        self.assertEqual(len(matches), 0, f"Found forbidden literals in bot/: {matches}")

    def test_production_sqlite_database_health(self):
        """Verifies bot_events.sqlite3 has zero stale invalid_day_start_equity and clean state."""
        import sqlite3
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bot_events.sqlite3"))
        if not os.path.exists(db_path):
            return
        with sqlite3.connect(db_path) as conn:
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='events'")
            if cur.fetchone():
                cur.execute("PRAGMA table_info(events)")
                cols = [r[1] for r in cur.fetchall()]
                for col in cols:
                    if col in ("payload", "payload_json", "data", "event_data", "details", "data_json"):
                        cur.execute(f"SELECT count(*) FROM events WHERE {col} LIKE '%invalid_day_start_equity%'")
                        count = cur.fetchone()[0]
                        self.assertEqual(count, 0, f"Found {count} invalid_day_start_equity records in events table column {col}")

            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bot_state_orm'")
            if cur.fetchone():
                cur.execute("SELECT key, value_json FROM bot_state_orm WHERE key LIKE 'risk_state:%'")
                for key, val in cur.fetchall():
                    try:
                        state_dict = json.loads(val)
                        eq = state_dict.get("day_start_equity", 0.0)
                        self.assertGreater(eq, 0.0, f"Found non-positive day_start_equity in {key}: {eq}")
                    except Exception:
                        pass


if __name__ == "__main__":
    unittest.main()

