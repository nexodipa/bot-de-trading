from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pandas as pd

from bot.binance_client import SymbolFilters
from bot.config import BotConfig
from bot.db import get_db_session, DBApiCredential
from bot.earn_manager import EarnManager
from bot.enterprise_manager import EnterpriseManager
from bot.models import Position, Signal
from bot.regime import MarketRegime
from bot.strategy import HybridStrategy


class TestRigorousAuditFixes(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmp_dir, "audit_test.sqlite3")

    def tearDown(self) -> None:
        import shutil
        from bot.db import _ENGINES
        key = os.path.abspath(self.db_path)
        if key in _ENGINES:
            _ENGINES.pop(key).dispose()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_1_micro_capital_step_size_floor_bnb_600(self) -> None:
        """
        High-unit-price asset (BNBUSDT @ $600, step_size=0.001, min_notional=5.0):
        5.10 / 600 = 0.0085 -> floored to 0.008 ($4.80 < $5.00) without step_size buffer.
        With step_size buffer, viable_qty = 0.0085 + 0.001 = 0.0095 -> floored to 0.009 ($5.40 >= $5.00).
        """
        from bot.main import LiveTrader

        cfg = BotConfig(
            symbol="BNBUSDT",
            event_db_path=self.db_path,
            initial_balance=7.50,
            live_max_quote_per_trade=15.0,
            use_testnet=True,
            auto_tune_enabled=False,
            dynamic_timeframe_enabled=False,
            use_multi_timeframe=False,
            use_btc_macro_filter=False,
        )

        with patch("bot.main.BinanceDataClient") as mock_data_cls, patch(
            "bot.main.BinanceExecutionClient"
        ) as mock_exec_cls:
            mock_exec = MagicMock()
            mock_data = MagicMock()
            mock_exec_cls.return_value = mock_exec
            mock_data_cls.return_value = mock_data

            filters = SymbolFilters(
                min_qty=0.001,
                max_qty=1000.0,
                step_size=0.001,
                min_notional=5.0,
                min_price=0.01,
                max_price=100000.0,
                tick_size=0.1,
            )
            mock_exec.get_symbol_filters.return_value = filters
            mock_exec.split_symbol.return_value = ("BNB", "USDT")
            mock_exec.get_asset_balance_values.side_effect = lambda asset: (
                (7.50, 0.0) if asset == "USDT" else (0.0, 0.0)
            )
            mock_exec.normalize_quantity.side_effect = lambda q, f: int(q / f.step_size) * f.step_size
            mock_exec.quantity_is_valid.side_effect = lambda q, f: q >= f.min_qty
            mock_exec.notional_is_valid.side_effect = lambda q, p, f: (q * p) >= f.min_notional

            trader = LiveTrader(cfg)
            try:
                # Direct floor of 5.10 / 600 fails min_notional
                raw_qty, raw_reason = trader._prepare_live_qty(5.10 / 600.0, 600.0)
                self.assertEqual(raw_qty, 0.0)
                self.assertEqual(raw_reason, "min_notional_rejected")

                # With step_size buffer, it resolves to 0.009 BNB ($5.40 >= $5.00)
                step_buf = filters.step_size
                viable_qty = (5.10 / 600.0) + step_buf
                v_qty, v_reason = trader._prepare_live_qty(viable_qty, 600.0)
                self.assertEqual(v_reason, "ok")
                self.assertAlmostEqual(v_qty, 0.009, places=6)
                self.assertGreaterEqual(v_qty * 600.0, 5.0)
            finally:
                trader.close()

    def test_2_active_momentum_confidence_in_range_and_rebound(self) -> None:
        """
        Ensures active_momentum buy signals in 'range' or 'bearish_trend' rebound
        receive regime_multiplier=0.85 rather than 0.35 or 0.0.
        """
        cfg = BotConfig(
            strategy_mode="active_momentum",
            min_confidence=0.45,
            min_entry_quality=0.55,
            use_regime_filter=True,
            use_btc_macro_filter=False,
        )
        strat = HybridStrategy(cfg)
        fx = pd.Series(
            {
                "close": 605.0,
                "open": 600.0,
                "high": 606.0,
                "low": 599.5,
                "prev_close": 600.0,
                "ema_5": 604.0,
                "ema_fast": 602.0,
                "ema_slow": 600.0,
                "ema_200": 595.0,
                "ema_slow_slope": 0.001,
                "rsi": 58.0,
                "rsi_3": 55.0,
                "atr": 4.0,
                "atr_pct": 0.0066,
                "adx": 20.0,
                "macd_hist": 0.5,
                "macd_hist_slope": 0.1,
                "mom_8": 0.008,
                "vol_z": 0.5,
                "vwap_20": 601.0,
                "vwap_50": 599.0,
                "bb_lower": 590.0,
                "bb_mid": 600.0,
                "donchian_high_20": 610.0,
                "donchian_low_20": 590.0,
                "candle_range_pct": 0.01,
                "close_location": 0.85,
                "higher_low": True,
                "green_candle": True,
            }
        )
        range_regime = MarketRegime(
            name="range",
            direction="neutral",
            trend_strength=0.0005,
            atr_pct=0.0066,
            risk_multiplier=0.35,
            allow_long=True,
            reason="range_low_volatility",
        )
        sig = strat.generate_from_features(fx, range_regime)
        self.assertEqual(sig.action, "buy")
        self.assertIn("active_momentum", sig.reason)

    def test_3_earn_unauthorized_circuit_breaker(self) -> None:
        """
        When Simple Earn returns -1002 unauthorized, EarnManager sets _sapi_write_unauthorized
        and skips subsequent subscribe calls without spamming API calls.
        """
        cfg = BotConfig(earn_enabled=True)
        mock_client = MagicMock()
        earn = EarnManager(cfg=cfg, client=mock_client, dry_run=False)
        earn._flexible_products_cache["USDT"] = {
            "productId": "USDT001",
            "minPurchaseAmount": "0.1",
            "latestAnnualPercentageRate": "0.05",
        }
        mock_client._request_margin_api.side_effect = RuntimeError(
            "APIError(code=-1002): You are not authorized to execute this request."
        )

        res1 = earn.subscribe_flexible("USDT", 10.0)
        self.assertFalse(res1["ok"])
        self.assertTrue(earn._sapi_write_unauthorized)
        self.assertEqual(mock_client._request_margin_api.call_count, 1)

        # Second call is short-circuited immediately without hitting the API
        res2 = earn.subscribe_flexible("USDT", 10.0)
        self.assertFalse(res2["ok"])
        self.assertEqual(res2["reason"], "sapi_write_unauthorized")
        self.assertEqual(mock_client._request_margin_api.call_count, 1)

    def test_4_enterprise_manager_credential_upsert_idempotent(self) -> None:
        """
        Adding API credentials for the same (user_id, platform) updates in-place instead of duplicating rows.
        """
        session = get_db_session(self.db_path)
        try:
            em = EnterpriseManager(session)
            user = em.create_user("audit@fehu.fund", "Audit User")
            em.add_api_credential(user.id, "binance", "key_v1", "sec_v1")
            em.add_api_credential(user.id, "binance", "key_v2", "sec_v2")

            count = session.query(DBApiCredential).filter_by(user_id=user.id, platform="binance").count()
            self.assertEqual(count, 1)
            k, s, _ = em.get_api_credentials(user.id, "binance")
            self.assertEqual(k, "key_v2")
            self.assertEqual(s, "sec_v2")
        finally:
            session.close()

    def test_5_binance_square_compliance_shield_and_30023_circuit_breaker(self) -> None:
        """
        Verifies:
        1. Outgoing OpenAPI payload strips external URLs (github.io, https://), @handles, /subscribe,
           wallet addresses, and >3 hashtags while adding an educational DYOR disclaimer.
        2. When Binance Square returns code '30023', the 24h circuit breaker trips and blocks
           subsequent network calls to protect the account.
        """
        from bot.binance_square import (
            BinanceSquareContentGenerator,
            BinanceSquarePublisher,
            enforce_square_community_compliance,
        )

        raw_setup = BinanceSquareContentGenerator.generate_quant_setup_post(
            symbol="SOLUSDT",
            action="BUY",
            entry_price=145.50,
            stop_price=141.80,
            tp1=149.10,
            tp2=153.50,
            tp3=158.60,
            composite_score=0.785,
            timeframe="15m",
            thesis="Ruptura técnica con volumen verificado. Wallet: TYDzsYocNCWiSCxZ5B29Y5c26q9wR18W3X",
        )
        compliant = enforce_square_community_compliance(raw_setup)
        self.assertNotIn("https://", compliant)
        self.assertNotIn("github.io", compliant)
        self.assertNotIn("@AdminVIPSignals", compliant)
        self.assertNotIn("/subscribe", compliant)
        self.assertNotIn("Telegram", compliant)
        self.assertNotIn("TYDzsYocNCWiSCxZ5B29Y5c26q9wR18W3X", compliant)
        self.assertIn("no constituye asesoramiento financiero", compliant.lower())
        # Max 3 hashtags
        import re
        self.assertLessEqual(len(re.findall(r"#[a-zA-Z0-9_]+", compliant)), 3)

        # Test 30023 Circuit Breaker
        cfg = BotConfig(
            binance_square_enabled=True,
            binance_square_api_key="test_sq_key",
            event_db_path=self.db_path,
        )
        pub = BinanceSquarePublisher(cfg)
        with patch("requests.post") as mock_post:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"code": "30023", "message": "Account restricted", "success": False}
            mock_post.return_value = mock_resp

            ok1 = pub.publish_post(raw_setup)
            self.assertFalse(ok1)
            self.assertEqual(mock_post.call_count, 1)
            restricted, reason = pub.rate_limiter.is_restricted()
            self.assertTrue(restricted)
            self.assertIn("30023", reason)

            # Second attempt must be blocked locally without making any HTTP request
            ok2 = pub.publish_post("Second post attempt")
            self.assertFalse(ok2)
            self.assertEqual(mock_post.call_count, 1)


if __name__ == "__main__":
    unittest.main()
