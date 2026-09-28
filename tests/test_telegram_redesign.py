from __future__ import annotations

import glob
import os
import sys
import threading
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath("."))

from bot.config import BotConfig
from bot.growth_traffic_engine import (
    AutoTrafficPublisher,
    translate_inactivity_reason,
)
from bot.main import (
    _format_live_alert,
    _format_paper_alert,
    run_live,
)


class TestTelegramRedesign(unittest.TestCase):
    def setUp(self):
        self.cfg = BotConfig.from_env()

    def test_grep_verification_forbidden_strings_in_python_code(self):
        """Verifica que no exista ninguna aparición de las cadenas prohibidas en bot/*.py."""
        bot_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bot"))
        py_files = glob.glob(os.path.join(bot_dir, "**", "*.py"), recursive=True)
        self.assertGreater(len(py_files), 0, "No se encontraron archivos en bot/")

        forbidden_phrases = [
            "protocolo de protección",
            "Operaciones pausadas temporalmente",
        ]

        for filepath in py_files:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
                for phrase in forbidden_phrases:
                    self.assertNotIn(
                        phrase,
                        content,
                        f"Violación: '{phrase}' encontrada en archivo {filepath}",
                    )

    def test_translate_inactivity_reason_all_mappings(self):
        """Verifica que todas las razones técnicas se traduzcan comenzando con 'se mantiene sin operar debido a'."""
        reasons_to_test = [
            "trend_no_edge",
            "breakout_no_edge",
            "pullback_no_edge",
            "mean_reversion_no_edge",
            "turtle_no_edge",
            "connors_no_edge",
            "elder_no_edge",
            "williams_no_edge",
            "cascade_no_edge",
            "active_momentum_no_edge",
            "macro_bearish",
            "regime_bearish_trend",
            "ml_low_probability",
            "news_sentiment_negative",
            "invalid_levels",
            "spread_too_high",
            "excessive_volatility",
            "position_or_orders_open",
            "insufficient_bars",
            "invalid_day_start_equity",
            "cooldown",
            "completely_unknown_custom_reason",
            "",
        ]

        expected_prefix = "se mantiene sin operar debido a "

        for r in reasons_to_test:
            translated = translate_inactivity_reason(r)
            self.assertTrue(
                translated.startswith(expected_prefix),
                f"Para reason='{r}', '{translated}' no inicia con '{expected_prefix}'",
            )
            # Asegurar que nunca se emita terminología críptica de error
            self.assertNotIn("protocolo de protección", translated)
            self.assertNotIn("invalid_day_start_equity", translated)
            self.assertNotIn("Operaciones pausadas temporalmente", translated)

    def test_format_live_alert_inactivity_translation(self):
        """Verifica que _format_live_alert traduzca eventos de pausa/guard a lenguaje humano institucional."""
        event_pause = {"event": "risk_pause", "reason": "trend_no_edge"}
        formatted = _format_live_alert("BTCUSDT", event_pause)

        self.assertIn("📊 <b>Estado de Mercado", formatted)
        self.assertIn("El activo se mantiene sin operar debido a", formatted)
        self.assertIn("ArcaFid Quantitative", formatted)
        self.assertNotIn("protocolo de protección", formatted)
        self.assertNotIn("Operaciones pausadas temporalmente", formatted)
        self.assertNotIn("invalid_day_start_equity", formatted)

        # Caso con invalid_day_start_equity como razón
        event_day_start = {"event": "risk_pause", "reason": "invalid_day_start_equity"}
        formatted_day = _format_live_alert("ETHUSDT", event_day_start)
        self.assertIn("El activo se mantiene sin operar debido a", formatted_day)
        self.assertNotIn("invalid_day_start_equity", formatted_day)

    def test_format_live_alert_real_fills_unaffected(self):
        """Verifica que las alertas de compras y ventas sigan formateándose correctamente."""
        buy_event = {"event": "live_buy", "price": 60500.0, "qty": 0.1, "reason": "Momentum Break"}
        fmt_buy = _format_live_alert("BTCUSDT", buy_event)
        self.assertIn("🟢 <b>BUY</b>", fmt_buy)
        self.assertIn("BTCUSDT", fmt_buy)

        sell_event = {"event": "live_sell", "price": 61500.0, "qty": 0.1, "pnl": 100.0, "pnl_pct": 1.65}
        fmt_sell = _format_live_alert("BTCUSDT", sell_event)
        self.assertIn("🔴 <b>SELL</b>", fmt_sell)
        self.assertIn("+1.65%", fmt_sell)

    def test_format_paper_alert_sanitization(self):
        """Verifica que _format_paper_alert sanitice cualquier intento de emitir frases prohibidas."""
        event = {"event": "risk_pause", "reason": "protocolo de protección activado"}
        formatted = _format_paper_alert("BTCUSDT", event)
        self.assertNotIn("protocolo de protección", formatted)
        self.assertNotIn("Operaciones pausadas temporalmente", formatted)

    def test_auto_traffic_publisher_default_interval_720(self):
        """Verifica que el intervalo por defecto del loop en segundo plano sea estrictamente 720 minutos (12h)."""
        defaults = AutoTrafficPublisher.start_background_loop.__defaults__
        self.assertIsNotNone(defaults)
        self.assertEqual(defaults[0], 720)

    @patch("bot.telemetry.TelegramNotifier.send")
    @patch("bot.growth_traffic_engine.HighROIScreener.get_btc_macro")
    def test_publish_consolidated_executive_digest(self, mock_btc, mock_send):
        """Verifica la generación y envío del resumen ejecutivo consolidado de 12 horas."""
        mock_send.return_value = True
        mock_btc.return_value = {"price": 61250.0, "change_pct": 2.45}

        publisher = AutoTrafficPublisher(self.cfg)
        status = publisher.publish_consolidated_executive_digest(
            portfolio_summary={
                "capital_total": 12500.0,
                "pnl_valor": 340.50,
                "pnl_pct": 2.72,
                "win_rate": 81.2,
                "num_trades": 18,
            },
            asset_statuses={
                "BTC": "🟢 Compra ejecutada a <code>$61,240.00</code> | SL: <code>$59,800.00</code>",
                "ETH": "trend_no_edge",
            },
        )

        self.assertTrue(status)
        self.assertTrue(mock_send.called)
        sent_html = mock_send.call_args[0][0]

        self.assertIn("ARCAFID QUANTITATIVE | RESUMEN EJECUTIVO CONSOLIDADO", sent_html)
        self.assertIn("Ciclo de 12 Horas", sent_html)
        self.assertIn("$12,500.00 USD", sent_html)
        self.assertIn("81.2% Win Rate", sent_html)
        self.assertIn("Límite Fiduciario Drawdown -6.4%", sent_html)
        self.assertIn("Bitcoin (#BTC)", sent_html)
        self.assertIn("SITUACIÓN TÁCTICA DE ACTIVOS MONITOREADOS", sent_html)
        self.assertIn("se mantiene sin operar debido a", sent_html)
        self.assertNotIn("protocolo de protección", sent_html)
        self.assertNotIn("invalid_day_start_equity", sent_html)

    def test_run_live_ignores_risk_pause_and_guard_for_telegram_alert(self):
        """Verifica que run_live solo despache alertas a Telegram para live_buy y live_sell, nunca risk_pause ni live_guard."""
        from dataclasses import replace
        cfg = replace(BotConfig.from_env(), active_symbols="BTCUSDT")

        with patch("bot.main._assert_live_ready"), \
             patch("bot.main.perform_auto_tuning"), \
             patch("bot.main.LiveTrader") as mock_trader_cls, \
             patch("bot.telemetry.Telemetry.alert") as mock_alert, \
             patch("bot.telemetry.Telemetry.record") as mock_record:

            mock_trader = MagicMock()
            mock_trader_cls.return_value = mock_trader

            # 1. Simular evento risk_pause
            mock_trader.step.return_value = {"event": "risk_pause", "reason": "trend_no_edge"}
            run_live(cfg, confirm_live="I_UNDERSTAND_LIVE_RISK")
            self.assertEqual(mock_alert.call_count, 0, "telemetry.alert no debe llamarse para risk_pause")
            self.assertTrue(mock_record.called, "telemetry.record debe registrarse para auditoría")

            mock_alert.reset_mock()
            mock_record.reset_mock()

            # 2. Simular evento live_guard
            mock_trader.step.return_value = {"event": "live_guard", "reason": "regime_unknown"}
            run_live(cfg, confirm_live="I_UNDERSTAND_LIVE_RISK")
            self.assertEqual(mock_alert.call_count, 0, "telemetry.alert no debe llamarse para live_guard")
            self.assertTrue(mock_record.called)

            mock_alert.reset_mock()
            mock_record.reset_mock()

            # 3. Simular evento live_buy (orden real)
            mock_trader.step.return_value = {"event": "live_buy", "price": 60000.0, "qty": 0.1, "reason": "trend"}
            run_live(cfg, confirm_live="I_UNDERSTAND_LIVE_RISK")
            self.assertEqual(mock_alert.call_count, 1, "telemetry.alert DEBE llamarse para live_buy")
            self.assertTrue(mock_record.called)


if __name__ == "__main__":
    unittest.main()
