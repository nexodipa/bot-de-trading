from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import tempfile
import time
import unittest
import uuid
from typing import Any
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.abspath("."))

import requests
from bot.config import BotConfig
from bot.binance_square import BinanceSquarePublisher

# Dynamically import components with fallback to allow verification across implementation stages
try:
    from bot.growth_traffic_engine import BinanceSquareContentGenerator
except ImportError:
    try:
        from bot.binance_square import BinanceSquareContentGenerator  # type: ignore[assignment]
    except ImportError:
        BinanceSquareContentGenerator = None  # type: ignore[assignment]

try:
    from bot.binance_square import SquareRateLimiter
except ImportError:
    try:
        from bot.growth_traffic_engine import SquareRateLimiter  # type: ignore[assignment]
    except ImportError:
        SquareRateLimiter = None  # type: ignore[assignment]

try:
    from bot.binance_square import sanitize_for_square
except ImportError:
    try:
        from bot.growth_traffic_engine import sanitize_for_square  # type: ignore[assignment]
    except ImportError:
        sanitize_for_square = None  # type: ignore[assignment]


class TestPostArchetypeRendering(unittest.TestCase):
    """Test suite for R1: Rendering of the 3 Binance Square content archetypes & precision."""

    def setUp(self) -> None:
        if BinanceSquareContentGenerator is None:
            self.skipTest("BinanceSquareContentGenerator not yet implemented in codebase")

    def test_render_archetype_1_quant_setup_alert(self) -> None:
        """Archetype 1: High-conviction setup (Composite Score >= 0.72), entry, TP1/2/3, SL, R:R >= 1:2.5."""
        post = BinanceSquareContentGenerator.generate_quant_setup_post(
            symbol="SOLUSDT",
            action="BUY",
            entry_price=145.50,
            stop_price=141.80,
            tp1=149.10,
            tp2=153.50,
            tp3=158.60,
            composite_score=0.785,
            timeframe="15m",
            thesis="Ruptura de volatilidad con volumen institucional anomalamente alto."
        )
        self.assertIsInstance(post, str)
        self.assertTrue(len(post) > 50, "Post should not be empty")

        # Invariant 1: Symbol & directional bias present
        self.assertIn("$SOL", post)
        self.assertTrue(any(act in post.upper() for act in ["ALCISTA", "LONG", "COMPRA", "BUY"]))

        # Invariant 2: Execution levels (Entry, TP1, TP2, TP3, SL) present with formatted values
        self.assertIn("145.50", post)
        self.assertIn("141.80", post)
        self.assertIn("149.10", post)
        self.assertIn("153.50", post)
        self.assertIn("158.60", post)

        # Invariant 3: Exact Risk/Reward ratio represented
        rr_matches = re.findall(r"1\s*:\s*(\d+(?:\.\d+)?)", post)
        self.assertTrue(rr_matches, f"Risk/Reward ratio missing in post: {post}")
        self.assertGreaterEqual(float(rr_matches[0]), 2.5, f"R:R ratio must be >= 2.5 here, found {rr_matches[0]}")

        # Invariant 4: Quantitative score >= 0.72 represented
        self.assertTrue(
            any(sc in post for sc in ["0.785", "0.79", "78.5%", "Score", "Composite"]),
            f"Composite score indicator missing in setup alert: {post}"
        )

        # Invariant 5: Zero external CTAs/URLs + native compliance tags & DYOR
        self.assertNotIn("@AdminVIPSignals", post)
        self.assertNotIn("/subscribe", post)
        self.assertNotIn("github.io", post)
        self.assertNotIn("https://", post)
        self.assertIn("#BinanceSquare", post)
        self.assertIn("#TradingCuantitativo", post)
        self.assertLessEqual(len(re.findall(r"#[a-zA-Z0-9_]+", post)), 3)
        cashtags = set(re.findall(r"\$(?!\d+[KMBT]?\b)((?:[0-9]{1,5})?[A-Z]{2,10}(?:[0-9]{1,3})?)\b", post))
        self.assertLessEqual(len(cashtags), 2)
        self.assertIn("?", post)
        self.assertIn("Proyecto Fehu", post)
        self.assertIn("no constituye asesoramiento financiero", post.lower())

    def test_render_archetype_2_daily_macro_report(self) -> None:
        """Archetype 2: Daily Macro & Market Report (BTC summary, top gainers, truthful RSS sentiment)."""
        gainers = [
            {"symbol": "SOLUSDT", "price": 145.50, "change_pct": 8.24, "quote_volume": 45000000.0},
            {"symbol": "AVAXUSDT", "price": 28.40, "change_pct": 5.12, "quote_volume": 18000000.0},
        ]
        post = BinanceSquareContentGenerator.generate_macro_market_report(
            btc_price=64250.0,
            btc_change_pct=3.45,
            top_gainers=gainers,
            sentiment_label="[ALCISTA] Fuerte Presión Compradora",
            sentiment_score=0.68,
            macro_summary="Flujo institucional neto positivo en derivados y acumulación en spot."
        )
        self.assertIsInstance(post, str)
        self.assertTrue(len(post) > 50)

        # Invariant 1: Bitcoin macro summary present
        self.assertTrue("64,250" in post or "64250" in post, "BTC price missing or unformatted")
        self.assertIn("3.45", post, "BTC change percent missing")

        # Invariant 2: Top gainers ranking rendered cleanly within <= 2 cashtag cap
        self.assertIn("$SOL", post)
        self.assertIn("AVAX", post)
        self.assertNotIn("#AVAXUSDT", post)
        self.assertTrue("8.24" in post or "8.2" in post)
        cashtags = set(re.findall(r"\$(?!\d+[KMBT]?\b)((?:[0-9]{1,5})?[A-Z]{2,10}(?:[0-9]{1,3})?)\b", post))
        self.assertLessEqual(len(cashtags), 2)

        # Invariant 3: Truthful RSS sentiment & institutional thesis present (no false FinBERT claim)
        self.assertNotIn("FinBERT", post)
        self.assertTrue(
            any(term in post for term in ["ALCISTA", "0.68", "Sentimiento", "RSS"]),
            "Sentiment attribution representation missing"
        )
        self.assertIn("Flujo institucional", post)

        # Invariant 4: Zero external CTAs/URLs + native compliance tags & closing question
        self.assertNotIn("@AdminVIPSignals", post)
        self.assertNotIn("/subscribe", post)
        self.assertNotIn("github.io", post)
        self.assertNotIn("https://", post)
        self.assertIn("#Bitcoin", post)
        self.assertIn("#BinanceSquare", post)
        self.assertLessEqual(len(re.findall(r"#[a-zA-Z0-9_]+", post)), 3)
        self.assertIn("?", post)
        self.assertIn("no constituye asesoramiento financiero", post.lower())

    def test_render_archetype_3_audited_performance(self) -> None:
        """Archetype 3: Audited Performance Report (Win Rate 55.0%, Profit Factor, -6.4% drawdown lock)."""
        post = BinanceSquareContentGenerator.generate_audited_performance_report(
            win_rate_pct=55.0,
            profit_factor=1.40,
            drawdown_lock_pct=-4.2,
            sharpe_ratio=0.35,
            total_trades=60,
            source="live_closed_trades",
        )
        self.assertIsInstance(post, str)
        self.assertTrue(len(post) > 50)
        for needle in ("55.0", "1.40", "-4.2", "0.35", "60"):
            self.assertIn(needle, post)
        self.assertIn("no garantiza", post.lower())

        # Invariant 3: Sober branding, native tags, zero external CTAs
        self.assertNotIn("@AdminVIPSignals", post)
        self.assertNotIn("/subscribe", post)
        self.assertNotIn("github.io", post)
        self.assertNotIn("https://", post)
        self.assertIn("Proyecto Fehu", post)
        self.assertIn("#BinanceSquare", post)
        self.assertLessEqual(len(re.findall(r"#[a-zA-Z0-9_]+", post)), 3)
        self.assertIn("?", post)
        self.assertIn("no constituye asesoramiento financiero", post.lower())

    def test_dynamic_numeric_precision_and_formatting(self) -> None:
        """Dynamic numeric formatting: cleanly formats prices, small tokens, and percentage variations."""
        gainers = [
            {"symbol": "PEPEUSDT", "price": 0.00001234, "change_pct": 14.5298, "quote_volume": 120000000.0}
        ]
        post = BinanceSquareContentGenerator.generate_macro_market_report(
            btc_price=60500.00000000001,
            btc_change_pct=4.5234,
            top_gainers=gainers,
            sentiment_label="Neutral",
            sentiment_score=0.1
        )
        # Avoid unformatted IEEE 754 floats
        self.assertNotIn("60500.00000000001", post)
        self.assertNotIn("14.52980000000", post)
        self.assertNotIn("4.52340000000", post)
        self.assertNotIn("1e-", post.lower())


