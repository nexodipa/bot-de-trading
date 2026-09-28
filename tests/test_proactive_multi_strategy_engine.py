"""
Unit tests for Milestone 2: Proactive Multi-Strategy Entry Engine, Active Momentum & Auto-Tuning Immunity.
File: tests/test_proactive_multi_strategy_engine.py
"""
from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch
import pandas as pd

from bot.config import BotConfig
from bot.models import Signal
from bot.regime import MarketRegime
from bot.strategy import HybridStrategy
from bot.main import LiveTrader, _build_autotune_grid, _autotune_candidate_is_acceptable
from bot.db import DBBotState


def _build_test_features(
    close: float = 105.0,
    prev_close: float = 104.0,
    ema_fast: float = 102.0,
    ema_slow: float = 100.0,
    ema_200: float = 95.0,
    ema_slow_slope: float = 0.001,
    macd_hist: float = 0.5,
    macd_hist_slope: float = 0.05,
    rsi: float = 60.0,
    rsi_3: float = 55.0,
    mom_8: float = 0.02,
    vol_z: float = 0.5,
    vwap_20: float = 103.0,
    donchian_high_20: float = 110.0,
    atr: float = 2.0,
    atr_pct: float = 0.019,
    adx: float = 25.0,
) -> pd.Series:
    """Helper creating a complete feature Series representing market state."""
    return pd.Series(
        {
            "open": 104.2,
            "high": 105.5,
            "low": 103.8,
            "close": close,
            "prev_close": prev_close,
            "volume": 1000.0,
            "ema_fast": ema_fast,
            "ema_slow": ema_slow,
            "ema_200": ema_200,
            "ema_5": 104.8,
            "ema_slow_slope": ema_slow_slope,
            "ema_200_slope": 0.0005,
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
            "bb_mid": 102.0,
            "bb_upper": 106.0,
            "bb_lower": 98.0,
            "candle_range_pct": 0.015,
            "green_candle": close > 104.2,
            "swing_low_5": 103.0,
            "swing_low_20": 98.0,
            "higher_low": True,
            "prev_low": 103.5,
            "close_location": 0.65,
        }
    )


