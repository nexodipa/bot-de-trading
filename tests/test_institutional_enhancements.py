import json
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from bot.config import BotConfig
from bot.growth_traffic_engine import AutoTrafficPublisher
from bot.risk import RiskManager, compute_volatility_scale


class TestVolatilityScalingAndTearsheet(unittest.TestCase):
    def setUp(self) -> None:
        self.tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.tmpdir.name, "test_events.sqlite3")
        self.cfg = BotConfig(
            event_db_path=self.db_path,
            telegram_enabled=True,
            telegram_bot_token="123456:TESTTOKEN",
            telegram_chat_id="999999",
            risk_per_trade=0.01,
            max_position_pct=0.50,
            initial_balance=1000.0,
        )

    def tearDown(self) -> None:
        self.tmpdir.cleanup()

    def test_compute_volatility_scale_bounds(self) -> None:
        # Neutral when no volatility inputs
        self.assertEqual(compute_volatility_scale(), 1.0)
        # Spike >= 2.0x baseline cuts size to 50%
        self.assertEqual(compute_volatility_scale(vol_ratio=2.2), 0.50)
        # Elevated 1.5x-2.0x cuts size to 75%
        self.assertEqual(compute_volatility_scale(vol_ratio=1.6), 0.75)
        # Calm compression <= 0.85 scales up modestly to 1.15
        self.assertEqual(compute_volatility_scale(vol_ratio=0.75), 1.15)
        # High atr_pct (5% vs 2.5% target) halves size
        self.assertAlmostEqual(compute_volatility_scale(atr_pct=0.05, target_atr_pct=0.025), 0.50, places=4)
        # Combined takes conservative minimum
        self.assertEqual(compute_volatility_scale(vol_ratio=0.75, atr_pct=0.05), 0.50)

    def test_risk_manager_position_size_volatility_scaling(self) -> None:
        rm = RiskManager(self.cfg)
        base_qty = rm.position_size(equity=1000.0, entry_price=100.0, stop_price=95.0, fee_rate=0.001)
        spike_qty = rm.position_size(
            equity=1000.0, entry_price=100.0, stop_price=95.0, fee_rate=0.001, vol_ratio=2.1
        )
        calm_qty = rm.position_size(
            equity=1000.0, entry_price=100.0, stop_price=95.0, fee_rate=0.001, vol_ratio=0.80
        )
        self.assertAlmostEqual(spike_qty, base_qty * 0.50, places=6)
        self.assertAlmostEqual(calm_qty, base_qty * 1.15, places=6)

    @patch("bot.telemetry.TelegramNotifier.send", return_value=True)
    @patch("bot.growth_traffic_engine.HighROIScreener.get_btc_macro", return_value={"price": 63500.0, "change_pct": -1.2})
    @patch("bot.growth_traffic_engine.HuggingFaceSentimentEngine.fetch_latest_sentiment", return_value={"label": "Neutral", "score": 0.05})
    def test_executive_digest_hydrates_live_sqlite_state(self, _mock_sent, _mock_btc, mock_send) -> None:
        conn = sqlite3.connect(self.db_path)
        with conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS bot_state (key TEXT PRIMARY KEY, updated_ts TEXT, value_json TEXT)"
            )
            conn.execute(
                "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT, mode TEXT, symbol TEXT, event TEXT, payload_json TEXT)"
            )
            conn.execute(
                "INSERT INTO bot_state (key, updated_ts, value_json) VALUES (?, ?, ?)",
                ("live:trader:BTCUSDT", "2026-11-18T10:00:00+00:00", json.dumps({"cash": 42.50})),
            )
            conn.execute(
                "INSERT INTO events (ts, mode, symbol, event, payload_json) VALUES (?, ?, ?, ?, ?)",
                ("2026-11-18T10:00:00+00:00", "live", "BTCUSDT", "hold", json.dumps({"reason": "cascade_no_edge:bearish_trend:bearish_trend"})),
            )
        conn.close()

        pub = AutoTrafficPublisher(self.cfg)
        ok = pub.publish_consolidated_executive_digest()
        self.assertTrue(ok)
        self.assertTrue(mock_send.called)
        sent_html = mock_send.call_args[0][0]
        self.assertEqual(mock_send.call_args[1].get("category"), "tearsheet")
        self.assertIn("$42.50 USD", sent_html)
        self.assertIn("Operativa Normal", sent_html)
        self.assertIn("evaluación secuencial de estrategias sin confluencia de entrada", sent_html.lower())

        # Verify persisted timestamp roundtrip
        pub._set_persisted_ts("telegram:last_digest_ts", 123456.0)
        self.assertEqual(pub._get_persisted_ts("telegram:last_digest_ts"), 123456.0)


if __name__ == "__main__":
    unittest.main()