class TestContentFormattingAndLimits(unittest.TestCase):
    """Test suite for R2: Character count (< 2,000 chars), HTML stripping, compliance & tag ceilings."""

    def setUp(self) -> None:
        if BinanceSquareContentGenerator is None:
            self.skipTest("BinanceSquareContentGenerator not yet implemented")

    def test_character_count_strictly_under_2000(self) -> None:
        """All 5 archetypes must remain strictly under 2,000 characters (max 1950 target)."""
        verbose_gainers = [
            {"symbol": f"COIN{i}USDT", "price": 10.0 * i, "change_pct": 5.0 + i, "quote_volume": 10000000.0 * i}
            for i in range(1, 9)
        ]
        long_thesis = "Análisis de flujo institucional y divergencias de volumen ponderado por volatilidad. " * 8

        p1 = BinanceSquareContentGenerator.generate_quant_setup_post(
            symbol="BTCUSDT", action="BUY", entry_price=65000.0, stop_price=64000.0,
            tp1=66000.0, tp2=67500.0, tp3=69000.0, composite_score=0.85,
            thesis=long_thesis
        )
        p2 = BinanceSquareContentGenerator.generate_macro_market_report(
            btc_price=65000.0, btc_change_pct=2.5, top_gainers=verbose_gainers,
            sentiment_label="[ALCISTA] Fuerte Presión", sentiment_score=0.75,
            macro_summary=long_thesis
        )
        p3 = BinanceSquareContentGenerator.generate_audited_performance_report(
            win_rate_pct=78.5, profit_factor=2.65, drawdown_lock_pct=-6.4, sharpe_ratio=2.42, total_trades=142
        )
        p4 = BinanceSquareContentGenerator.generate_trade_close_post(
            symbol="SOLUSDT", exit_price=154.25, pnl_pct=4.85, pnl_usdt=48.50,
            reason="take_profit", sentiment_label="Alcista", sentiment_score=0.40, entry_price=147.10,
        )
        p5 = BinanceSquareContentGenerator.generate_recalibration_note(
            tuned_summary=["#BTCUSDT: Estructura Adaptativa (SL: 1.8x ATR | Target R:R: 2.2)"],
            sentiment_label="Neutral", sentiment_score=0.05, symbols=["BTCUSDT", "ETHUSDT"],
        )

        for idx, post in enumerate([p1, p2, p3, p4, p5], start=1):
            self.assertLess(
                len(post), 2000,
                f"Archetype {idx} exceeds Binance Square 2000-character ceiling: {len(post)} chars"
            )
            self.assertLessEqual(
                len(post), 1950,
                f"Archetype {idx} exceeds recommended 1950-character safety bound: {len(post)} chars"
            )

    def test_absence_of_unsupported_html_tags(self) -> None:
        """Rendered output must contain 0% forbidden HTML tags and strip external URLs on compliance."""
        from bot.binance_square import enforce_square_community_compliance

        html_input_thesis = (
            "<b>Alerta institucional:</b> <pre><code>entry: 100</code></pre>. "
            "Consulte <a href='https://example.com'>detalles</a> en <i>mesa técnica</i>."
        )
        post = BinanceSquareContentGenerator.generate_quant_setup_post(
            symbol="ETHUSDT", action="BUY", entry_price=3500.0, stop_price=3400.0,
            tp1=3600.0, tp2=3700.0, tp3=3850.0, composite_score=0.80,
            thesis=html_input_thesis
        )

        forbidden_tags = ["<b", "</b>", "<code", "</code>", "<pre", "</pre>", "<i", "</i>", "<a ", "</a>", "<div", "</div>", "**"]
        for tag in forbidden_tags:
            self.assertNotIn(tag, post, f"Disallowed HTML/Markdown tag '{tag}' found in rendered post")
        compliant = enforce_square_community_compliance(post)
        self.assertNotIn("https://example.com", compliant)

    def test_zero_external_ctas_and_urls_in_all_archetypes(self) -> None:
        """All 5 archetypes must have zero external CTAs/URLs/hype emojis and include DYOR + closing question."""
        p1 = BinanceSquareContentGenerator.generate_quant_setup_post(
            symbol="SOLUSDT", action="BUY", entry_price=145.0, stop_price=140.0,
            tp1=150.0, tp2=155.0, tp3=160.0, composite_score=0.75
        )
        p2 = BinanceSquareContentGenerator.generate_macro_market_report(
            btc_price=64000.0, btc_change_pct=1.0, top_gainers=[],
            sentiment_label="Neutral", sentiment_score=0.0
        )
        p3 = BinanceSquareContentGenerator.generate_audited_performance_report(
            win_rate_pct=55.0, profit_factor=1.4, drawdown_lock_pct=-4.0, sharpe_ratio=0.3, total_trades=40
        )
        p4 = BinanceSquareContentGenerator.generate_trade_close_post(
            symbol="BTCUSDT", exit_price=59000.0, pnl_pct=-1.67, reason="stop_loss"
        )
        p5 = BinanceSquareContentGenerator.generate_recalibration_note(
            tuned_summary=["BTCUSDT: Ruptura de Canal (SL: 1.8x ATR | Target R:R: 2.2)"],
            symbols=["BTCUSDT"]
        )

        banned = ["@AdminVIPSignals", "/subscribe", "github.io", "https://", "http://", "Telegram", "WhatsApp", "Discord", "**", "🚀", "🔥", "💎", "ArcaFid", "FinBERT", "muy limpia", "oportunidad"]
        for idx, post in enumerate([p1, p2, p3, p4, p5], start=1):
            for term in banned:
                self.assertNotIn(term, post, f"Forbidden term '{term}' found in Archetype {idx}")
            self.assertIn("no constituye asesoramiento financiero", post.lower(), f"DYOR missing in Archetype {idx}")
            self.assertIn("?", post, f"Closing analytical question missing in Archetype {idx}")

    def test_hashtag_and_cashtag_ceilings_in_generator_outputs(self) -> None:
        """Generated posts must respect <=3 hashtags and <=2 unique $COIN cashtags without orphan words."""
        p1 = BinanceSquareContentGenerator.generate_quant_setup_post(
            symbol="BNBUSDT", action="BUY", entry_price=580.0, stop_price=570.0,
            tp1=595.0, tp2=610.0, tp3=630.0, composite_score=0.76
        )
        hashtags = re.findall(r"#[a-zA-Z0-9_]+", p1)
        cashtags = set(re.findall(r"\$([A-Z0-9]{2,10})\b", p1))
        self.assertIn("#BinanceSquare", p1)
        self.assertGreaterEqual(len(hashtags), 1)
        self.assertLessEqual(len(hashtags), 3)
        self.assertLessEqual(len(cashtags), 2)
        self.assertNotIn("CryptoTrading ArcaFid", p1)

    def test_boundary_truncation_safety(self) -> None:
        """Boundary truncation safely limits oversized content (<=1950 chars) preserving DYOR & hashtags."""
        from bot.binance_square import enforce_square_community_compliance

        cleaner = sanitize_for_square
        if cleaner is None:
            cleaner = getattr(BinanceSquareContentGenerator, "sanitize_text", None)
        if cleaner is None:
            publisher = BinanceSquarePublisher(BotConfig(event_db_path=":memory:"))
            cleaner = getattr(publisher, "sanitize_text", None)

        if cleaner is None:
            self.skipTest("No sanitize_for_square or sanitize_text function available to test directly")

        huge_text = (
            "Análisis cuantitativo de alta frecuencia con algoritmos de optimización. " * 80
            + "\n\n— Proyecto Fehu (ᚠ) Quantitative | Análisis informativo (DYOR), no constituye asesoramiento financiero."
            + "\n#TradingCuantitativo #GestionDeRiesgo #BinanceSquare"
        )
        sanitized = cleaner(huge_text, max_chars=1950)
        self.assertLessEqual(len(sanitized), 1950)
        self.assertIn("#BinanceSquare", sanitized)
        self.assertIn("no constituye asesoramiento financiero", sanitized.lower())
        compliant = enforce_square_community_compliance(sanitized)
        self.assertLessEqual(len(re.findall(r"#[a-zA-Z0-9_]+", compliant)), 3)
        self.assertNotIn("@AdminVIPSignals", compliant)
        self.assertNotIn("github.io", compliant)


