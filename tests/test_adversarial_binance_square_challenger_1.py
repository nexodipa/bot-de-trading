from __future__ import annotations

import hashlib
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
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.abspath("."))

from bot.binance_square import (
    BinanceSquareContentGenerator,
    BinanceSquarePublisher,
    SquareRateLimiter,
    enforce_square_community_compliance,
    sanitize_for_square,
)
from bot.config import BotConfig


class TestAdversarialExtremeTextSizes(unittest.TestCase):
    """Stress tests for extreme text inputs, boundary enforcement, and CTA preservation."""

    def test_massive_overflow_setup_post_bounds(self) -> None:
        """Massive thesis (50,000 characters) must never exceed 1,950 characters."""
        massive_thesis = "Divergencia cuantitativa extrema con absorción fiduciaria. " * 1000  # ~58,000 chars
        post = BinanceSquareContentGenerator.generate_quant_setup_post(
            symbol="BTCUSDT",
            action="BUY",
            entry_price=65432.10,
            stop_price=64000.00,
            tp1=66500.00,
            tp2=68000.00,
            tp3=70000.00,
            composite_score=0.892,
            timeframe="15m",
            thesis=massive_thesis,
        )

        self.assertLessEqual(len(post), 1950, f"Post length {len(post)} exceeded 1950 limit")
        self.assertLess(len(post), 2000, "Post length must be strictly under 2,000 chars")

        # Sober DYOR signature, closing question & strategic hashtag survive truncation; zero external CTAs
        self.assertNotIn("@AdminVIPSignals", post)
        self.assertNotIn("/subscribe", post)
        self.assertNotIn("github.io", post)
        self.assertNotIn("https://", post)
        self.assertIn("no constituye asesoramiento financiero", post.lower())
        self.assertIn("?", post)
        self.assertIn("#BinanceSquare", post, "Strategic hashtag lost in truncation")
        self.assertLessEqual(len(re.findall(r"#[a-zA-Z0-9_]+", post)), 3)
        self.assertLessEqual(len(set(re.findall(r"\$([A-Z0-9]{2,10})\b", post))), 2)

    def test_massive_macro_report_gainers_overflow(self) -> None:
        """Macro report with 50 top gainers and 20,000 character summary remains bounded."""
        huge_gainers = [
            {"symbol": f"TOKEN{i}USDT", "price": 1.23 * i, "change_pct": 5.0 + i, "quote_volume": 1000000.0 * i}
            for i in range(1, 51)
        ]
        huge_summary = "Análisis de macro liquidez y tasas de financiamiento. " * 400

        post = BinanceSquareContentGenerator.generate_macro_market_report(
            btc_price=63500.0,
            btc_change_pct=1.85,
            top_gainers=huge_gainers,
            sentiment_label="[ALCISTA] Fuerte Presión",
            sentiment_score=0.72,
            macro_summary=huge_summary,
        )

        self.assertLessEqual(len(post), 1950)
        self.assertNotIn("@AdminVIPSignals", post)
        self.assertNotIn("github.io", post)
        self.assertIn("#BinanceSquare", post)
        self.assertIn("no constituye asesoramiento financiero", post.lower())
        self.assertLessEqual(len(re.findall(r"#[a-zA-Z0-9_]+", post)), 3)
        self.assertLessEqual(len(set(re.findall(r"\$([A-Z0-9]{2,10})\b", post))), 2)

    def test_raw_sanitizer_arbitrary_unstructured_overflow(self) -> None:
        """Arbitrary string of 100,000 continuous characters without spaces or markers."""
        huge_blob = "A" * 100000
        sanitized = sanitize_for_square(huge_blob, max_chars=1950)
        self.assertLessEqual(len(sanitized), 1950)
        self.assertTrue(sanitized.endswith("..."))

    def test_oversized_footer_boundary(self) -> None:
        """When footer itself is extremely large, total length must still strictly respect max_chars."""
        huge_footer_text = (
            "Encabezado de prueba.\n\n"
            + "📲 Canal VIP & Señales Cuantitativas: @AdminVIPSignals (Comando /subscribe) "
            + ("DETALLES ADICIONALES " * 200)
            + "\n🏛️ Portal Institucional & Simulador Actuarial: https://nexodipa.github.io/bot-de-trading/"
            + "\n#BinanceSquare"
        )
        sanitized = sanitize_for_square(huge_footer_text, max_chars=1950)
        self.assertLessEqual(len(sanitized), 1950)


