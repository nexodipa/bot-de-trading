from __future__ import annotations

import os
import sys
import tempfile
import unittest
from dataclasses import replace
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath("."))

from bot.config import BotConfig
from bot.growth_traffic_engine import (
    AutoTrafficPublisher,
    HighROIScreener,
    HuggingFaceSentimentEngine,
    reset_square_worker,
)


class TestGrowthTrafficEngine(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "growth_test.sqlite3")
        self.cfg = replace(
            BotConfig.from_env(),
            event_db_path=self.db_path,
            binance_square_enabled=False,
            binance_square_dry_run=True,
            telegram_enabled=True,
            telegram_bot_token="mock_token",
            telegram_chat_id="999999",
        )

    def tearDown(self):
        reset_square_worker()
        self._tmpdir.cleanup()

    @patch("requests.get")
    def test_sentiment_engine(self, mock_get):
        rss_xml = (
            b"<?xml version='1.0' encoding='UTF-8'?>"
            b"<rss><channel><item><title>Bitcoin institutional inflow surge</title></item></channel></rss>"
        )
        mock_get.return_value = MagicMock(status_code=200, content=rss_xml)
        engine = HuggingFaceSentimentEngine()
        sent = engine.fetch_latest_sentiment()
        self.assertIn("score", sent)
        self.assertIn("label", sent)
        self.assertIn("headlines", sent)
        self.assertGreaterEqual(sent["score"], -1.0)
        self.assertLessEqual(sent["score"], 1.0)
        self.assertTrue(mock_get.called)

    @patch("requests.get")
    def test_high_roi_screener_mock(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {"symbol": "BTCUSDT", "quoteVolume": "100000000", "priceChangePercent": "2.5", "lastPrice": "60000", "highPrice": "61000", "lowPrice": "59000"},
            {"symbol": "RAYUSDT", "quoteVolume": "45000000", "priceChangePercent": "21.5", "lastPrice": "2.5", "highPrice": "2.8", "lowPrice": "2.1"},
            {"symbol": "SOLUSDT", "quoteVolume": "80000000", "priceChangePercent": "5.5", "lastPrice": "150", "highPrice": "155", "lowPrice": "145"},
            {"symbol": "BTCUPUSDT", "quoteVolume": "99999999", "priceChangePercent": "50.0", "lastPrice": "10", "highPrice": "12", "lowPrice": "8"},  # Excluded
        ]

        movers = HighROIScreener.get_top_movers(min_volume_usdt=5_000_000.0, top_n=5)
        self.assertEqual(len(movers), 3)
        self.assertEqual(movers[0]["symbol"], "RAYUSDT")
        self.assertEqual(movers[0]["change_pct"], 21.5)

    @patch("bot.telemetry.TelegramNotifier.send")
    @patch("bot.growth_traffic_engine.HighROIScreener.get_top_movers")
    @patch("bot.growth_traffic_engine.HighROIScreener.get_btc_macro")
    def test_auto_traffic_publisher_methods(self, mock_btc, mock_movers, mock_send):
        mock_send.return_value = True
        mock_btc.return_value = {"price": 60500.0, "change_pct": 2.1}
        mock_movers.return_value = [
            {"symbol": "SOLUSDT", "price": 145.5, "change_pct": 6.8, "quote_volume": 45000000.0, "high": 150.0, "low": 140.0}
        ]
        publisher = AutoTrafficPublisher(self.cfg)

        # Test market pulse
        res_pulse = publisher.publish_market_pulse()
        self.assertTrue(res_pulse)
        self.assertTrue(mock_send.called)
        sent_text = mock_send.call_args[0][0]
        self.assertIn("PULSO DE MERCADO", sent_text)

        # Test hot coin alert
        res_hot = publisher.publish_hot_coin_alert()
        self.assertTrue(res_hot)
        sent_hot = mock_send.call_args[0][0]
        self.assertIn("ALERTA DE VOLATILIDAD", sent_hot)

        # Test VIP promo
        res_promo = publisher.publish_vip_promo()
        self.assertTrue(res_promo)
        sent_promo = mock_send.call_args[0][0]
        self.assertIn("MEMBRESÍAS DISPONIBLES", sent_promo)

    def test_square_last_post_ts_persisted_across_restarts(self):
        """AutoTrafficPublisher persists square:last_post_ts and square:cycle_idx across instances."""
        pub1 = AutoTrafficPublisher(self.cfg)
        pub1._set_persisted_ts("square:last_post_ts", 1234567.5)
        pub1._set_persisted_ts("square:cycle_idx", 3.0)

        pub2 = AutoTrafficPublisher(self.cfg)
        self.assertEqual(pub2._get_persisted_ts("square:last_post_ts"), 1234567.5)
        self.assertEqual(int(pub2._get_persisted_ts("square:cycle_idx")), 3)

    @patch("bot.growth_traffic_engine.enqueue_square_post", return_value=True)
    @patch("bot.growth_traffic_engine.HuggingFaceSentimentEngine.fetch_latest_sentiment")
    @patch("bot.growth_traffic_engine.HighROIScreener.get_top_movers")
    @patch("bot.growth_traffic_engine.HighROIScreener.get_btc_macro")
    def test_publish_square_macro_strips_english_rss_headlines(
        self, mock_btc, mock_movers, mock_sent, mock_enqueue
    ):
        """publish_square_macro must summarize themes in Spanish without interpolating raw English headlines."""
        mock_btc.return_value = {"price": 64250.0, "change_pct": 2.1, "high": 65000.0, "low": 63000.0, "volume_usdt": 2_500_000_000.0}
        mock_movers.return_value = [
            {"symbol": "SOLUSDT", "price": 145.5, "change_pct": 6.8, "quote_volume": 45000000.0}
        ]
        english_hl = "Bitcoin ETF sees record inflows amid Fed pause"
        mock_sent.return_value = {"score": 0.45, "label": "Alcista", "headlines": [english_hl]}

        publisher = AutoTrafficPublisher(self.cfg)
        ok = publisher.publish_square_macro()
        self.assertTrue(ok)
        mock_enqueue.assert_called_once()
        post = mock_enqueue.call_args[0][0]
        self.assertNotIn(english_hl, post)
        self.assertNotIn("FinBERT", post)
        self.assertIn("flujos en productos institucionales y ETF", post)

    @patch("bot.growth_traffic_engine.enqueue_square_post", return_value=True)
    @patch("bot.growth_traffic_engine.HuggingFaceSentimentEngine.fetch_latest_sentiment")
    @patch("bot.growth_traffic_engine.HighROIScreener.get_top_movers")
    @patch("bot.growth_traffic_engine.HighROIScreener.get_btc_macro")
    def test_scheduled_square_archetypes_diverse_when_trades_lt_30(
        self, mock_btc, mock_movers, mock_sent, mock_enqueue
    ):
        """When total_trades < 30, publish_square_structure_digest provides distinct rotated posts."""
        mock_btc.return_value = {"price": 64000.0, "change_pct": 1.2, "high": 64800.0, "low": 63200.0, "volume_usdt": 1_800_000_000.0}
        mock_movers.return_value = [
            {"symbol": "SOLUSDT", "price": 145.5, "change_pct": 6.8, "quote_volume": 45000000.0},
            {"symbol": "ETHUSDT", "price": 3200.0, "change_pct": 2.4, "quote_volume": 90000000.0},
        ]
        mock_sent.return_value = {"score": 0.10, "label": "Neutral", "headlines": []}

        publisher = AutoTrafficPublisher(self.cfg)
        self.assertFalse(publisher.publish_square_audit())
        self.assertTrue(publisher.publish_square_macro())
        macro_post = mock_enqueue.call_args[0][0]
        self.assertTrue(publisher.publish_square_structure_digest(theme_idx=0))
        digest_0 = mock_enqueue.call_args[0][0]
        self.assertTrue(publisher.publish_square_structure_digest(theme_idx=1))
        digest_1 = mock_enqueue.call_args[0][0]

        self.assertNotEqual(macro_post, digest_0)
        self.assertNotEqual(digest_0, digest_1)
        self.assertIn("no constituye asesoramiento financiero", digest_0.lower())
        self.assertIn("?", digest_0)

    def test_worker_cfg_signature_rebinds_on_rate_limit_change(self):
        """get_square_worker must stop old worker and rebind when rate_limit or cooldown config changes."""
        from bot.growth_traffic_engine import get_square_worker

        cfg1 = replace(
            self.cfg,
            binance_square_enabled=True,
            binance_square_api_key="valid_test_key",
            binance_square_dry_run=True,
            binance_square_rate_limit_per_hour=5,
            binance_square_min_cooldown_minutes=15,
        )
        w1 = get_square_worker(cfg1)
        self.assertIsNotNone(w1)
        self.assertTrue(w1.running)
        self.assertEqual(w1.publisher.rate_limiter.rate_limit_per_hour, 5)

        cfg2 = replace(cfg1, binance_square_rate_limit_per_hour=2)
        w2 = get_square_worker(cfg2)
        self.assertIsNotNone(w2)
        self.assertIsNot(w2, w1)
        self.assertFalse(w1.running)
        self.assertTrue(w2.running)
        self.assertEqual(w2.publisher.rate_limiter.rate_limit_per_hour, 2)

        cfg3 = replace(cfg2, binance_square_min_cooldown_minutes=30)
        w3 = get_square_worker(cfg3)
        self.assertIsNotNone(w3)
        self.assertIsNot(w3, w2)
        self.assertFalse(w2.running)
        self.assertTrue(w3.running)
        self.assertEqual(w3.publisher.rate_limiter.min_cooldown_seconds, 1800.0)


if __name__ == "__main__":
    unittest.main()