class TestProactiveMultiStrategyEngine(unittest.TestCase):
    """Pruebas unitarias para el motor de cascada multi-estrategia y señal active_momentum."""

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
            reason="trend_stack_confirmed",
        )
        self.range_regime = MarketRegime(
            name="range",
            direction="neutral",
            trend_strength=0.0005,
            atr_pct=0.012,
            risk_multiplier=0.85,
            allow_long=True,
            reason="oscillator_in_bounds",
        )

    def test_active_momentum_signal_produces_buy_on_positive_momentum(self):
        """Active momentum produces buy on healthy uptrend (RSI 55-65, aligned EMAs, positive MACD)."""
        fx = _build_test_features(
            close=105.0,
            ema_fast=102.0,
            ema_slow=100.0,
            rsi=62.0,
            macd_hist=0.6,
            macd_hist_slope=0.1,
            vol_z=0.4,
            vwap_20=103.0,
        )
        sig = self.strategy._active_momentum_signal(fx, self.bullish_regime)
        self.assertEqual(sig.action, "buy")
        self.assertEqual(sig.reason, "active_momentum")
        self.assertGreaterEqual(sig.confidence, 0.65)
        self.assertLessEqual(sig.confidence, 1.0)

    def test_active_momentum_signal_returns_hold_on_extreme_overbought_or_downtrend(self):
        """Active momentum returns hold when RSI is beyond limit or trend stack is broken."""
        # Case A: RSI too high (> 78)
        fx_overbought = _build_test_features(rsi=85.0)
        sig_overbought = self.strategy._active_momentum_signal(fx_overbought, self.bullish_regime)
        self.assertEqual(sig_overbought.action, "hold")
        self.assertEqual(sig_overbought.reason, "active_momentum_no_edge")

        # Case B: Severe downtrend below all EMAs with negative slope
        fx_downtrend = _build_test_features(
            close=90.0,
            ema_fast=96.0,
            ema_slow=100.0,
            ema_200=105.0,
            ema_slow_slope=-0.01,
            macd_hist=-0.5,
            macd_hist_slope=-0.05,
            rsi=40.0,
        )
        sig_downtrend = self.strategy._active_momentum_signal(fx_downtrend, self.bullish_regime)
        self.assertEqual(sig_downtrend.action, "hold")
        self.assertEqual(sig_downtrend.reason, "active_momentum_no_edge")

    def test_cascading_fallback_when_primary_connors_rsi_has_no_edge(self):
        """When strategy_mode is connors_rsi and rsi_3 > 20 (no edge), engine cascades to active_momentum buy."""
        cfg_connors = BotConfig(
            symbol="BTCUSDT",
            strategy_mode="connors_rsi",
            min_confidence=0.45,
            min_entry_quality=0.45,
            use_regime_filter=True,
        )
        strategy = HybridStrategy(cfg_connors)

        # In healthy rally, rsi_3 is 55 (>> 20), so connors_rsi yields hold ("connors_no_edge")
        fx = _build_test_features(
            close=106.0,
            rsi=63.0,
            rsi_3=55.0,  # Not oversold
            ema_fast=102.0,
            ema_slow=100.0,
            vol_z=0.2,
        )
        # Direct check on primary method to verify it has no edge
        primary_sig = strategy._connors_rsi_signal(fx, self.bullish_regime)
        self.assertEqual(primary_sig.action, "hold")
        self.assertEqual(primary_sig.reason, "connors_no_edge")

        # Now test _entry_signal cascading fallback
        cascade_sig = strategy._entry_signal(fx, self.bullish_regime)
        self.assertEqual(cascade_sig.action, "buy")
        self.assertIn("active_momentum", cascade_sig.reason)

        # Test full generate_from_features pipeline
        full_sig = strategy.generate_from_features(fx, self.bullish_regime)
        self.assertEqual(full_sig.action, "buy")
        self.assertIn("active_momentum", full_sig.reason)

    def test_cascading_fallback_when_primary_turtle_breakout_has_no_edge(self):
        """When strategy_mode is turtle_breakout and close <= donchian_high_20, engine cascades to buy."""
        cfg_turtle = BotConfig(
            symbol="BTCUSDT",
            strategy_mode="turtle_breakout",
            min_confidence=0.45,
            min_entry_quality=0.45,
            use_regime_filter=True,
        )
        strategy = HybridStrategy(cfg_turtle)

        # close is 105, donchian_high_20 is 110 -> breakout_ok is False
        fx = _build_test_features(
            close=105.0,
            donchian_high_20=110.0,
            rsi=58.0,
            vol_z=0.3,
        )
        primary_sig = strategy._turtle_breakout_signal(fx, self.bullish_regime)
        self.assertEqual(primary_sig.action, "hold")
        self.assertEqual(primary_sig.reason, "turtle_no_edge")

        cascade_sig = strategy._entry_signal(fx, self.bullish_regime)
        self.assertEqual(cascade_sig.action, "buy")
        self.assertIn("active_momentum", cascade_sig.reason)

    def test_cascading_fallback_in_auto_mode_bullish_trend(self):
        """In auto mode under bullish_trend, engine evaluates active_momentum cascade instead of locking in elder/connors."""
        fx = _build_test_features(
            close=105.0,
            rsi=62.0,
            rsi_3=58.0,
            macd_hist=0.4,
            vol_z=0.2,
        )
        sig = self.strategy.generate_from_features(fx, self.bullish_regime)
        self.assertEqual(sig.action, "buy")
        self.assertIn("active_momentum", sig.reason)

    def test_cascading_fallback_returns_cascade_no_edge_when_all_fail(self):
        """When none of the strategies find an edge, returns cascade_no_edge:<regime>."""
        fx_dead = _build_test_features(
            close=90.0,
            prev_close=92.0,
            ema_fast=95.0,
            ema_slow=100.0,
            ema_200=110.0,
            ema_slow_slope=-0.01,
            macd_hist=-1.0,
            macd_hist_slope=-0.1,
            rsi=40.0,
            rsi_3=42.0,
            mom_8=-0.05,
            vol_z=-1.0,
            vwap_20=105.0,
            donchian_high_20=115.0,
        )
        sig = self.strategy._entry_signal(fx_dead, self.bullish_regime)
        self.assertEqual(sig.action, "hold")
        self.assertEqual(sig.reason, "cascade_no_edge:bullish_trend")

    def test_entry_quality_recognizes_active_momentum(self):
        """_entry_quality recognizes active_momentum in price_context_ok and passes quality."""
        fx = _build_test_features(
            close=105.0,
            vwap_20=105.2,  # Close slightly below vwap_20, but >= vwap_20 * 0.995 and reason is active_momentum
        )
        entry = Signal("buy", 0.85, "active_momentum")
        macro = {"enabled": False, "allow_long": True, "score": 1.0, "reason": "macro_unavailable"}
        quality, blockers = self.strategy._entry_quality(fx, entry, self.bullish_regime, macro)
        self.assertGreaterEqual(quality, self.cfg.min_entry_quality)
        self.assertNotIn("price_context", blockers)


