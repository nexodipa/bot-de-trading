import logging.handlers
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from bot.binance_client import BinanceExecutionClient, SymbolFilters
from bot.config import BotConfig
from bot.telemetry import setup_logging


class TestMakerExecutionAndLogRotation(unittest.TestCase):
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

        res = exec_client.execute_smart_maker_buy(
            "BTCUSDT", 0.01, bid_price=60000.0, filters=self.filters, timeout_seconds=1
        )
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
        exec_client.create_market_buy = MagicMock(
            return_value={"orderId": 102, "status": "FILLED", "type": "MARKET"}
        )

        res = exec_client.execute_smart_maker_buy(
            "BTCUSDT", 0.01, bid_price=60000.0, filters=self.filters, timeout_seconds=1
        )
        self.assertEqual(res["type"], "MARKET")
        exec_client.create_market_buy.assert_called_once()

    def test_smart_maker_buy_zero_fill_canceled_returns_zero_qty(self) -> None:
        cfg = BotConfig(binance_api_key="k", binance_api_secret="s", use_testnet=True)
        with patch("binance.client.Client"):
            exec_client = BinanceExecutionClient(cfg)
        exec_client.create_limit_maker_buy = MagicMock(return_value={"orderId": 103, "status": "NEW"})
        exec_client.get_order_status = MagicMock(return_value={"orderId": 103, "status": "NEW", "executedQty": "0"})
        exec_client.cancel_order = MagicMock(return_value={"orderId": 103, "status": "CANCELED", "executedQty": "0"})
        exec_client.notional_is_valid = MagicMock(return_value=False)

        res = exec_client.execute_smart_maker_buy(
            "BTCUSDT", 0.01, bid_price=60000.0, filters=self.filters, timeout_seconds=1
        )
        self.assertEqual(res["status"], "CANCELED")
        self.assertEqual(res["executedQty"], "0")

    def test_setup_logging_uses_rotating_file_handler(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            log_path = os.path.join(tmpdir, "test_bot.log")
            cfg = BotConfig(log_file=log_path)
            root = logging.getLogger()
            old_handlers = list(root.handlers)
            root.handlers.clear()
            try:
                setup_logging(cfg)
                rotating = [h for h in root.handlers if isinstance(h, logging.handlers.RotatingFileHandler)]
                self.assertEqual(len(rotating), 1)
                self.assertEqual(rotating[0].maxBytes, 5 * 1024 * 1024)
                self.assertEqual(rotating[0].backupCount, 3)
            finally:
                for h in root.handlers:
                    h.close()
                root.handlers.clear()
                root.handlers.extend(old_handlers)


if __name__ == "__main__":
    unittest.main()