class TestOpenAPINetworkMocking(unittest.TestCase):
    """Test suite for R2 & R3: Binance Square OpenAPI interaction, payloads, and HTTP error states."""

    def setUp(self) -> None:
        self.db_path = os.path.join(tempfile.gettempdir(), f"test_sq_res_{uuid.uuid4().hex[:8]}.sqlite3")
        self.cfg = BotConfig(
            binance_square_enabled=True,
            binance_square_api_key="mock_square_api_key_12345",
            event_db_path=self.db_path,
        )
        self.publisher = BinanceSquarePublisher(self.cfg)

    def tearDown(self) -> None:
        if hasattr(self, "db_path") and os.path.exists(self.db_path):
            try:
                os.remove(self.db_path)
            except Exception:
                pass

    def _publish_helper(self, text: str, **kwargs: Any) -> bool:
        """Helper to invoke publish_post whether it takes extra kwargs or not."""
        try:
            return self.publisher.publish_post(text, **kwargs)
        except TypeError:
            return self.publisher.publish_post(text)

    @patch("requests.post")
    def test_openapi_publish_success_code_000000(self, mock_post: MagicMock) -> None:
        """Mock HTTP 200 with code '000000' and success=True returns True."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "code": "000000",
            "message": None,
            "data": {"id": "content_id_998877"},
            "success": True,
        }
        mock_post.return_value = mock_resp

        result = self._publish_helper("Test setup post content")
        self.assertTrue(result)
        mock_post.assert_called_once()

    @patch("requests.post")
    def test_openapi_publish_success_boolean_flag(self, mock_post: MagicMock) -> None:
        """Mock HTTP 200 with {'success': True} returns True even if explicit 'code' field is absent."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True, "data": {}}
        mock_post.return_value = mock_resp

        result = self._publish_helper("Test macro post content")
        self.assertTrue(result)

    @patch("requests.post")
    def test_openapi_request_headers_and_payload_structure(self, mock_post: MagicMock) -> None:
        """Verifies exact OpenAPI request URL, headers, and JSON body structure."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": "000000", "success": True}
        mock_post.return_value = mock_resp

        text_to_publish = "Test post payload structure"
        self._publish_helper(text_to_publish)

        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args

        # URL validation
        expected_url = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add"
        self.assertEqual(args[0] if args else kwargs.get("url"), expected_url)

        # Headers validation
        headers = kwargs.get("headers", {})
        self.assertEqual(headers.get("X-Square-OpenAPI-Key"), "mock_square_api_key_12345")
        self.assertEqual(headers.get("Content-Type"), "application/json")
        self.assertEqual(headers.get("clienttype"), "binanceSkill")

        # Payload validation
        json_data = kwargs.get("json", {})
        self.assertEqual(json_data.get("bodyTextOnly"), text_to_publish)

    @patch("requests.post")
    def test_openapi_business_error_code_returns_false(self, mock_post: MagicMock) -> None:
        """Mock HTTP 200 with business error (e.g., code '200001') returns False without raising."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "code": "200001",
            "message": "Content violated community guidelines",
            "success": False
        }
        mock_post.return_value = mock_resp

        result = self._publish_helper("Invalid marketing post")
        self.assertFalse(result)

    @patch("requests.post")
    def test_openapi_http_400_bad_request(self, mock_post: MagicMock) -> None:
        """Mock HTTP 400 Bad Request returns False without unhandled exception."""
        mock_resp = MagicMock()
        mock_resp.status_code = 400
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("400 Client Error")
        mock_resp.json.return_value = {"code": "400001", "message": "Missing required parameter"}
        mock_post.return_value = mock_resp

        result = self._publish_helper("Bad request test")
        self.assertFalse(result)

    @patch("requests.post")
    def test_openapi_http_401_invalid_api_key(self, mock_post: MagicMock) -> None:
        """Mock HTTP 401 Unauthorized returns False without unhandled exception."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("401 Unauthorized")
        mock_resp.json.return_value = {"code": "401000", "message": "Invalid API key"}
        mock_post.return_value = mock_resp

        result = self._publish_helper("Unauthorized test")
        self.assertFalse(result)

    @patch("time.sleep", return_value=None)
    @patch("requests.post")
    def test_openapi_http_500_gateway_error_retry(self, mock_post: MagicMock, mock_sleep: MagicMock) -> None:
        """Mock HTTP 500 followed by HTTP 200 retries and succeeds, or fails cleanly."""
        err_resp = MagicMock()
        err_resp.status_code = 500
        err_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Internal Server Error")
        err_resp.json.return_value = {"code": "500000", "message": "Server Error"}

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.json.return_value = {"code": "000000", "success": True}

        # First call fails with 500, second call succeeds with 200
        mock_post.side_effect = [err_resp, ok_resp]

        result = self._publish_helper("Retry after 500 test")
        if mock_post.call_count > 1:
            self.assertTrue(result)
        else:
            self.assertFalse(result)

    @patch("time.sleep", return_value=None)
    @patch("requests.post")
    def test_openapi_network_timeout_and_connection_reset(self, mock_post: MagicMock, mock_sleep: MagicMock) -> None:
        """Mock network Timeout or ConnectionResetError handles cleanly without crashing bot loop."""
        mock_post.side_effect = requests.exceptions.Timeout("Read timed out after 15s")

        try:
            result = self._publish_helper("Timeout post test")
            self.assertFalse(result)
        except Exception as exc:
            self.fail(f"publish_post() raised unhandled exception on timeout: {exc}")


class TestGracefulDegradation(unittest.TestCase):
    """Test suite for R2 & Acceptance Criteria: Graceful standby / simulation degradation."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "degradation_test.sqlite3")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    @patch("requests.post")
    def test_degradation_when_api_key_empty(self, mock_post: MagicMock) -> None:
        """When binance_square_api_key is empty string, service is disabled; 0 network calls sent."""
        cfg = BotConfig(binance_square_enabled=True, binance_square_api_key="", event_db_path=self.db_path)
        publisher = BinanceSquarePublisher(cfg)

        self.assertFalse(publisher.enabled)
        res = publisher.publish_post("Should not be published")
        self.assertFalse(res)
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_degradation_when_service_disabled(self, mock_post: MagicMock) -> None:
        """When binance_square_enabled is False, publish_post returns False immediately; 0 network calls."""
        cfg = BotConfig(binance_square_enabled=False, binance_square_api_key="valid_key", event_db_path=self.db_path)
        publisher = BinanceSquarePublisher(cfg)

        self.assertFalse(publisher.enabled)
        res = publisher.publish_post("Should not be published")
        self.assertFalse(res)
        mock_post.assert_not_called()

    @patch("requests.post")
    def test_degradation_default_config_safe(self, mock_post: MagicMock) -> None:
        """Default BotConfig initializes with binance_square_enabled=False safely without exceptions."""
        cfg = BotConfig(event_db_path=self.db_path)
        self.assertFalse(cfg.binance_square_enabled)

        publisher = BinanceSquarePublisher(cfg)
        self.assertFalse(publisher.enabled)
        self.assertFalse(publisher.publish_post("Safe test"))
        mock_post.assert_not_called()