class TestAutoTuningImmunity(unittest.TestCase):
    """Pruebas unitarias para inmunidad ante sobreescritura de auto-tuning."""

    def test_build_autotune_grid_contains_reachable_thresholds(self):
        """_build_autotune_grid includes relaxed reachable thresholds for confidence and quality."""
        grid = _build_autotune_grid(["auto", "turtle_breakout"])
        self.assertEqual(grid["min_confidence"], [0.42, 0.46, 0.50])
        self.assertEqual(grid["min_entry_quality"], [0.45, 0.50, 0.55])

    def test_load_optimal_config_clamps_excessive_thresholds(self):
        """LiveTrader.load_optimal_config clamps min_entry_quality <= 0.55 and min_confidence <= 0.50."""
        cfg = BotConfig(
            symbol="BTCUSDT",
            auto_tune_enabled=True,
            min_confidence=0.45,
            min_entry_quality=0.45,
        )
        mock_db_session = MagicMock()
        mock_record = MagicMock()
        # High excessive thresholds that would freeze symbol in hold
        mock_record.value_json = json.dumps(
            {
                "score": 1.5,
                "params": {
                    "min_confidence": 0.65,
                    "min_entry_quality": 0.80,
                    "strategy_mode": "connors_rsi",
                },
                "metrics": {
                    "roi_pct": 12.5,
                    "profit_factor": 2.1,
                    "num_trades": 15,
                },
            }
        )
        with patch("bot.main.BinanceDataClient"), \
             patch("bot.main.BinanceExecutionClient") as mock_exec_cls, \
             patch("bot.main.build_telemetry"):
            mock_exec = mock_exec_cls.return_value
            mock_exec.get_symbol_filters.return_value = MagicMock()
            mock_exec.split_symbol.return_value = ("BTC", "USDT")
            mock_exec.get_asset_balance_values.return_value = (10000.0, 0.0)
            trader = LiveTrader(cfg)
            trader.db_session.query = MagicMock()
            trader.db_session.query.return_value.filter.return_value.first.return_value = mock_record
            trader.load_optimal_config()

            # Ensure parameters were clamped to reachable ceilings
            self.assertLessEqual(trader.cfg.min_entry_quality, 0.55)
            self.assertLessEqual(trader.cfg.min_confidence, 0.50)
            self.assertEqual(trader.cfg.min_entry_quality, 0.55)
            self.assertEqual(trader.cfg.min_confidence, 0.50)
            self.assertEqual(trader.cfg.strategy_mode, "connors_rsi")
            trader.close()


if __name__ == "__main__":
    unittest.main()