class TestAdversarialHTMLInjectionAndBypasses(unittest.TestCase):
    """Stress tests for HTML injection, XSS vectors, and Markdown tag hygiene."""

    def test_script_tag_injection_purged(self) -> None:
        """Script tags with inline code or remote sources must be completely purged."""
        vectors = [
            "<script>alert('xss')</script>",
            "<SCRIPT SRC=\"https://attacker.com/malware.js\"></SCRIPT>",
            "<script type=\"text/javascript\">document.cookie='stolen';</script>",
            "<<SCRIPT>alert('nested')</SCRIPT>",
        ]
        for vector in vectors:
            sanitized = sanitize_for_square(f"Análisis cuantitativo {vector} seguro")
            self.assertNotIn("<script", sanitized.lower(), f"Script tag bypassed sanitizer: {vector}")
            self.assertNotIn("</script", sanitized.lower(), f"Closing script tag bypassed: {vector}")

    def test_img_and_iframe_event_handlers_purged(self) -> None:
        """Image and iframe tags with onerror or javascript URIs must be completely stripped."""
        payloads = [
            "<img src='x' onerror='alert(1)'>",
            "<IMG SRC=javascript:alert('XSS')>",
            "<iframe src=\"javascript:alert('xss')\"></iframe>",
            "<svg/onload=alert(1)>",
            "<body onload=alert('test')>",
        ]
        for payload in payloads:
            sanitized = sanitize_for_square(f"Setup {payload} confirmado")
            self.assertNotIn("<img", sanitized.lower())
            self.assertNotIn("<iframe", sanitized.lower())
            self.assertNotIn("<svg", sanitized.lower())
            self.assertNotIn("<body", sanitized.lower())

    def test_disallowed_formatting_converted_or_removed(self) -> None:
        """HTML formatting tags (b, strong, i, em, pre, code) and robotic ** / [] symbols must be stripped to clean text."""
        raw = "[ALERTA] <b>Bold</b> <strong>Strong</strong> <i>Italic</i> <em>Em</em> <pre>Code</pre> <code>inline</code> **extra**"
        sanitized = sanitize_for_square(raw)

        # Forbidden HTML tags and robotic markers (** / * / [ / ]) must not exist in output
        for tag in ["<b", "</b>", "<strong", "</strong>", "<i", "</i>", "<em", "</em>", "<pre", "</pre>", "<code", "</code>", "**", "*", "[", "]"]:
            self.assertNotIn(tag, sanitized.lower())

        # Clean plain-text words should be preserved
        self.assertIn("ALERTA", sanitized)
        self.assertIn("Bold", sanitized)
        self.assertIn("Strong", sanitized)
        self.assertIn("Italic", sanitized)
        self.assertIn("Em", sanitized)
        self.assertIn("Code", sanitized)
        self.assertIn("inline", sanitized)

    def test_anchor_tag_sanitization(self) -> None:
        """Anchor tags <a href='url'>text</a> are converted to text (url) without raw HTML."""
        raw = 'Consulte nuestro <a href="https://example.com/signals">Canal VIP</a> para alertas.'
        sanitized = sanitize_for_square(raw)
        self.assertNotIn("<a", sanitized)
        self.assertNotIn("</a>", sanitized)
        self.assertIn("Canal VIP (https://example.com/signals)", sanitized)

    def test_mathematical_angle_brackets_behavior(self) -> None:
        """Adversarial probe: tests how mathematical comparisons (Drawdown < -6.4% y Sharpe > 2.0) are handled.
        
        Documents the behavior when text contains < ... > on the same line.
        """
        raw = "Operativa con Score >= 0.72, Drawdown < -6.4% y Sharpe > 2.0 con capital < $50k."
        sanitized = sanitize_for_square(raw)
        self.assertIn("Score >= 0.72", sanitized)
        self.assertIn("Drawdown < -6.4%", sanitized)
        self.assertIn("Sharpe > 2.0", sanitized)
        self.assertIn("< $50k", sanitized)


