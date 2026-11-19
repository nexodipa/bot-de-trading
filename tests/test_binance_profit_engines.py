import unittest
from unittest.mock import MagicMock, patch

import pandas as pd

from bot.binance_client import BinanceExecutionClient, SymbolFilters
from bot.config import BotConfig
from bot.funding_arbitrage import FundingOpportunity, FundingRateArbitrageMonitor
from bot.grid_engine import QuantitativeRangeGrid, build_range_grid


class TestBinanceProfitEngines(unittest.TestCase):
    def setUp(self) -> None:
        self.filters = SymbolFilters(
            min_qty=0.001,
            max_qty=10000.0,
            step_size=0.001,
            min_notional=5.0,
            tick_size=0.01,
            min_price=0.01,
            max_price=1000000.0,
        )

    def test_smart_maker_buy_fills_immediately(self) -> None:
        cfg = BotConfig(binance_api_key="k", binance_api_secret="s", use_testnet=True)
        with patch("binance.client.Client"):
            exec_client = BinanceExecutionClient(cfg)
        exec_client.create_limit_maker_buy = MagicMock(return_value={"orderId": 101, "status": "FILLED"})
        exec_client.create_market_buy = MagicMock()

        res = exec_client.execute_smart_maker_buy("BTCUSDT", 0.01, bid_price=60000.0, filters=self.filters, timeout_seconds=1)
        self.assertEqual(res["status"], "FILLED")
        exec_client.create_limit_maker_buy.assert_called_once()
        exec_client.create_market_buy.assert_not_called()

    def test_smart_maker_buy_falls_back_on_2010(self) -> None:
        cfg = BotConfig(binance_api_key="k", binance_api_secret="s", use_testnet=True)
        with patch("binance.client.Client"):
            exec_client = BinanceExecutionClient(cfg)
        exec_client.create_limit_maker_buy = MagicMock(
            side_effect=RuntimeError("APIError(code=-2010): Order would immediately match and take.")
        )
        exec_client.create_market_buy = MagicMock(return_value={"orderId": 102, "status": "FILLED", "type": "MARKET"})

        res = exec_client.execute_smart_maker_buy("BTCUSDT", 0.01, bid_price=60000.0, filters=self.filters, timeout_seconds=1)
        self.assertEqual(res["type"], "MARKET")
        exec_client.create_market_buy.assert_called_once()

    def test_range_grid_build_and_breakout_stop(self) -> None:
        plan = build_range_grid(
            symbol="AVAXUSDT",
            current_price=20.0,
            atr_value=0.5,
            levels=6,
            atr_mult=2.0,
            total_quote_budget=25.0,
            min_notional=5.0,
        )
        self.assertIsNotNone(plan)
        assert plan is not None
        self.assertGreaterEqual(plan.step_pct, 0.0045)
        self.assertGreaterEqual(plan.quote_per_order, 5.0)
        self.assertTrue(all(p < 20.0 for p in plan.buy_levels))
        self.assertTrue(all(p > 20.0 for p in plan.sell_levels))

        grid = QuantitativeRangeGrid(levels=5, atr_mult=2.0, max_quote_usdt=25.0)
        df_range = pd.DataFrame({"close": [20.0, 20.1, 20.0]})
        res_active = grid.evaluate_step(
            symbol="AVAXUSDT",
            df=df_range,
            regime_label="range",
            atr_value=0.5,
            quote_free=25.0,
            dry_run=True,
        )
        self.assertEqual(res_active["event"], "grid_active")

        # Breakout below stop_loss_bound triggers grid_breakout_stop
        df_break = pd.DataFrame({"close": [20.0, 17.0]})
        res_stop = grid.evaluate_step(
            symbol="AVAXUSDT",
            df=df_break,
            regime_label="bearish_trend",
            atr_value=0.5,
            quote_free=25.0,
            dry_run=True,
        )
        self.assertEqual(res_stop["event"], "grid_breakout_stop")

    @patch("bot.funding_arbitrage.requests.get")
    def test_funding_rate_arbitrage_monitor_and_capital_guard(self, mock_get) -> None:
        mock_resp = MagicMock()
        mock_resp.json.return_value = [
            {"symbol": "SOLUSDT", "lastFundingRate": "0.00025", "markPrice": "75.0", "nextFundingTime": 1700000000000},
            {"symbol": "BTCUSDT", "lastFundingRate": "0.00005", "markPrice": "63000.0", "nextFundingTime": 1700000000000},
        ]
        mock_resp.raise_for_status.return_value = None
        mock_get.return_value = mock_resp

        monitor = FundingRateArbitrageMonitor(min_apr_pct=12.0, min_capital_usdt=200.0, max_allocation_pct=0.25)
        opps = monitor.fetch_funding_opportunities()
        # SOL: 0.00025 * 3 * 365 * 100 = 27.375% -> included; BTC: 5.475% -> excluded
        self.assertEqual(len(opps), 1)
        self.assertEqual(opps[0].symbol, "SOLUSDT")
        self.assertAlmostEqual(opps[0].annualized_apr_pct, 27.38, places=2)

        # Guard blocks micro capital ($7.50) from Futures liquidation risk
        eval_small = monitor.evaluate_allocation(capital_usdt=7.50, opportunity=opps[0])
        self.assertFalse(eval_small["eligible"])
        self.assertEqual(eval_small["reason"], "below_min_fiduciary_capital")

        # Eligible capital ($1000) calculates 1:1 delta-neutral split
        eval_ok = monitor.evaluate_allocation(capital_usdt=1000.0, opportunity=opps[0])
        self.assertTrue(eval_ok["eligible"])
        self.assertEqual(eval_ok["spot_leg_usdt"], 125.0)
        self.assertEqual(eval_ok["perp_margin_usdt"], 125.0)


if __name__ == "__main__":
    unittest.main()
