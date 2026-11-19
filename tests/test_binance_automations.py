import unittest
from unittest.mock import MagicMock

import pandas as pd

from bot.config import BotConfig
from bot.dca_accumulator import QuantitativeDCAAccumulator
from bot.earn_manager import EarnManager
from bot.main import LiveTrader


class TestBinanceAutomations(unittest.TestCase):
    def test_dca_accumulator_oversold_and_cooldown(self) -> None:
        dca = QuantitativeDCAAccumulator(rsi_threshold=28.0, cooldown_hours=72, quote_usdt=6.0)
        # Build 220-candle downtrend so RSI < 28 and price < EMA200 * 0.92
        prices = [100.0] * 180 + [100.0 - (i * 0.9) for i in range(1, 41)]
        df = pd.DataFrame({"close": prices})

        ok, meta = dca.should_accumulate("BTCUSDT", df, last_buy_ts=0.0, now_ts=1_000_000.0)
        self.assertTrue(ok, f"Expected DCA authorized, got {meta}")
        self.assertLessEqual(meta["rsi"], 28.0)

        # Cooldown blocks immediate re-buy
        ok2, meta2 = dca.should_accumulate("BTCUSDT", df, last_buy_ts=999_000.0, now_ts=1_000_000.0)
        self.assertFalse(ok2)
        self.assertEqual(meta2["reason"], "dca_cooldown_active")

    def test_earn_launchpool_bnb_ready(self) -> None:
        cfg = BotConfig(earn_enabled=True, earn_launchpool_auto_stake=True)
        client = MagicMock()
        em = EarnManager(cfg, client, dry_run=True)
        em._free_balance = MagicMock(return_value=0.05)
        em.subscribe_flexible = MagicMock(return_value={"ok": True, "dry_run": True})

        res = em.ensure_bnb_launchpool_ready()
        self.assertTrue(res["ok"])
        self.assertEqual(res["action"], "subscribed_bnb")
        em.subscribe_flexible.assert_called_once_with("BNB", 0.05)

        # Below min BNB skips safely
        em._free_balance = MagicMock(return_value=0.0002)
        res_skip = em.ensure_bnb_launchpool_ready()
        self.assertTrue(res_skip["ok"])
        self.assertEqual(res_skip["action"], "none")

    def test_live_trader_profit_sweep(self) -> None:
        trader = LiveTrader.__new__(LiveTrader)
        trader.cfg = BotConfig(profit_sweep_pct=0.30, earn_min_subscribe=0.1)
        trader.quote_asset = "USDT"
        trader.earn = MagicMock()

        swept = trader._maybe_sweep_profit(10.0)
        self.assertAlmostEqual(swept, 3.0, places=4)
        trader.earn.subscribe_flexible.assert_called_once_with("USDT", 3.0)

        # Zero or negative pnl does not sweep
        trader.earn.reset_mock()
        self.assertEqual(trader._maybe_sweep_profit(-2.0), 0.0)
        trader.earn.subscribe_flexible.assert_not_called()


if __name__ == "__main__":
    unittest.main()