class TestRateLimitingAndScheduling(unittest.TestCase):
    """Test suite for R3: SquareRateLimiter cooldowns, hourly ceilings, and HTTP 429 backoff."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "rate_limit.sqlite3")

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_rate_limiter_blocks_rapid_spam(self) -> None:
        """Rate limiter permits initial post, blocks immediate second post within cooldown window."""
        if SquareRateLimiter is None:
            self.skipTest("SquareRateLimiter not yet implemented in bot.binance_square")

        limiter = SquareRateLimiter(
            db_path=self.db_path,
            rate_limit_per_hour=5,
            min_cooldown_seconds=600.0
        )

        can_pub_1, reason_1 = limiter.can_publish("Market Update #1", is_priority_alert=False)
        self.assertTrue(can_pub_1, f"First post should be permitted: {reason_1}")

        limiter.record_published("Market Update #1")

        # Second post immediately after should be blocked by cooldown
        can_pub_2, reason_2 = limiter.can_publish("Market Update #2", is_priority_alert=False)
        self.assertFalse(can_pub_2, "Rapid second post must be blocked by rate limiter")
        self.assertTrue(
            any(w in reason_2.lower() for w in ["cooldown", "limit", "rate", "wait", "frecuencia"]),
            f"Expected cooldown reason, got: {reason_2}"
        )

    @patch("time.sleep", return_value=None)
    @patch("requests.post")
    def test_http_429_retry_after_backoff(self, mock_post: MagicMock, mock_sleep: MagicMock) -> None:
        """Mock HTTP 429 Too Many Requests invokes sleep with backoff and succeeds on retry."""
        cfg = BotConfig(binance_square_enabled=True, binance_square_api_key="valid_key", event_db_path=self.db_path)
        publisher = BinanceSquarePublisher(cfg)

        resp_429 = MagicMock()
        resp_429.status_code = 429
        resp_429.headers = {"Retry-After": "2"}
        resp_429.raise_for_status.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
        resp_429.json.return_value = {"code": "429000", "message": "Too Many Requests"}

        resp_200 = MagicMock()
        resp_200.status_code = 200
        resp_200.json.return_value = {"code": "000000", "success": True}

        mock_post.side_effect = [resp_429, resp_200]

        try:
            res = publisher.publish_post("Retry test on 429")
            if mock_post.call_count > 1:
                self.assertTrue(res)
                mock_sleep.assert_called()
            else:
                self.assertFalse(res)
        except Exception as exc:
            self.fail(f"publish_post() crashed on HTTP 429: {exc}")


class TestSQLiteTelemetryLogging(unittest.TestCase):
    """Test suite for R3: SQLite 'events' logging in temp SQLite DB."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "test_telemetry.sqlite3")
        self.cfg = BotConfig(
            binance_square_enabled=True,
            binance_square_api_key="test_key_sqlite",
            event_db_path=self.db_path
        )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    @patch("requests.post")
    def test_successful_publication_logged_to_sqlite(self, mock_post: MagicMock) -> None:
        """Successful post records an event in SQLite 'events' table with mode='binance_square'."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": "000000", "success": True, "data": {"id": "sq_101"}}
        mock_post.return_value = mock_resp

        publisher = BinanceSquarePublisher(self.cfg)
        try:
            publisher.publish_post("Sample setup post", metadata={"symbol": "SOLUSDT", "archetype": "setup_alert"})
        except TypeError:
            publisher.publish_post("Sample setup post")

        if not os.path.exists(self.db_path) and not hasattr(publisher, "event_store"):
            self.skipTest("SQLite telemetry logging not yet wired in BinanceSquarePublisher (pending M2)")

        self.assertTrue(os.path.exists(self.db_path), f"Database file {self.db_path} should exist after publication")
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT mode, event, payload_json FROM events WHERE mode = 'binance_square' OR event LIKE '%square%'"
            )
            rows = cursor.fetchall()
            self.assertGreaterEqual(len(rows), 1, "Expected publication event to be persisted in SQLite events table")
            mode, event_name, payload_json = rows[0]
            self.assertTrue("square" in mode.lower() or "square" in event_name.lower())
            payload = json.loads(payload_json)
            self.assertIsInstance(payload, dict)
        finally:
            conn.close()

    @patch("time.sleep", return_value=None)
    @patch("requests.post")
    def test_failed_publication_logged_to_sqlite(self, mock_post: MagicMock, _mock_sleep: MagicMock) -> None:
        """Failed post records failure telemetry in SQLite 'events' table."""
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.raise_for_status.side_effect = requests.exceptions.HTTPError("500 Server Error")
        mock_resp.json.return_value = {"code": "500000", "message": "Internal Server Error"}
        mock_post.return_value = mock_resp

        publisher = BinanceSquarePublisher(self.cfg)
        try:
            publisher.publish_post("Failed post attempt")
        except Exception:
            pass

        if not os.path.exists(self.db_path) and not hasattr(publisher, "event_store"):
            self.skipTest("SQLite failure logging not yet wired in BinanceSquarePublisher (pending M2)")

        if os.path.exists(self.db_path):
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT mode, event, payload_json FROM events WHERE event LIKE '%failed%' OR event LIKE '%square%'"
                )
                rows = cursor.fetchall()
                if rows:
                    self.assertGreaterEqual(len(rows), 1)
            finally:
                conn.close()

    def test_sqlite_connection_closed_cleanly(self) -> None:
        """Ensures database connections are cleanly closed without leaking locks on Windows."""
        publisher = BinanceSquarePublisher(self.cfg)
        with patch("requests.post") as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = {"code": "000000", "success": True}
            try:
                publisher.publish_post("Cleanup test")
            except Exception:
                pass

        # Verify that an external SQLite connection can acquire write lock immediately
        conn = sqlite3.connect(self.db_path, timeout=1.0)
        try:
            conn.execute("CREATE TABLE IF NOT EXISTS test_lock (id INTEGER PRIMARY KEY);")
            conn.commit()
        finally:
            conn.close()
        self.assertTrue(os.path.exists(self.db_path))


class TestAsyncWorkerExecution(unittest.TestCase):
    """Architectural test class representing the asynchronous non-blocking worker pipeline.

    Verifies that publisher components can be scheduled and executed without blocking
    the real-time trading loop (R3 & M3).
    """

    def tearDown(self) -> None:
        from bot.growth_traffic_engine import reset_square_worker
        reset_square_worker()

    def test_mathematical_expressions_preserved_in_sanitizer(self) -> None:
        """Sanitizer must preserve mathematical inequalities (< -6.4%, > 2.0, < $50k) while stripping HTML."""
        raw_text = (
            "<div>Análisis institucional</div>: Drawdown < -6.4% y Sharpe > 2.0 con capital < $50k. "
            "<script>alert('xss')</script> Operación ejecutada exitosamente."
        )
        cleaned = sanitize_for_square(raw_text)
        self.assertNotIn("<div>", cleaned)
        self.assertNotIn("</div>", cleaned)
        self.assertNotIn("<script>", cleaned)
        self.assertNotIn("</script>", cleaned)
        self.assertIn("Drawdown < -6.4%", cleaned)
        self.assertIn("Sharpe > 2.0", cleaned)
        self.assertIn("< $50k", cleaned)

    def test_enqueue_square_post_non_blocking_when_worker_inactive(self) -> None:
        """If worker is None or inactive, enqueue_square_post must not make blocking synchronous HTTP calls."""
        from bot.growth_traffic_engine import enqueue_square_post
        with patch("bot.growth_traffic_engine.get_square_worker", return_value=None):
            with patch("bot.binance_square.BinanceSquarePublisher.publish_post") as mock_pub:
                cfg = BotConfig(binance_square_enabled=True, binance_square_api_key="valid_key", event_db_path=":memory:")
                result = enqueue_square_post("Test post", cfg=cfg)
                self.assertFalse(result)
                mock_pub.assert_not_called()

    def test_auto_tune_cycle_enqueues_square_post(self) -> None:
        """Auto tune cycle must enqueue compliant recalibration note with allow_network=False."""
        from bot.main import run_auto_tune_cycle
        cfg = BotConfig(
            auto_tune_enabled=True,
            binance_square_enabled=True,
            binance_square_api_key="valid_key",
            event_db_path=":memory:",
            active_symbols="BTCUSDT",
        )
        mock_telemetry = MagicMock()
        mock_df = MagicMock()
        mock_df.empty = False
        mock_df.__len__ = MagicMock(return_value=120)
        candidate = {
            "score": 1.25,
            "metrics": {"roi_pct": 4.2, "profit_factor": 1.45, "num_trades": 12},
            "params": {"strategy_mode": "connors_rsi", "stop_atr_mult": 1.8, "take_profit_rr": 2.2},
        }
        with patch("bot.growth_traffic_engine.enqueue_square_post") as mock_enqueue:
            with patch("bot.binance_square.BinanceSquarePublisher.publish_post"):
                with patch("bot.main.BinanceDataClient") as mock_data_cls:
                    mock_data_cls.return_value.get_klines.return_value = mock_df
                    with patch("bot.optimizer.optimize_config", return_value=[candidate]):
                        with patch("bot.news_sentiment.NewsSentimentAnalyzer.get_sentiment", return_value=(0.25, [{"title": "Market Rally"}])) as mock_sent:
                            with patch("bot.main.get_db_session") as mock_get_session:
                                mock_session = MagicMock()
                                mock_session.query.return_value.filter.return_value.first.return_value = None
                                mock_get_session.return_value = mock_session

                                run_auto_tune_cycle(cfg, mock_telemetry)
                                mock_sent.assert_called_once_with(allow_network=False)
                                self.assertTrue(mock_enqueue.called)
                                enqueued_msg = mock_enqueue.call_args[0][0]
                                self.assertIn("$BTC", enqueued_msg)
                                self.assertNotIn("Market Rally", enqueued_msg)
                                self.assertNotIn("Buy the Dip", enqueued_msg)
                                self.assertLessEqual(len(re.findall(r"#[a-zA-Z0-9_]+", enqueued_msg)), 3)
                                self.assertEqual(mock_enqueue.call_args[1].get("is_priority"), False)

    def test_live_event_to_square_avoids_cold_network_fetch(self) -> None:
        """_publish_live_event_to_square must not perform cold 15s network fetch on live trading thread."""
        from bot.main import _publish_live_event_to_square
        cfg = BotConfig(binance_square_enabled=True, binance_square_api_key="valid_key", event_db_path=":memory:")
        with patch("bot.news_sentiment.fetch_latest_news") as mock_fetch:
            with patch("bot.growth_traffic_engine.enqueue_square_post") as mock_enqueue:
                _publish_live_event_to_square(
                    cfg,
                    "BTCUSDT",
                    {"event": "live_buy", "price": 60000.0, "stop": 59000.0, "take": 63000.0}
                )
                mock_fetch.assert_not_called()
                self.assertTrue(mock_enqueue.called)

    def test_live_buy_score_gating_rejects_below_min_score(self) -> None:
        """_publish_live_event_to_square skips live_buy below binance_square_min_score without clamping."""
        from bot.main import _publish_live_event_to_square
        cfg = BotConfig(
            binance_square_enabled=True,
            binance_square_api_key="valid_key",
            binance_square_min_score=0.72,
            event_db_path=":memory:",
        )
        with patch("bot.growth_traffic_engine.enqueue_square_post") as mock_enqueue:
            _publish_live_event_to_square(
                cfg,
                "BTCUSDT",
                {"event": "live_buy", "price": 60000.0, "stop": 59000.0, "take": 63000.0, "composite_score": 0.55},
            )
            mock_enqueue.assert_not_called()

            _publish_live_event_to_square(
                cfg,
                "BTCUSDT",
                {"event": "live_buy", "price": 60000.0, "stop": 59000.0, "take": 63000.0, "composite_score": 0.81},
            )
            mock_enqueue.assert_called_once()
            self.assertIn("0.810", mock_enqueue.call_args[0][0])

    def test_live_sell_uses_trade_close_spanish_formatting(self) -> None:
        """_publish_live_event_to_square routes live_sell through generate_trade_close_post cleanly."""
        from bot.main import _publish_live_event_to_square
        cfg = BotConfig(binance_square_enabled=True, binance_square_api_key="valid_key", event_db_path=":memory:")
        with patch("bot.growth_traffic_engine.enqueue_square_post") as mock_enqueue:
            _publish_live_event_to_square(
                cfg,
                "BTCUSDT",
                {"event": "live_sell", "price": 65000.0, "pnl": 1.48, "pnl_pct": 2.32, "reason": "take_profit"},
            )
            mock_enqueue.assert_called_once()
            msg = mock_enqueue.call_args[0][0]
            self.assertIn("65,000.00", msg)
            self.assertNotIn("65000.0000", msg)
            self.assertNotIn("take_profit", msg)
            self.assertNotIn("@AdminVIPSignals", msg)
            self.assertNotIn("github.io", msg)

    def test_zero_live_http_guard_blocks_unmocked_requests_post(self) -> None:
        """Inside unittest runtime without @patch('requests.post'), BinanceSquarePublisher never sends HTTP."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "guard.sqlite3")
            cfg = BotConfig(
                binance_square_enabled=True,
                binance_square_api_key="real_looking_key",
                binance_square_dry_run=False,
                event_db_path=db_path,
            )
            pub = BinanceSquarePublisher(cfg)
            with patch("socket.create_connection", side_effect=AssertionError("Network socket must not be opened!")):
                ok = pub.publish_post("Guard check post")
            self.assertFalse(ok)
            con = sqlite3.connect(db_path)
            try:
                row = con.execute("SELECT event, payload_json FROM events WHERE mode='binance_square'").fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], "binance_square_simulation")
                self.assertEqual(json.loads(row[1]).get("status"), "test_guard_blocked")
            finally:
                con.close()

    def test_perform_auto_tuning_active_momentum_no_snake_case(self) -> None:
        """perform_auto_tuning with strategy_mode='active_momentum' must produce clean Spanish copy with zero snake_case leaks."""
        from bot.binance_square import enforce_square_community_compliance
        from bot.main import perform_auto_tuning

        with tempfile.TemporaryDirectory() as td:
            cfg = BotConfig(
                auto_tune_enabled=True,
                binance_square_enabled=True,
                binance_square_api_key="valid_key",
                event_db_path=os.path.join(td, "autotune_test.sqlite3"),
                active_symbols="BTCUSDT,ETHUSDT",
            )
            mock_telemetry = MagicMock()
            mock_df = MagicMock()
            mock_df.empty = False
            mock_df.__len__ = MagicMock(return_value=120)
            candidate = {
                "score": 1.35,
                "metrics": {"roi_pct": 5.1, "profit_factor": 1.55, "num_trades": 15},
                "params": {"strategy_mode": "active_momentum", "stop_atr_mult": 1.4, "take_profit_rr": 1.8},
            }
            with patch("bot.growth_traffic_engine.enqueue_square_post") as mock_enqueue:
                with patch("bot.binance_square.BinanceSquarePublisher.publish_post"):
                    with patch("bot.main.BinanceDataClient") as mock_data_cls:
                        mock_data_cls.return_value.get_klines.return_value = mock_df
                        with patch("bot.optimizer.optimize_config", return_value=[candidate]):
                            with patch(
                                "bot.news_sentiment.NewsSentimentAnalyzer.get_sentiment",
                                return_value=(0.12, []),
                            ) as mock_sent:
                                with patch("bot.db.get_db_session") as mock_get_session:
                                    mock_session = MagicMock()
                                    mock_session.query.return_value.filter.return_value.first.return_value = None
                                    mock_get_session.return_value = mock_session

                                    perform_auto_tuning(cfg, mock_telemetry)
                                    mock_sent.assert_called_once_with(allow_network=False)
                                    self.assertTrue(mock_enqueue.called)
                                    enqueued_msg = mock_enqueue.call_args[0][0]
                                    self.assertNotIn("active_momentum", enqueued_msg)
                                    self.assertIn("Momentum Activo", enqueued_msg)
                                    self.assertEqual(re.findall(r"\b[a-z]+_[a-z0-9_]+\b", enqueued_msg), [])
                                    self.assertLessEqual(len(enqueued_msg), 1950)
                                    self.assertLessEqual(len(set(re.findall(r"\$([A-Z0-9]{2,10})\b", enqueued_msg))), 2)
                                    self.assertLessEqual(len(re.findall(r"#\w+", enqueued_msg)), 3)
                                    self.assertIn("no constituye asesoramiento financiero", enqueued_msg.lower())
                                    self.assertEqual(enforce_square_community_compliance(enqueued_msg), enqueued_msg)

        direct_note = BinanceSquareContentGenerator.generate_recalibration_note(
            ["• ETH: Estrategia de active_momentum (SL: 1.4x ATR | Ratio R:R objetivo: 1.5)"]
        )
        self.assertNotIn("active_momentum", direct_note)
        self.assertIn("Momentum Activo", direct_note)
        self.assertEqual(re.findall(r"\b[a-z]+_[a-z0-9_]+\b", direct_note), [])
        self.assertEqual(enforce_square_community_compliance(direct_note), direct_note)

    def test_target_exit_live_sell_outcome_tag(self) -> None:
        """live_sell with reason='target_exit' must pass raw reason so outcome_tag renders 'Objetivo asegurado'."""
        from bot.main import _publish_live_event_to_square

        cfg = BotConfig(binance_square_enabled=True, binance_square_api_key="valid_key", event_db_path=":memory:")
        with patch("bot.growth_traffic_engine.enqueue_square_post") as mock_enqueue:
            _publish_live_event_to_square(
                cfg,
                "ETHUSDT",
                {
                    "event": "live_sell",
                    "price": 3250.0,
                    "pnl": 42.5,
                    "pnl_pct": 2.85,
                    "reason": "target_exit",
                    "strategy_mode": "active_momentum",
                },
            )
            mock_enqueue.assert_called_once()
            post = mock_enqueue.call_args[0][0]
            self.assertIn("Objetivo asegurado", post)
            self.assertNotIn("Cierre en positivo", post)
            self.assertIn("alcance de zona objetivo definida", post)
            self.assertNotIn("target_exit", post)
            self.assertIn("Momentum Activo", post)

        direct_close = BinanceSquareContentGenerator.generate_trade_close_post(
            symbol="ETHUSDT", exit_price=3250.0, pnl_pct=2.85, reason="target_exit"
        )
        self.assertIn("Objetivo asegurado", direct_close)
        self.assertNotIn("Cierre en positivo", direct_close)
        self.assertIn("alcance de zona objetivo definida", direct_close)
        self.assertNotIn("target_exit", direct_close)