class TestAdversarialRateLimitingAndDeduplication(unittest.TestCase):
    """Stress tests for SquareRateLimiter: rapid bursts, cooldowns, hourly ceilings, and 24h deduplication."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self._tmpdir.name, "adv_rate.sqlite3")
        self.limiter = SquareRateLimiter(
            db_path=self.db_path,
            rate_limit_per_hour=5,
            min_cooldown_seconds=900.0,  # 15 minutes standard
        )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_rapid_burst_calls_cleanly_throttled(self) -> None:
        """Rapid burst calls (10 attempts in instant sequence) are throttled after the first."""
        # 1st call must succeed
        can_pub_1, reason_1 = self.limiter.can_publish("Market Update #1", is_priority_alert=False)
        self.assertTrue(can_pub_1, f"First call should succeed: {reason_1}")
        self.limiter.record_published("Market Update #1")

        # Calls 2..10 within the same second must all fail due to cooldown
        for i in range(2, 11):
            can_pub, reason = self.limiter.can_publish(f"Market Update #{i}", is_priority_alert=False)
            self.assertFalse(can_pub, f"Burst call #{i} should be throttled")
            self.assertIn("cooldown", reason.lower())

    def test_priority_alert_reduced_cooldown_handling(self) -> None:
        """Priority alerts (Score >= 0.72) enforce a shorter 180s cooldown instead of 900s."""
        self.limiter.record_published("Initial Post")

        # At t + 10s: Priority alert is still blocked by 180s cooldown
        with patch("time.time", return_value=self.limiter.last_post_ts + 10.0):
            can_pub, reason = self.limiter.can_publish("Priority Alert", is_priority_alert=True)
            self.assertFalse(can_pub)
            self.assertIn("170s", reason)

        # At t + 185s: Standard alert is STILL blocked (needs 900s), but Priority alert is ALLOWED (needs 180s)
        with patch("time.time", return_value=self.limiter.last_post_ts + 185.0):
            can_std, reason_std = self.limiter.can_publish("Standard Alert", is_priority_alert=False)
            self.assertFalse(can_std, "Standard alert should remain blocked within 900s cooldown")

            can_prio, reason_prio = self.limiter.can_publish("Priority Alert", is_priority_alert=True)
            self.assertTrue(can_prio, f"Priority alert should be permitted after 180s: {reason_prio}")

    def test_hourly_sliding_window_ceiling_at_5_posts(self) -> None:
        """Even with cooldown satisfied, the 6th post within 3600 seconds is strictly blocked."""
        base_time = 100000.0

        # Simulate 5 successful priority posts spaced by 200s (satisfying 180s cooldown)
        for i in range(1, 6):
            post_time = base_time + (i * 200.0)
            with patch("time.time", return_value=post_time):
                can_pub, reason = self.limiter.can_publish(f"Alert #{i}", is_priority_alert=True)
                self.assertTrue(can_pub, f"Alert #{i} at t={post_time} should succeed, got {reason}")
                self.limiter.record_published(f"Alert #{i}")

        # Attempt 6th post at t = base_time + 1200s (cooldown is satisfied: 1200 - 1000 = 200 > 180)
        # BUT hourly window has 5 posts in the last 1200s (< 3600s)
        with patch("time.time", return_value=base_time + 1200.0):
            can_pub_6, reason_6 = self.limiter.can_publish("Alert #6", is_priority_alert=True)
            self.assertFalse(can_pub_6, "6th post in 1 hour must be strictly throttled")
            self.assertIn("Hourly rate limit exceeded: 5/5", reason_6)

        # Window recovery: at t = base_time + 3801s (more than 3600s after post #1)
        # Post #1 (at base_time + 200s) has aged 3601s, sliding out of the window
        with patch("time.time", return_value=base_time + 3801.0):
            can_pub_7, reason_7 = self.limiter.can_publish("Alert #7", is_priority_alert=True)
            self.assertTrue(can_pub_7, f"Post #7 should succeed after window slides: {reason_7}")

    def test_duplicate_content_hash_blocked_within_24h(self) -> None:
        """Identical content hash is blocked within 24h rolling window, even if rate quota is available."""
        base_time = 100000.0
        post_content = "Setup de alta convicción en SOLUSDT con R:R 1:3.0"

        with patch("time.time", return_value=base_time):
            can_pub, _ = self.limiter.can_publish(post_content)
            self.assertTrue(can_pub)
            self.limiter.record_published(post_content)

        # 2 hours later (t + 7200s): Cooldown (900s) and hourly quota (max 5) are 100% free
        # Attempt to publish the EXACT same content
        with patch("time.time", return_value=base_time + 7200.0):
            can_dup, reason_dup = self.limiter.can_publish(post_content)
            self.assertFalse(can_dup, "Duplicate content within 24h must be rejected")
            self.assertIn("Duplicate content detected within 24 hours", reason_dup)

            # Different content must be permitted
            can_diff, reason_diff = self.limiter.can_publish("Different post content")
            self.assertTrue(can_diff, f"Different content should be accepted: {reason_diff}")

        # 24 hours and 1 minute later (t + 86460s): 24h window has passed
        with patch("time.time", return_value=base_time + 86460.0):
            can_after_24h, reason_after_24h = self.limiter.can_publish(post_content)
            self.assertTrue(can_after_24h, f"Same content should be allowed after 24 hours: {reason_after_24h}")

    def test_sqlite_state_persistence_across_instances(self) -> None:
        """Limiter state persisted in SQLite bot_state is cleanly reloaded by a new instance."""
        post_text = "Persisted State Test Post"
        self.limiter.record_published(post_text)

        # Instantiate a second limiter on the same SQLite file
        new_limiter = SquareRateLimiter(
            db_path=self.db_path,
            rate_limit_per_hour=5,
            min_cooldown_seconds=900.0,
        )

        # Verify state was reloaded
        self.assertEqual(len(new_limiter.hourly_timestamps), 1)
        self.assertEqual(len(new_limiter.recent_hashes), 1)
        self.assertEqual(new_limiter.last_post_ts, self.limiter.last_post_ts)

        # Rapid second post in new instance is blocked
        can_pub, reason = new_limiter.can_publish("Another Post")
        self.assertFalse(can_pub)
        self.assertIn("cooldown", reason.lower())

    def test_priority_alert_tiered_cooldown_for_60m_config(self) -> None:
        """For 60m (3600s) config, priority alerts enforce 1800s (30m) instead of collapsing to 180s."""
        with tempfile.TemporaryDirectory() as td:
            limiter_60m = SquareRateLimiter(
                db_path=os.path.join(td, "tier.sqlite3"),
                rate_limit_per_hour=5,
                min_cooldown_seconds=3600.0,
            )
            limiter_60m.record_published("Initial 60m Post")
            with patch("time.time", return_value=limiter_60m.last_post_ts + 200.0):
                ok_200, _ = limiter_60m.can_publish("Priority at 200s", is_priority_alert=True)
                self.assertFalse(ok_200)
            with patch("time.time", return_value=limiter_60m.last_post_ts + 1805.0):
                ok_1805, _ = limiter_60m.can_publish("Priority at 1805s", is_priority_alert=True)
                self.assertTrue(ok_1805)


class TestAdversarialComplianceHardening(unittest.TestCase):
    """Edge-case compliance tests: orphan hashtags, digit-prefixed cashtags, Telegram news preservation, DYOR truncation."""

    def test_excess_hashtags_dropped_cleanly_without_orphan_words(self) -> None:
        raw = "Lectura técnica en $BTC.\n\n#BinanceSquare #TradingCuantitativo #Bitcoin #CryptoTrading #ArcaFid"
        compliant = enforce_square_community_compliance(raw)
        self.assertLessEqual(len(re.findall(r"#[a-zA-Z0-9_]+", compliant)), 3)
        self.assertNotIn("CryptoTrading", compliant)
        self.assertNotIn("ArcaFid", compliant)

    def test_digit_prefixed_and_duplicate_cashtags_dedup_220095(self) -> None:
        raw = (
            "Seguimiento en #BTC y segunda lectura en #BTC.\n"
            "Rotación hacia #1000PEPEUSDT, #ETHUSDT y #SOLUSDT con volumen $50k, $45.0M, $100MM sobre $USDT, $DAI, $EUR y $PYUSD."
        )
        compliant = enforce_square_community_compliance(raw)
        unique_cashtags = set(re.findall(r"\$(?!\d+(?:[KMBT]|MM|BN)?\b)((?:[0-9]{1,5})?[A-Z]{2,10}(?:[0-9]{1,3})?)\b", compliant))
        self.assertLessEqual(len(unique_cashtags), 2)
        self.assertIn("$BTC", compliant)
        self.assertIn("$1000PEPE", compliant)
        self.assertIn("$50k", compliant)
        self.assertIn("$45.0M", compliant)
        self.assertIn("$100MM", compliant)
        self.assertNotIn("$USDT", compliant)
        self.assertNotIn("$DAI", compliant)
        self.assertNotIn("$EUR", compliant)
        self.assertNotIn("$PYUSD", compliant)

    def test_telegram_filter_preserves_news_headline_context(self) -> None:
        raw = (
            "TON rebounds after Telegram mini-app update while El CEO de Telegram comentó sobre liquidez.\n"
            "Canal VIP en Telegram @AdminVIPSignals"
        )
        compliant = enforce_square_community_compliance(raw)
        self.assertIn("TON rebounds after Telegram mini-app update", compliant)
        self.assertIn("El CEO de Telegram comentó sobre liquidez", compliant)
        self.assertNotIn("Canal VIP", compliant)
        self.assertNotIn("@AdminVIPSignals", compliant)

    def test_compliance_before_truncation_preserves_dyor_and_max_chars(self) -> None:
        long_body = ("Análisis cuantitativo de liquidez y estructura en $BTC con control ATR.\n" * 45)
        raw = f"{long_body}\nhttps://evil.example/promo\n#A #B #C #D #E"
        compliant = enforce_square_community_compliance(raw)
        self.assertLessEqual(len(compliant), 1950)
        self.assertIn("no constituye asesoramiento financiero", compliant.lower())
        self.assertLessEqual(len(re.findall(r"#[a-zA-Z0-9_]+", compliant)), 3)
        self.assertNotIn("https://", compliant)
        self.assertEqual(enforce_square_community_compliance(compliant), compliant)

    def test_unicode_accented_hashtags_trimmed_cleanly(self) -> None:
        """Unicode Spanish accented hashtags >3 must drop cleanly without orphan fragments."""
        raw_a = "Estructura sólida en $BTC hoy.\n\n#TradingCuantitativo #GestionDeRiesgo #BinanceSquare #Análisis #Inversión #Criptografía"
        out_a = enforce_square_community_compliance(raw_a)
        self.assertLessEqual(len(re.findall(r"#[^\W_][\w]*", out_a)), 3)
        for orphan in ("álisis", "ón", "ía"):
            self.assertNotIn(orphan, out_a)

        raw_b = (
            "Lectura cuantitativa de estructura y liquidez en $BTC sobre múltiples marcos temporales.\n\n"
            "#Análisis #Inversión #BinanceSquare #GestiónDeRiesgo #Criptografía"
        )
        out_b = enforce_square_community_compliance(raw_b)
        tags_b = re.findall(r"#[^\W_][\w]*", out_b)
        self.assertEqual(tags_b, ["#Análisis", "#Inversión", "#BinanceSquare"])
        self.assertNotIn("DeRiesgo", out_b)
        self.assertNotIn("ía", out_b)
        self.assertIn("no constituye asesoramiento financiero", out_b.lower())
        self.assertLess(out_b.lower().find("no constituye asesoramiento financiero"), out_b.find("#Análisis"))
        self.assertEqual(enforce_square_community_compliance(out_b), out_b)

    def test_multilevel_github_io_and_anchor_parens_stripped_cleanly(self) -> None:
        """Multi-level *.github.io subdomains and <a href> parens strip cleanly without stray '(' or 'sub.'."""
        s1 = "Lee más en sub.user.github.io/repo y docs.team.github.io sobre $BTC."
        out1 = enforce_square_community_compliance(sanitize_for_square(s1, max_chars=None))
        for bad in ("github.io", "sub.", "docs.", "/repo"):
            self.assertNotIn(bad, out1)

        s2 = "<b># Análisis</b> de <i>$BTC</i> con `codigo` y <script>alert(1)</script> y <a href='https://evil.com'>click aquí</a> **fuerte**"
        out2 = sanitize_for_square(enforce_square_community_compliance(sanitize_for_square(s2, max_chars=None)), max_chars=1950)
        for bad in ("https://evil.com", "<b>", "<script>", "click aquí ("):
            self.assertNotIn(bad, out2)
        self.assertIn("click aquí", out2)
        self.assertEqual(out2.count("("), out2.count(")"))

        s3 = 'Consulta <a href="https://evil.com">click aquí</a> ahora sobre $BTC.'
        out3 = sanitize_for_square(enforce_square_community_compliance(sanitize_for_square(s3, max_chars=None)), max_chars=1950)
        self.assertIn("click aquí", out3)
        self.assertNotIn("(", out3)
        self.assertNotIn(")", out3)

    def test_telegram_news_endings_and_acceso_preserved(self) -> None:
        """Legitimate news mentions of Telegram ('CEO de Telegram.', 'sobre Telegram,', 'El acceso a...') are preserved."""
        cases = [
            "Las declaraciones fueron confirmadas por el CEO de Telegram.\n$BTC mantiene soporte.",
            "Según un reporte sobre Telegram, la actividad on-chain subió.\n$BTC mantiene soporte.",
            "El acceso a herramientas de pago en Telegram crece en Europa.\n$BTC mantiene soporte.",
        ]
        for raw in cases:
            out = enforce_square_community_compliance(raw)
            first_line = raw.splitlines()[0]
            self.assertIn(first_line, out)

        cta_raw = "Únete a nuestro canal VIP en Telegram @AdminVIPSignals /subscribe\n$BTC mantiene soporte."
        cta_out = enforce_square_community_compliance(cta_raw)
        self.assertNotIn("canal VIP", cta_out)
        self.assertNotIn("@AdminVIPSignals", cta_out)
        self.assertNotIn("/subscribe", cta_out)
        self.assertIn("$BTC mantiene soporte.", cta_out)

    def test_truncation_gt_1950_preserves_closing_question_and_dyor(self) -> None:
        """Truncation > 1950 chars preserves both the closing analytical '?' line and DYOR disclaimer."""
        from bot.binance_square import BinanceSquareContentGenerator

        long_lines = [
            f"• BTCUSDT: active_momentum SL 1.8x ATR con seguimiento de volatilidad realizada y control de liquidez intradía número {i} " + ("detalle " * 15)
            for i in range(6)
        ]
        recal_huge = BinanceSquareContentGenerator.generate_recalibration_note(
            tuned_summary=long_lines,
            sentiment_label="Neutral",
            sentiment_score=0.02,
            symbols=["BTCUSDT", "ETHUSDT"],
            market_context="Calibración estadística con validación fuera de muestra sobre múltiples ventanas de volatilidad realizada. " * 4,
        )
        self.assertLessEqual(len(recal_huge), 1950)
        self.assertIn("?", recal_huge)
        self.assertIn("no constituye asesoramiento financiero", recal_huge.lower())
        self.assertEqual(enforce_square_community_compliance(recal_huge), recal_huge)

        long_body = ("Análisis cuantitativo de profundidad de mercado y control de riesgo en $BTC.\n" * 40)
        custom = (
            f"{long_body}\n¿Cómo calibras tu riesgo?\n\n"
            "Nota educativa. No constituye asesoramiento financiero.\n\n#A #B #C"
        )
        out_custom = enforce_square_community_compliance(custom)
        self.assertLessEqual(len(out_custom), 1950)
        self.assertIn("¿Cómo calibras tu riesgo?", out_custom)
        self.assertIn("no constituye asesoramiento financiero", out_custom.lower())
        self.assertEqual(enforce_square_community_compliance(out_custom), out_custom)


if __name__ == "__main__":
    unittest.main()
