import os
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from bot.performance import MIN_TRADES_FOR_STATS, compute_performance, get_real_performance


def _trades(pnls):
    return [{"pnl": p, "pnl_pct": p / 100.0, "exit_time": f"2026-01-{i + 1:02d}"} for i, p in enumerate(pnls)]


class TestComputePerformance(unittest.TestCase):
    def test_no_trades_returns_none_metrics(self):
        r = compute_performance([], 10000.0)
        self.assertEqual(r["total_trades"], 0)
        self.assertFalse(r["sufficient_data"])
        for k in ("win_rate_pct", "profit_factor", "sharpe_per_trade", "max_drawdown_pct"):
            self.assertIsNone(r[k], k)

    def test_insufficient_sample_withholds_statistics(self):
        r = compute_performance(_trades([10, -5, 8]), 10000.0)
        self.assertEqual(r["total_trades"], 3)
        self.assertIsNone(r["win_rate_pct"])
        self.assertEqual(r["net_pnl"], 13.0)

    def test_metrics_with_enough_trades(self):
        pnls = ([20.0, -10.0] * (MIN_TRADES_FOR_STATS // 2))
        r = compute_performance(_trades(pnls), 10000.0)
        self.assertTrue(r["sufficient_data"])
        self.assertEqual(r["win_rate_pct"], 50.0)
        self.assertEqual(r["profit_factor"], 2.0)
        self.assertGreater(r["sharpe_per_trade"], 0)
        self.assertLess(r["max_drawdown_pct"], 0)

    def test_max_drawdown_value(self):
        pnls = [100.0] * 15 + [-500.0] + [0.0001] * 14
        r = compute_performance(_trades(pnls), 1000.0)
        peak = 1000.0 + 1500.0
        self.assertAlmostEqual(r["max_drawdown_pct"], round((-500.0 / peak) * 100, 2), places=1)

    def test_ignores_invalid_rows(self):
        r = compute_performance([{"pnl": None}, {"pnl": "x"}, {"pnl": float("nan")}, {"pnl": 5}], 100.0)
        self.assertEqual(r["total_trades"], 1)


class TestGetRealPerformance(unittest.TestCase):
    def test_empty_database_is_no_trades(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.sqlite3")
            sqlite3.connect(path).close()
            r = get_real_performance(path, 1000.0)
        self.assertEqual(r["source"], "no_trades")
        self.assertEqual(r["total_trades"], 0)

    def test_reads_live_trades_table(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.sqlite3")
            con = sqlite3.connect(path)
            con.execute(
                "CREATE TABLE trades (id INTEGER PRIMARY KEY, symbol TEXT, entry_time TEXT, exit_time TEXT, "
                "entry_price REAL, exit_price REAL, quantity REAL, pnl REAL, pnl_pct REAL, reason TEXT)"
            )
            con.execute("INSERT INTO trades VALUES (1,'BTCUSDT','a','2026-01-01',1,2,1,5.0,1.0,'tp')")
            con.commit()
            con.close()
            r = get_real_performance(path, 1000.0)
        self.assertEqual(r["source"], "live_closed_trades")
        self.assertEqual(r["total_trades"], 1)
        self.assertIsNone(r["win_rate_pct"])


class TestNoFabricatedFigures(unittest.TestCase):
    def test_square_report_requires_real_inputs(self):
        from bot.binance_square import BinanceSquareContentGenerator as G
        with self.assertRaises(TypeError):
            G.generate_audited_performance_report()
        post = G.generate_audited_performance_report(
            win_rate_pct=55.0, profit_factor=None, drawdown_lock_pct=None,
            sharpe_ratio=None, total_trades=40, source="paper_trading",
        )
        self.assertIn("paper", post.lower())
        self.assertNotIn("2.42", post)
        self.assertNotIn("78.5", post)

    def test_portal_has_no_hardcoded_track_record(self):
        from bot.institutional_portal import INSTITUTIONAL_PORTAL_HTML as html
        for fake in ("2.42", "78.5%", "AQC-88", "18.42M", "SOC 2", "Hawkes"):
            self.assertNotIn(fake, html)


if __name__ == "__main__":
    unittest.main()