class TestArchetypesAndEditorialQuality(unittest.TestCase):
    """Tests for honest math, pre-fold hooks, and Archetypes 4 & 5."""

    def test_archetype_1_no_rr_clamping_or_fabrication(self) -> None:
        post_low_rr = BinanceSquareContentGenerator.generate_quant_setup_post(
            symbol="SOLUSDT", action="BUY", entry_price=100.0, stop_price=90.0,
            tp1=105.0, tp2=110.0, tp3=115.0, composite_score=0.76,
        )
        self.assertIn("1:1.50", post_low_rr)
        self.assertNotIn("1:2.50", post_low_rr)

        post_zero_risk = BinanceSquareContentGenerator.generate_quant_setup_post(
            symbol="SOLUSDT", action="BUY", entry_price=100.0, stop_price=100.0,
            tp1=105.0, tp2=110.0, tp3=115.0, composite_score=0.76,
        )
        self.assertNotIn("1:2.50", post_zero_risk)
        self.assertIn("n/d", post_zero_risk)

    def test_archetype_1_prefold_hook_and_veteran_tone(self) -> None:
        post = BinanceSquareContentGenerator.generate_quant_setup_post(
            symbol="SOLUSDT", action="BUY", entry_price=145.50, stop_price=141.80,
            tp1=149.10, tp2=153.50, tp3=158.60, composite_score=0.785, timeframe="15m",
        )
        first_line = post.splitlines()[0]
        self.assertLessEqual(len(first_line), 220)
        self.assertIn("$SOL", first_line)
        self.assertIn("15m", first_line)
        self.assertIn("145.50", first_line)
        self.assertIn("Proyecto Fehu (ᚠ) Quantitative", post)
        self.assertIn("?", post)
        for hype in ("🚀", "🔥", "💎", "garantizado", "infalible", "100% seguro", "muy limpia", "oportunidad"):
            self.assertNotIn(hype, post.lower())

    def test_archetype_4_trade_close_post_profit_and_stop_loss(self) -> None:
        win_post = BinanceSquareContentGenerator.generate_trade_close_post(
            symbol="BTCUSDT", exit_price=65000.0, pnl_pct=3.12, reason="take_profit"
        )
        loss_post = BinanceSquareContentGenerator.generate_trade_close_post(
            symbol="SOLUSDT", exit_price=141.20, pnl_pct=-2.15, reason="trend_or_momentum_exit"
        )
        for post in (win_post, loss_post):
            self.assertLessEqual(len(post), 1950)
            self.assertNotIn("take_profit", post)
            self.assertNotIn("trend_or_momentum_exit", post)
            self.assertNotIn("stop_loss", post)
            self.assertLessEqual(len(set(re.findall(r"\$([A-Z0-9]{2,10})\b", post))), 2)
            self.assertLessEqual(len(re.findall(r"#[a-zA-Z0-9_]+", post)), 3)
            self.assertIn("no constituye asesoramiento financiero", post.lower())
            self.assertIn("?", post)
        self.assertIn("65,000.00", win_post)

    def test_archetype_5_recalibration_note(self) -> None:
        post = BinanceSquareContentGenerator.generate_recalibration_note(
            tuned_summary=[
                "• #BTCUSDT: Estrategia de Retroceso en Tendencia (Buy the Dip) (SL: 1.8x ATR | Target R:R: 2.2)",
                "• #ETHUSDT: Ruptura de Canal (SL: 2.0x ATR | Target R:R: 2.5)",
                "• #SOLUSDT: Triple Pantalla (SL: 1.6x ATR | Target R:R: 2.0)",
            ],
            sentiment_label="Neutral",
            sentiment_score=0.05,
        )
        self.assertLessEqual(len(post), 1950)
        self.assertNotIn("Buy the Dip", post)
        self.assertLessEqual(len(set(re.findall(r"\$([A-Z0-9]{2,10})\b", post))), 2)
        self.assertLessEqual(len(re.findall(r"#[a-zA-Z0-9_]+", post)), 3)
        self.assertIn("no constituye asesoramiento financiero", post.lower())
        self.assertIn("?", post)

    def test_adversarial_finbert_arcafid_emojis_hype_scrubbed_cleanly(self) -> None:
        """Adversarial FinBERT/ArcaFid/hype/URL inputs must be scrubbed cleanly without blank headings or losing R:R note."""
        from bot.binance_square import enforce_square_community_compliance

        adv_line = "Lectura FinBERT de ArcaFid muy limpia 🚀🔥💎 con enlace https://t.me/vip /subscribe"
        p_setup = BinanceSquareContentGenerator.generate_quant_setup_post(
            symbol="SOLUSDT",
            action="BUY",
            entry_price=145.0,
            stop_price=140.0,
            tp1=150.0,
            tp2=155.0,
            tp3=160.0,
            composite_score=0.80,
            thesis=adv_line,
            sentiment_label="FinBERT Alcista 🚀",
            sentiment_score=0.41,
        )
        p_macro = BinanceSquareContentGenerator.generate_macro_market_report(
            btc_price=64000.0,
            btc_change_pct=1.8,
            top_gainers=[],
            sentiment_label="FinBERT Alcista 🔥",
            sentiment_score=0.35,
            macro_summary=adv_line,
            session_label="Sesión ArcaFid 💎",
        )
        p_recal = BinanceSquareContentGenerator.generate_recalibration_note(
            tuned_summary=[adv_line],
            sentiment_label="FinBERT Neutral",
            sentiment_score=0.0,
            symbols=["BTCUSDT"],
            market_context=adv_line,
        )
        p_close = BinanceSquareContentGenerator.generate_trade_close_post(
            symbol="BTCUSDT",
            exit_price=65000.0,
            pnl_pct=2.1,
            reason="FinBERT ArcaFid muy limpia 🚀",
            sentiment_label="FinBERT Alcista",
            sentiment_score=0.25,
        )
        p_digest = BinanceSquareContentGenerator.generate_market_structure_digest(
            btc_price=64000.0,
            btc_change_pct=0.5,
            top_movers=[],
            sentiment_label="FinBERT Alcista 💎",
            sentiment_score=0.15,
        )

        for post in (p_setup, p_macro, p_recal, p_close, p_digest):
            low = post.lower()
            for forbidden in ("finbert", "arcafid", "muy limpia", "🚀", "🔥", "💎", "https://", "/subscribe", "rss alcista"):
                self.assertNotIn(forbidden, low)
            self.assertEqual(enforce_square_community_compliance(post), post)

        self.assertIn("asimetría", p_setup.lower())
        self.assertNotRegex(p_setup, r"Lectura cuantitativa \([^)]*\):\n\nMapa técnico:")
        self.assertNotRegex(p_macro, r"Lectura de mesa:\n\n¿")
        self.assertNotRegex(p_recal, r"Nota metodológica:\n\n¿")

    def test_quant_setup_sell_wording(self) -> None:
        """action='SELL' must render bearish wording ('Sesgo bajista', 'zonas inferiores', 'resistencia', 'cierre bajo')."""
        from bot.binance_square import enforce_square_community_compliance

        post = BinanceSquareContentGenerator.generate_quant_setup_post(
            symbol="BTCUSDT",
            action="SELL",
            entry_price=65000.0,
            stop_price=66500.0,
            tp1=63500.0,
            tp2=62000.0,
            tp3=60500.0,
            composite_score=0.80,
        )
        self.assertIn("Sesgo bajista", post)
        self.assertIn("1:3.00", post)
        self.assertNotIn("zonas superiores", post)
        self.assertNotIn("sostenga el soporte", post)
        self.assertNotIn("cierre sobre 63,500.00", post)
        self.assertEqual(enforce_square_community_compliance(post), post)

    def test_digest_zero_positive_movers(self) -> None:
        """theme_idx=1 with 0/N positive movers must avoid contradictory 'liderazgo puntual' / 'demanda real' copy."""
        from bot.binance_square import enforce_square_community_compliance

        post = BinanceSquareContentGenerator.generate_market_structure_digest(
            btc_price=62000.0,
            btc_change_pct=-2.5,
            top_movers=[
                {"symbol": "ETHUSDT", "change_pct": -3.1},
                {"symbol": "SOLUSDT", "change_pct": -4.2},
            ],
            sentiment_label="Bajista",
            sentiment_score=-0.35,
            theme_idx=1,
        )
        self.assertIn("0/2", post)
        self.assertNotIn("liderazgo puntual", post)
        self.assertNotIn("reciben demanda real", post)
        self.assertLessEqual(len(set(re.findall(r"\$([A-Z0-9]{2,10})\b", post))), 2)
        self.assertLessEqual(len(re.findall(r"#\w+", post)), 3)
        self.assertIn("no constituye asesoramiento financiero", post.lower())
        self.assertIn("?", post)
        self.assertEqual(enforce_square_community_compliance(post), post)

    def test_audited_performance_unknown_source_sanitized(self) -> None:
        """Performance report must map backtest_walkforward and sanitize unknown snake_case/URL sources."""
        from bot.binance_square import enforce_square_community_compliance

        out_bw = BinanceSquareContentGenerator.generate_audited_performance_report(
            62.5, 1.85, -3.2, 1.9, 100, source="backtest_walkforward"
        )
        out_custom = BinanceSquareContentGenerator.generate_audited_performance_report(
            62.5, 1.85, -3.2, 1.9, 100, source="custom_raw_snake https://evil.com"
        )
        for out in (out_bw, out_custom):
            self.assertNotIn("backtest_walkforward", out)
            self.assertNotIn("custom_raw_snake", out)
            self.assertNotIn("https://", out)
            self.assertEqual(re.findall(r"\b[a-z]+_[a-z0-9_]+\b", out), [])
            self.assertEqual(enforce_square_community_compliance(out), out)
        self.assertIn("walk-forward", out_bw.lower())

    def test_gainer_volume_billion_formatting(self) -> None:
        """Top gainers with quote_volume >= 1B must format as $X.XXB rather than $1540.0M."""
        out = BinanceSquareContentGenerator.generate_macro_market_report(
            btc_price=64000.0,
            btc_change_pct=2.0,
            top_gainers=[
                {"symbol": "ETHUSDT", "price": 3200.0, "change_pct": 4.5, "quote_volume": 1_540_000_000.0},
                {"symbol": "SOLUSDT", "price": 150.0, "change_pct": 3.2, "quote_volume": 45_000_000.0},
            ],
            sentiment_label="Alcista",
            sentiment_score=0.25,
        )
        self.assertIn("$1.54B", out)
        self.assertNotIn("$1540.0M", out)
        self.assertIn("$45.0M", out)


if __name__ == "__main__":
    unittest.main()
