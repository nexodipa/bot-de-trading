"""
Unit tests for Milestone 1: Equity Auto-Initialization & Risk Unblock.
File: tests/test_equity_auto_init.py
"""
import unittest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import json
import tempfile
import os

from bot.config import BotConfig
from bot.risk import RiskManager, CircuitBreakerStatus
from bot.main import LiveTrader
from bot.db import DBBotState, get_db_session


class TestEquityAutoInitAndRiskUnblock(unittest.TestCase):
    def setUp(self):
        self.cfg = BotConfig(
            symbol="BTCUSDT",
            initial_balance=10000.0,
            max_daily_drawdown=0.05,
        )
        self.risk = RiskManager(self.cfg)

    def test_can_trade_auto_seeds_zero_day_start_equity(self):
        """When equity <= 0 is passed to can_trade in cold start, day_start_equity is auto-seeded safely."""
        self.assertEqual(self.risk.state.day_start_equity, 0.0)
        now = datetime.now(timezone.utc)
        allowed, reason = self.risk.can_trade(now, 0.0)
        self.assertTrue(allowed, f"Expected allowed=True, got reason={reason}")
        self.assertEqual(reason, "ok")
        self.assertEqual(self.risk.state.day_start_equity, 10000.0)
        self.assertIsNotNone(self.risk.state.day_anchor)

    def test_can_trade_auto_seeds_negative_or_none_equity(self):
        """When equity is negative, can_trade resolves positive safe equity."""
        now = datetime.now(timezone.utc)
        allowed, reason = self.risk.can_trade(now, -500.0)
        self.assertTrue(allowed)
        self.assertEqual(reason, "ok")
        self.assertEqual(self.risk.state.day_start_equity, 10000.0)

    def test_sync_day_preserves_positive_equity_when_passed_zero(self):
        """sync_day never overwrites a positive day_start_equity with <= 0."""
        now = datetime.now(timezone.utc)
        self.risk.sync_day(now, 12500.0)
        self.assertEqual(self.risk.state.day_start_equity, 12500.0)

        # Next day with 0.0 equity reading
        next_day = now + timedelta(days=1)
        self.risk.sync_day(next_day, 0.0)
        self.assertEqual(self.risk.state.day_start_equity, 12500.0)

    def test_direct_check_global_circuit_breaker_zeros_still_locks(self):
        """Direct adversarial calls to check_global_circuit_breaker(0.0, 0.0) still return non_positive_equity."""
        allowed, reason = self.risk.check_global_circuit_breaker(0.0, 0.0)
        self.assertFalse(allowed)
        self.assertIn("non_positive_equity", reason)

    def test_live_trader_balances_fallback_when_quote_zero(self):
        """LiveTrader._balances does not zero out cash when broker returns 0.0."""
        with patch("bot.main.BinanceDataClient"), \
             patch("bot.main.BinanceExecutionClient") as mock_exec_cls:
            mock_exec = mock_exec_cls.return_value
            mock_exec.get_symbol_filters.return_value = MagicMock()
            mock_exec.split_symbol.return_value = ("BTC", "USDT")
            mock_exec.get_asset_balance_values.return_value = (0.0, 0.0)
            mock_exec.get_account.return_value = {"balances": []}

            trader = LiveTrader(self.cfg)
            trader.cash = 10000.0
            q_free, q_locked, b_free, b_locked = trader._balances()
            self.assertGreaterEqual(trader.cash, 10000.0)
            trader.close()

    def test_live_trader_equity_returns_safe_positive(self):
        """LiveTrader._equity returns positive fallback if cash + pos_val <= 0."""
        with patch("bot.main.BinanceDataClient"), \
             patch("bot.main.BinanceExecutionClient") as mock_exec_cls:
            mock_exec = mock_exec_cls.return_value
            mock_exec.get_symbol_filters.return_value = MagicMock()
            mock_exec.split_symbol.return_value = ("BTC", "USDT")
            mock_exec.get_asset_balance_values.return_value = (10000.0, 0.0)

            trader = LiveTrader(self.cfg)
            trader.cash = 0.0
            trader.position = None
            eq = trader._equity(50000.0)
            self.assertEqual(eq, 10000.0)
            trader.close()

    def test_load_optimal_config_preserves_risk_state(self):
        """LiveTrader.load_optimal_config preserves existing risk state and day_start_equity."""
        with patch("bot.main.BinanceDataClient"), \
             patch("bot.main.BinanceExecutionClient") as mock_exec_cls:
            mock_exec = mock_exec_cls.return_value
            mock_exec.get_symbol_filters.return_value = MagicMock()
            mock_exec.split_symbol.return_value = ("BTC", "USDT")
            mock_exec.get_asset_balance_values.return_value = (10000.0, 0.0)

            trader = LiveTrader(self.cfg)
            trader.risk.state.day_start_equity = 14200.0
            trader.risk.state.daily_trade_count = 3
            anchor = datetime.now(timezone.utc)
            trader.risk.state.day_anchor = anchor

            # Mock optimal config in DB session
            mock_record = MagicMock()
            mock_record.value_json = json.dumps({
                "params": {"rsi_oversold": 28.0},
                "score": 88.0,
                "profit_factor": 1.9,
                "win_rate": 0.65,
                "max_drawdown": 0.03,
            })
            trader.db_session.query = MagicMock()
            trader.db_session.query.return_value.filter.return_value.first.return_value = mock_record

            trader.load_optimal_config()

            self.assertEqual(trader.risk.state.day_start_equity, 14200.0)
            self.assertEqual(trader.risk.state.daily_trade_count, 3)
            self.assertEqual(trader.risk.state.day_anchor, anchor)
            trader.close()

    def test_load_state_auto_seeds_day_start_equity_if_zero_in_db(self):
        """LiveTrader.load_state auto-seeds day_start_equity if record in DB has <= 0."""
        temp_db = tempfile.NamedTemporaryFile(suffix=".sqlite3", delete=False)
        temp_db.close()
        db_path = temp_db.name
        trader = None
        try:
            cfg = BotConfig(
                symbol="ETHUSDT",
                initial_balance=10000.0,
                event_db_path=db_path,
            )
            sess = get_db_session(db_path)
            state_rec = DBBotState(
                key=f"risk_state:ETHUSDT",
                value_json=json.dumps({"day_start_equity": 0.0, "consecutive_losses": 0}),
            )
            sess.add(state_rec)
            sess.commit()
            sess.close()

            with patch("bot.main.BinanceDataClient"), \
                 patch("bot.main.BinanceExecutionClient") as mock_exec_cls:
                mock_exec = mock_exec_cls.return_value
                mock_exec.get_symbol_filters.return_value = MagicMock()
                mock_exec.split_symbol.return_value = ("ETH", "USDT")
                mock_exec.get_asset_balance_values.return_value = (10000.0, 0.0)

                trader = LiveTrader(cfg)
                self.assertGreaterEqual(trader.risk.state.day_start_equity, 10000.0)
        finally:
            if trader is not None and hasattr(trader, "close"):
                trader.close()
            if os.path.exists(db_path):
                try:
                    os.remove(db_path)
                except Exception:
                    pass


if __name__ == "__main__":
    unittest.main()
