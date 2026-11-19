from __future__ import annotations

import hashlib
import inspect
import json
import logging
import os
import random
import re
import sqlite3
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import requests
from bot.config import BotConfig

__all__ = [
    "BinanceSquarePublisher",
    "BinanceSquareContentGenerator",
    "SquareRateLimiter",
    "sanitize_for_square",
    "enforce_square_community_compliance",
    "translate_close_reason_es",
]


def _is_unmocked_test_http_call() -> bool:
    """Impide llamadas HTTP reales a Binance Square cuando se ejecuta bajo test sin mock de requests.post."""
    in_test_runtime = (
        os.getenv("PYTEST_CURRENT_TEST") is not None
        or os.getenv("BOT_DISABLE_LIVE_SQUARE", "").strip().lower() in {"1", "true", "yes"}
    )
    if not in_test_runtime:
        main_mod = sys.modules.get("__main__")
        main_file = str(getattr(main_mod, "__file__", "") or "").lower()
        if "unittest" in main_file or "pytest" in main_file:
            in_test_runtime = True
        elif "unittest" in sys.modules or "pytest" in sys.modules:
            # Librerías científicas (sklearn/pandas) importan unittest en runtime productivo;
            # verificar si realmente estamos dentro de un TestCase o runner de pytest en la pila.
            for frame in inspect.stack():
                fn = frame.filename.replace("\\", "/").lower()
                if "/unittest/case.py" in fn or "/_pytest/" in fn:
                    in_test_runtime = True
                    break
    if not in_test_runtime:
        return False
    try:
        from unittest.mock import NonCallableMock
        return not isinstance(requests.post, NonCallableMock)
    except Exception:
        return True


def translate_close_reason_es(reason: str) -> str:
    """Traduce códigos internos de cierre de operación a lenguaje técnico natural en español."""
    raw = (reason or "").strip()
    low = raw.lower()
    mapping = {
        "take_profit": "alcance de objetivo de liquidez (Take Profit)",
        "target_exit": "alcance de zona objetivo definida",
        "stop_loss": "activación de nivel de invalidación estructural (Stop Loss)",
        "stop_or_trailing": "ejecución de límite de invalidación o trailing de protección",
        "trailing_stop": "activación de trailing stop para proteger margen acumulado",
        "trend_or_momentum_exit": "rotación de flujo y pérdida de momentum direccional",
        "time_exit": "vencimiento de ventana temporal sin continuidad de volumen",
        "drawdown_lock": "activación preventiva de límite fiduciario de drawdown",
        "reconciled_close": "cierre conciliado contra el libro de órdenes del exchange",
        "anti_orphan_emergency_sell": "liquidación de salvaguarda para evitar posición sin protección",
        "manual_close": "cierre táctico discrecional",
    }
    if low in mapping:
        return mapping[low]
    for key, desc in mapping.items():
        if key in low:
            return desc
    if not raw or "_" in raw or low == "unknown":
        return "gestión táctica de salida según control de riesgo"
    cleaned_raw = _sanitize_editorial_text(raw, max_chars=120)
    return cleaned_raw or "gestión táctica de salida según control de riesgo"


def sanitize_for_square(text: str, max_chars: int | None = 1950) -> str:
    """Limpia y sanitiza el texto para el OpenAPI de Binance Square.

    1. Convierte o elimina etiquetas HTML no soportadas (<b>, <code>, <pre>, <i>, <a>, <div>, etc.).
    2. Elimina Markdown crudo (**, backticks, encabezados # ).
    3. Cuando max_chars > 0, respeta límites estrictos (< 2,000 caracteres, objetivo <= max_chars)
       preservando pie editorial DYOR y bloque final de hashtags.
    """
    if not text:
        return ""

    # Normalizar retornos de carro
    cleaned = text.replace("\r\n", "\n").replace("\r", "\n")

    # Eliminar etiquetas HTML de formato sin dejar asteriscos ni marcas robóticas
    cleaned = re.sub(r"<\s*/?\s*(?:b|strong|i|em|pre|code)\s*>", "", cleaned, flags=re.IGNORECASE)

    # Convertir enlaces <a href="url">texto</a> -> texto (url) o url
    def _replace_a_tag(match: re.Match[str]) -> str:
        url = match.group(1).strip()
        anchor_text = match.group(2).strip()
        if anchor_text and anchor_text.lower() != url.lower():
            return f"{anchor_text} ({url})"
        return url

    cleaned = re.sub(
        r"""<\s*a\s+[^>]*href=["']([^"']+)["'][^>]*>(.*?)<\s*/\s*a\s*>""",
        _replace_a_tag,
        cleaned,
        flags=re.IGNORECASE | re.DOTALL,
    )

    # Eliminar cualquier etiqueta HTML remanente (<div...>, </div...>, etc.)
    # preservando expresiones matemáticas comparativas como "Drawdown < -6.4% y Sharpe > 2.0" o "< $50k"
    cleaned = re.sub(r"</?[a-zA-Z][^>]*>", "", cleaned)

    # Eliminar signos robóticos de Markdown (**, backticks, encabezados "# ") y corchetes ([ ])
    cleaned = re.sub(r"\*+", "", cleaned)
    cleaned = cleaned.replace("`", "")
    cleaned = re.sub(r"(?m)^#{1,6}[ \t]+", "", cleaned)
    cleaned = re.sub(r"\[([^\]]+)\]", r"\1", cleaned)
    cleaned = cleaned.replace("[", "").replace("]", "")

    # Modo solo-normalización (usado antes de aplicar cumplimiento comunitario)
    if max_chars is None or max_chars <= 0:
        return cleaned

    # Si el texto ya entra en el límite de caracteres, retornar directamente
    if len(cleaned) <= max_chars:
        return cleaned

    # Si excede max_chars, separar el cuerpo de la sección de pie (DYOR y hashtags)
    # para garantizar que el descargo educativo y las etiquetas finales no queden truncados
    footer_markers = [
        "— Proyecto Fehu (ᚠ) Quantitative",
        "Nota: Análisis cuantitativo estrictamente educativo",
        "Esto no es asesoramiento financiero",
        "No constituye asesoramiento financiero",
        "no constituye asesoramiento financiero",
        "📲 Señales",
        "📲 Canal VIP",
        "@AdminVIPSignals",
        "/subscribe",
        "🏛️ Simulador",
        "🏛️ Portal Institucional",
        "https://nexodipa.github.io/bot-de-trading/",
        "https://josuest-b.github.io/bot-de-trading/",
        "#BinanceSquare",
    ]

    min_marker_idx = -1
    for marker in footer_markers:
        idx = cleaned.find(marker)
        if idx != -1:
            if min_marker_idx == -1 or idx < min_marker_idx:
                min_marker_idx = idx

    if min_marker_idx > 0 and cleaned[min_marker_idx - 1] != "\n":
        line_start = cleaned.rfind("\n", 0, min_marker_idx) + 1
        if 0 < (min_marker_idx - line_start) <= 120:
            min_marker_idx = line_start

    if min_marker_idx == -1:
        m_hash_footer = re.search(
            r"\n+(?:#\w+(?:[ \t]+#\w+)*)\s*$",
            cleaned,
        )
        if m_hash_footer:
            min_marker_idx = m_hash_footer.start() + 1

    if min_marker_idx != -1:
        body = cleaned[:min_marker_idx].rstrip()
        footer = cleaned[min_marker_idx:].strip()

        # Preservar pregunta analítica de cierre (?) inmediatamente previa al pie editorial
        if body:
            last_nl = body.rfind("\n")
            if last_nl != -1:
                body_prefix = body[:last_nl].rstrip()
                last_line = body[last_nl + 1 :].strip()
                if (
                    body_prefix
                    and last_line.endswith("?")
                    and len(last_line) <= 320
                    and (max_chars - (len(last_line) + 2 + len(footer)) - 5) > 40
                ):
                    body = body_prefix
                    footer = f"{last_line}\n\n{footer}"

        # Margen de seguridad para separador "...\n\n"
        avail_body = max_chars - len(footer) - 5
        if avail_body > 40:
            if len(body) <= avail_body:
                return f"{body}\n\n{footer}"
            truncated_body = body[:avail_body].rstrip()
            # Buscar último salto de línea o espacio para no cortar palabras
            last_space = max(truncated_body.rfind("\n"), truncated_body.rfind(" "))
            if last_space > avail_body // 2:
                truncated_body = truncated_body[:last_space].rstrip()
            return f"{truncated_body}...\n\n{footer}"
        else:
            # Si el footer solo casi llena max_chars, truncar el footer si fuera imprescindible
            return footer[:max_chars]
    else:
        # Sin bloque de footer identificado: truncado regular respetando palabras
        truncated = cleaned[: max_chars - 3].rstrip()
        last_space = max(truncated.rfind("\n"), truncated.rfind(" "))
        if last_space > (max_chars - 3) // 2:
            truncated = truncated[:last_space].rstrip()
        return f"{truncated}..."


_EDITORIAL_NOISE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"#?\b(?:arcafid(?:\s+quantitative)?|finbert)\b", re.IGNORECASE),
    re.compile(r"\bmuy\s+limpi[ao]s?\b", re.IGNORECASE),
    re.compile(r"\b(?:gran\s+)?oportunidad(?:es)?(?:\s+(?:única|imperdible))?\b", re.IGNORECASE),
    re.compile(
        r"\b(?:100%\s*segur[ao]s?|garantizad[ao]s?|infalible(?:s)?|dinero\s+f[aá]cil|sin\s+riesgo)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"[\U0001F680\U0001F525\U0001F48E\U0001F4F2\U0001F3DB\U0001F4B0\U0001F4C8"
        r"\U0001F6A8\U0001F911\U0001F4A5\U0001F3AF\u26A1\U0001F319\U0001F4B8\u2728"
        r"\U0001F52E\U0001F447\U0001F449\ufe0f]+"
    ),
)


def _strip_external_ctas_and_links(text: str) -> str:
    """Elimina líneas/fragmentos de CTAs externos, URLs, @handles, comandos y billeteras cripto."""
    if not text:
        return ""
    out = text

    # 1. Purgar líneas completas de CTAs externos e invitaciones a mensajería
    out = re.sub(
        r"(?im)^.*?(?:Canal VIP|Señales VIP|Portal Institucional|simulador en vivo|"
        r"Notificación de depósito|Dirección Oficial|@AdminVIPSignals|/subscribe|"
        r"t\.me/|telegram\.(?:me|dog)/|wa\.me/|chat\.whatsapp\.com/|discord\.gg/|"
        r"(?:únete|unete|síguenos|siguenos|escríbenos|escribenos|escribe|consultas|"
        r"contacto|contáctanos|contactanos|solicita\s+acceso|acceso\s+(?:vip|privado|exclusivo|por|v[ií]a)|"
        r"grupo|canal|comunidad|bot|link|enlace|dm|privado|join)\b"
        r".*?\b(?:Telegram|WhatsApp|Discord)\b|"
        r"\b(?:Telegram|WhatsApp|Discord)\b.*?\b(?:VIP|canal|grupo|bot|link|enlace|"
        r"únete|unete|join|channel|group|signals|señales|senales)\b).*$(?:\n|$)",
        "",
        out,
    )

    # 2. Purgar URLs externas (https://, http://, www., *.github.io, invitaciones sin protocolo)
    #    Preserva el paréntesis exterior ')' cuando sanitize_for_square convierte <a href="url">texto</a> -> texto (url)
    _url_tail = r"[^\s<>()]+(?:\([^\s<>()]*\)[^\s<>()]*)*"
    out = re.sub(rf"https?://{_url_tail}", "", out, flags=re.IGNORECASE)
    out = re.sub(rf"\bwww\.{_url_tail}", "", out, flags=re.IGNORECASE)
    out = re.sub(
        r"\b(?:[a-zA-Z0-9_-]+\.)+github\.io(?:/[^\s<>()]*(?:\([^\s<>()]*\)[^\s<>()]*)*)?",
        "",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        rf"\b(?:t\.me|telegram\.(?:me|dog)|wa\.me|chat\.whatsapp\.com|discord\.gg)/{_url_tail}",
        "",
        out,
        flags=re.IGNORECASE,
    )

    # 3. Purgar menciones @handle, comandos de bot y CTAs en línea a mensajería externa
    out = out.replace("@AdminVIPSignals", "")
    out = re.sub(r"@[a-zA-Z0-9_]{3,}", "", out)
    out = re.sub(r"\(\s*(?:escribe|comando)\s*/[a-zA-Z0-9_]+\s*\)", "", out, flags=re.IGNORECASE)
    out = re.sub(r"(?<!\w)/(?:subscribe|plans|vip|start)\b", "", out, flags=re.IGNORECASE)
    out = re.sub(
        r"[ \t]+(?:(?:en|por|vía|via|al?|de)[ \t]+)?(?:nuestro|mi|(?:el[ \t]+)?(?:canal|grupo|bot|comunidad)(?:[ \t]+de)?)[ \t]+"
        r"(?:Telegram|WhatsApp|Discord)\b(?=\s*[:;,.\n]|$)",
        "",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"[ \t]+(?:vía|via)[ \t]+(?:Telegram|WhatsApp|Discord)\b(?=\s*[:;,.\n]|$)",
        "",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(
        r"\b(?:Telegram|WhatsApp|Discord)\s+(?:VIP|oficial|bot|canal|grupo|channel|group|signals|señales|senales)\b",
        "",
        out,
        flags=re.IGNORECASE,
    )
    out = re.sub(r"\b(?:Canal VIP|Señales VIP)\b", "", out, flags=re.IGNORECASE)

    # 4. Purgar direcciones de billeteras cripto (TRC20 / EVM) para evitar bloqueos anti-phishing
    out = re.sub(r"\bT[1-9A-HJ-NP-Za-km-z]{33}\b", "", out)
    out = re.sub(r"\b0x[a-fA-F0-9]{40}\b", "", out)
    return out


def _strip_editorial_noise(text: str) -> str:
    """Elimina menciones prohibidas (ArcaFid, FinBERT, frases vendehumos) y emojis promocionales."""
    if not text:
        return ""
    out = text
    for pat in _EDITORIAL_NOISE_PATTERNS:
        out = pat.sub("", out)
    out = re.sub(r"[ \t]+\(\s*\)(?=[.,;:!?\s]|$)", "", out)
    out = re.sub(r"\(\s*\)", "", out)
    out = re.sub(r"[ \t]+([,.;:!?])", r"\1", out)
    out = re.sub(r"[,;:]+\.", ".", out)
    out = re.sub(r"(?<=\S)[ \t]{2,}", " ", out)
    out = re.sub(r"[ \t]+\n", "\n", out)
    return out


def _sanitize_editorial_text(text: str, max_chars: int | None = None) -> str:
    """Sanitiza un fragmento de entrada de texto antes de ensamblarlo en una plantilla Square."""
    if not text or not str(text).strip():
        return ""
    out = sanitize_for_square(str(text), max_chars=None)
    out = _strip_external_ctas_and_links(out)
    # Eliminar hashtags inyectados en fragmentos de cuerpo para no consumir el cupo de pie (<= 3)
    out = re.sub(r"(?<!\w)#\w+", "", out)
    out = _strip_editorial_noise(out)
    out = re.sub(r"^[ \t]+", "", out, flags=re.MULTILINE)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    out = re.sub(r"^[\s.,;:]+", "", out).strip()
    out = re.sub(r"[,;:]+$", "", out).strip()
    if not re.search(r"[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ]", out):
        return ""
    if max_chars is not None and max_chars > 0:
        out = sanitize_for_square(out, max_chars=max_chars).strip()
    return out


class BinanceSquareContentGenerator:
    """Generador dinámico de publicaciones para Binance Square con tono sobrio de inversor veterano.

    Arquetipos soportados (Proyecto Fehu (ᚠ) Quantitative — cero misticismo ni lenguaje promocional):
    1. Nota de Estructura y Setup Cuantitativo (`generate_quant_setup_post`).
    2. Pulso Macro, Liquidez y Flujo de Sesión (`generate_macro_market_report`).
    3. Auditoría de Riesgo y Rendimiento Verificado (`generate_audited_performance_report`).
    4. Bitácora de Cierre Táctico (`generate_trade_close_post`).
    5. Nota de Calibración Walk-Forward (`generate_recalibration_note`).
    6. Síntesis de Estructura y Disciplina de Riesgo (`generate_market_structure_digest`).
    """

    MAX_CHARS: int = 1950
    SIGNATURE_PREFIX: str = "— Proyecto Fehu (ᚠ) Quantitative"
    HASHTAGS: str = "#TradingCuantitativo #GestionDeRiesgo #BinanceSquare"
    _STABLE_OR_FIAT: set[str] = {"USD", "USDT", "USDC", "FDUSD", "TUSD", "BUSD", "PYUSD", "DAI", "EUR"}

    @staticmethod
    def sanitize_text(text: str, max_chars: int | None = 1950) -> str:
        return sanitize_for_square(text, max_chars=max_chars)

    @classmethod
    def _base_symbol(cls, symbol: str) -> str:
        sym = (symbol or "BTC").strip().upper().lstrip("#$")
        for quote in ("USDT", "USDC", "FDUSD", "BUSD", "TUSD", "USD"):
            if len(sym) > len(quote) and sym.endswith(quote):
                return sym[: -len(quote)]
        return sym

    @classmethod
    def _format_price(cls, price: float) -> str:
        """Formatea precios numéricos con precisión adaptativa evitando notación científica."""
        if price <= 0:
            return "n/d"
        if price >= 1000.0:
            return f"{price:,.2f}"
        elif price >= 1.0:
            return f"{price:.2f}"
        elif price >= 0.01:
            return f"{price:.4f}"
        else:
            return f"{price:.8f}"

    @staticmethod
    def _pick_variant(seed_text: str, options: tuple[str, ...]) -> str:
        idx = sum(ord(ch) for ch in seed_text) % len(options)
        return options[idx]

    @staticmethod
    def _format_volume(volume_usdt: float) -> str:
        """Formatea volumen en USDT de manera consistente ($X.XXB, $X.XM, $X,XXX)."""
        if volume_usdt >= 1_000_000_000.0:
            return f"${volume_usdt / 1_000_000_000.0:.2f}B"
        if volume_usdt >= 1_000_000.0:
            return f"${volume_usdt / 1_000_000.0:.1f}M"
        return f"${volume_usdt:,.0f}"

    @staticmethod
    def _clean_sentiment_label(sentiment_label: str) -> str:
        cleaned = _sanitize_editorial_text(sentiment_label or "Neutral", max_chars=80)
        return cleaned or "Neutral"

    @staticmethod
    def _strategy_display(strategy_mode: str) -> str:
        key = (strategy_mode or "").strip().lower()
        mapping = {
            "turtle_breakout": "Ruptura Donchian",
            "connors_rsi": "Retroceso RSI",
            "elder_triple": "Triple Pantalla",
            "williams_alligator": "Tendencia Alligator",
            "mean_reversion": "Reversión a la Media",
            "active_momentum": "Momentum Activo",
            "trend": "Tendencia Direccional",
            "breakout": "Ruptura de Rango",
            "pullback_trend": "Retroceso en Tendencia",
            "trend_following": "Seguimiento de Tendencia",
            "pullback": "Retroceso Táctico",
            "auto": "Modelo Adaptativo",
        }
        if not key:
            return ""
        if key in mapping:
            return mapping[key]
        return _sanitize_editorial_text(key.replace("_", " ").capitalize(), max_chars=48)

    @classmethod
    def generate_quant_setup_post(
        cls,
        symbol: str,
        action: str,
        entry_price: float,
        stop_price: float,
        tp1: float,
        tp2: float,
        tp3: float,
        composite_score: float,
        timeframe: str = "15m",
        thesis: str = "",
        strategy_mode: str = "",
        sentiment_label: str = "",
        sentiment_score: float | None = None,
    ) -> str:
        """Genera publicación de setup cuantitativo sin sesgos promocionales ni R:R maquillado."""
        base = cls._base_symbol(symbol)
        pair_display = f"{base}USDT" if not (symbol or "").upper().endswith(("USDT", "USDC", "FDUSD", "BUSD")) else (symbol or "").upper().lstrip("#$")

        has_valid_stop = entry_price > 0 and stop_price > 0 and abs(entry_price - stop_price) > 0
        risk = abs(entry_price - stop_price) if has_valid_stop else 0.0
        reward = abs(tp3 - entry_price) if (entry_price > 0 and tp3 > 0) else 0.0
        rr = (reward / risk) if (risk > 0 and reward > 0) else None

        entry_str = cls._format_price(entry_price)
        stop_display_short = cls._format_price(stop_price) if has_valid_stop else "n/d"
        stop_display = f"{stop_display_short} USDT" if has_valid_stop else "n/d"
        stop_pct_str = (
            f" ({((stop_price - entry_price) / entry_price) * 100:+.2f}%)"
            if has_valid_stop
            else ""
        )
        tp1_str = cls._format_price(tp1)
        tp2_str = cls._format_price(tp2)
        tp3_str = cls._format_price(tp3)
        score_str = f"{composite_score:.3f}"
        rr_str = f"1:{rr:.2f}" if rr is not None else "n/d"

        if composite_score >= 0.85:
            score_band = "convicción alta"
        elif composite_score >= 0.72:
            score_band = "convicción moderada-alta"
        else:
            score_band = "sesgo táctico condicionado"

        act_low = (action or "BUY").strip().lower()
        is_long = act_low in {"buy", "long", "compra"}
        bias_word = "alcista" if is_long else "bajista"
        clean_tf = _sanitize_editorial_text(timeframe, max_chars=24) or "15m"

        if rr is None:
            rr_note_sentence = "Ratio R:R no calculable por ausencia de nivel de invalidación definido; la prioridad recae en dimensionar riesgo acotado."
        elif rr >= 2.5:
            rr_note_sentence = (
                "La asimetría proyectada hacia zonas superiores justifica seguimiento disciplinado mientras se sostenga el soporte."
                if is_long
                else "La asimetría proyectada hacia zonas inferiores justifica seguimiento disciplinado mientras se respete la resistencia."
            )
        elif rr >= 1.5:
            rr_note_sentence = "Asimetría moderada; la gestión exige asegurar reducción de riesgo al alcanzar la primera zona de liquidez."
        else:
            rr_note_sentence = "Asimetría ajustada; el margen de maniobra depende de la reacción de volumen en el primer objetivo."

        if is_long:
            default_theses = (
                "Confluencia de estructura direccional y expansión relativa de volumen sobre rango previo.",
                "Desequilibrio comprador en marco intradía respaldado por absorción en zona de demanda.",
                "Continuidad técnica sobre media de control con volatilidad contenida respecto al rango reciente.",
            )
        else:
            default_theses = (
                "Confluencia de estructura bajista y expansión relativa de volumen vendedor sobre rango previo.",
                "Desequilibrio vendedor en marco intradía respaldado por rechazo en zona de oferta.",
                "Continuidad bajista bajo media de control con volatilidad contenida respecto al rango reciente.",
            )
        clean_thesis = _sanitize_editorial_text(thesis, max_chars=750) if thesis else ""
        if not clean_thesis:
            clean_thesis = cls._pick_variant(f"{base}:{clean_tf}:{score_str}", default_theses)
        if "\n" in clean_thesis:
            quant_reading = f"{clean_thesis}\n{rr_note_sentence}"
        else:
            if clean_thesis[-1] not in ".!?":
                clean_thesis = f"{clean_thesis}."
            quant_reading = f"{clean_thesis} {rr_note_sentence}"

        optional_sent = ""
        if sentiment_label or sentiment_score is not None:
            clean_sent = cls._clean_sentiment_label(sentiment_label or "Neutral")
            s_val = f" ({sentiment_score:+.2f})" if sentiment_score is not None else ""
            optional_sent = f"• Sentimiento informativo (titulares RSS): {clean_sent}{s_val}\n"

        mode_label = cls._strategy_display(strategy_mode)
        mode_tag = f" | {mode_label}" if mode_label else ""
        if has_valid_stop:
            if is_long:
                questions = (
                    f"¿Validas la defensa en {stop_display_short} USDT o prefieres esperar confirmación de cierre sobre {tp1_str} USDT en ${base}?",
                    f"Con invalidación en {stop_display_short} USDT, ¿ves absorción suficiente en ${base} para sostener el tramo hacia {tp2_str} USDT?",
                    f"¿Cómo gestionarías parciales en ${base} si el volumen comprador se frena antes de {tp1_str} USDT?",
                )
            else:
                questions = (
                    f"¿Validas la invalidación en {stop_display_short} USDT o prefieres esperar confirmación de cierre bajo {tp1_str} USDT en ${base}?",
                    f"Con invalidación en {stop_display_short} USDT, ¿ves presión vendedora suficiente en ${base} para sostener el tramo hacia {tp2_str} USDT?",
                    f"¿Cómo gestionarías parciales en ${base} si el flujo vendedor se frena antes de {tp1_str} USDT?",
                )
        else:
            if is_long:
                questions = (
                    f"Sin nivel de invalidación fijo en referencia, ¿dónde ubicarías el soporte estructural clave de ${base} antes de proyectar hacia {tp1_str} USDT?",
                    f"Con referencia en {entry_str} USDT, ¿ves absorción suficiente en ${base} para sostener el tramo hacia {tp2_str} USDT?",
                )
            else:
                questions = (
                    f"Sin nivel de invalidación fijo en referencia, ¿dónde ubicarías la resistencia estructural clave de ${base} antes de proyectar hacia {tp1_str} USDT?",
                    f"Con referencia en {entry_str} USDT, ¿ves debilidad suficiente en ${base} para sostener el tramo hacia {tp2_str} USDT?",
                )
        closing_q = cls._pick_variant(f"q:{base}:{entry_str}", questions)

        raw_post = (
            f"${base} ({clean_tf}) | Sesgo {bias_word} en {entry_str} USDT — Invalidación en {stop_display_short}{stop_pct_str}\n\n"
            f"Lectura cuantitativa (Score {score_str} | {score_band} | R:R {rr_str}{mode_tag}):\n"
            f"{quant_reading}\n\n"
            f"Mapa técnico ({pair_display}):\n"
            f"• Referencia de entrada: {entry_str} USDT\n"
            f"• Invalidación estructural (SL): {stop_display}\n"
            f"• Zonas de liquidez (TP1 / TP2 / TP3): {tp1_str} / {tp2_str} / {tp3_str} USDT\n"
            f"{optional_sent}\n"
            f"{closing_q}\n\n"
            f"{cls.SIGNATURE_PREFIX} | Análisis informativo (DYOR), no constituye asesoramiento financiero.\n"
            f"{cls.HASHTAGS}"
        )
        return enforce_square_community_compliance(sanitize_for_square(raw_post, max_chars=None))

    @classmethod
    def generate_macro_market_report(
        cls,
        btc_price: float,
        btc_change_pct: float,
        top_gainers: list[dict[str, Any]],
        sentiment_label: str,
        sentiment_score: float,
        macro_summary: str = "",
        session_label: str = "",
        btc_high: float | None = None,
        btc_low: float | None = None,
        btc_volume_usdt: float | None = None,
    ) -> str:
        """Genera lectura macro y de liquidez con máximo 2 cashtags ($BTC + primer líder) y sin atribución falsa."""
        btc_price_str = cls._format_price(btc_price)
        btc_chg_str = f"{btc_change_pct:+.2f}%"
        sent_score_str = f"{sentiment_score:+.2f}"

        clean_session = _sanitize_editorial_text(session_label, max_chars=60) if session_label else ""
        if clean_session:
            session_title = clean_session
        else:
            hr = datetime.now(timezone.utc).hour
            session_title = "Sesión Asiática" if hr < 8 else ("Sesión Europea" if hr < 14 else "Sesión Americana")

        if btc_change_pct >= 3.0:
            regime_short = "expansión direccional alcista"
        elif btc_change_pct >= 0.5:
            regime_short = "avance ordenado sobre demanda"
        elif btc_change_pct > -0.5:
            regime_short = "compresión lateral de rango"
        elif btc_change_pct > -3.0:
            regime_short = "retroceso controlado en soporte"
        else:
            regime_short = "presión vendedora marcada"

        range_parts = []
        if btc_low is not None and btc_high is not None and btc_low > 0 and btc_high >= btc_low:
            amp_pct = ((btc_high - btc_low) / btc_low) * 100.0
            range_parts.append(f"rango 24h {cls._format_price(btc_low)}–{cls._format_price(btc_high)} ({amp_pct:.2f}%)")
        if btc_volume_usdt is not None and btc_volume_usdt > 0:
            range_parts.append(f"vol. {cls._format_volume(btc_volume_usdt)}")
        optional_range = f" | {' | '.join(range_parts)}" if range_parts else ""

        gainers_lines = []
        used_second_cashtag = False
        if top_gainers:
            for idx, g in enumerate(top_gainers[:5], start=1):
                base = cls._base_symbol(str(g.get("symbol", "")))
                prc = float(g.get("price", 0.0))
                chg = float(g.get("change_pct", 0.0))
                vol = float(g.get("quote_volume", 0.0))
                prc_str = cls._format_price(prc)
                vol_str = cls._format_volume(vol)
                if not used_second_cashtag and base and base != "BTC" and base not in cls._STABLE_OR_FIAT:
                    sym_disp = f"${base}"
                    used_second_cashtag = True
                else:
                    sym_disp = base or "ALT"
                gainers_lines.append(f"  {idx}. {sym_disp}: {prc_str} USDT ({chg:+.2f}% | Vol: {vol_str})")
        else:
            gainers_lines.append("  • Liquidez concentrada en los pares principales sin dispersión notable hacia altcoins.")

        gainers_block = "\n".join(gainers_lines)

        clean_macro = _sanitize_editorial_text(macro_summary, max_chars=700) if macro_summary else ""
        if not clean_macro:
            clean_macro = (
                f"Con $BTC en {regime_short}, la amplitud del mercado exige discriminar entre rotación genuina con volumen "
                f"y simples rebotes técnicos de baja profundidad antes de ampliar exposición."
            )
        clean_sent = cls._clean_sentiment_label(sentiment_label)

        questions = (
            "¿Observas rotación sostenible hacia altcoins de alta liquidez o solo cobertura táctica alrededor de $BTC?",
            "En este régimen de liquidez, ¿priorizas reducir exposición beta o buscar fuerza relativa frente a $BTC?",
            "¿Consideras saludable la amplitud actual de volumen para sostener rupturas fuera de $BTC?",
        )
        closing_q = cls._pick_variant(f"macro:{btc_price_str}:{regime_short}", questions)

        raw_post = (
            f"$BTC en {btc_price_str} USDT ({btc_chg_str}) | {session_title}: {regime_short} (RSS {sent_score_str})\n\n"
            f"Pulso de mercado y liquidez:\n"
            f"• Referencia $BTC: {btc_price_str} USDT ({btc_chg_str}){optional_range}\n"
            f"• Sentimiento informativo (titulares RSS): {clean_sent} ({sent_score_str})\n\n"
            f"Activos con mayor flujo relativo (vol. 24h > 5M USDT):\n"
            f"{gainers_block}\n\n"
            f"Lectura de mesa:\n"
            f"{clean_macro}\n\n"
            f"{closing_q}\n\n"
            f"{cls.SIGNATURE_PREFIX} | Lectura estadística informativa (DYOR), no constituye asesoramiento financiero.\n"
            f"#Bitcoin #Liquidez #BinanceSquare"
        )
        return enforce_square_community_compliance(sanitize_for_square(raw_post, max_chars=None))

    @classmethod
    def generate_audited_performance_report(
        cls,
        win_rate_pct: float,
        profit_factor: float | None,
        drawdown_lock_pct: float | None,
        sharpe_ratio: float | None,
        total_trades: int,
        source: str = "live_closed_trades",
    ) -> str:
        """Informe estadístico calculado desde operaciones reales o paper trading; sin valores inventados."""
        src_key = (source or "").strip().lower()
        origin_map = {
            "live_closed_trades": "operaciones reales cerradas",
            "closed_trades": "operaciones cerradas verificadas",
            "paper_trading": "simulación (paper trading, sin capital real)",
            "no_trades": "sin operaciones cerradas registradas",
            "backtest_walkforward": "validación histórica fuera de muestra (walk-forward)",
        }
        if src_key in origin_map:
            origin = origin_map[src_key]
        else:
            cleaned_src = _sanitize_editorial_text(str(source or "").replace("_", " "), max_chars=80)
            origin = cleaned_src or "registros verificados"
        pf = "n/d" if profit_factor is None else f"{profit_factor:.2f}"
        dd = "n/d" if drawdown_lock_pct is None else f"{drawdown_lock_pct:.1f}%"
        sh = "n/d" if sharpe_ratio is None else f"{sharpe_ratio:.2f}"

        hook_line = f"Bitácora de riesgo: Drawdown en {dd} tras {total_trades} operaciones (límite -6.4%)"
        if profit_factor is not None and profit_factor >= 1.5:
            discipline_note = (
                f"Con un Profit Factor de {pf} sobre {total_trades} registros y caída máxima contenida en {dd}, "
                "la prioridad operativa sigue siendo preservar asimetría positiva sin relajar los topes por posición."
            )
        else:
            discipline_note = (
                f"Sobre una muestra de {total_trades} registros y drawdown observado en {dd}, "
                "la regla central continúa siendo acotar exposición en fases de compresión y evitar sobreapalancamiento."
            )

        questions = (
            "En fases de menor acierto o rango estrecho, ¿prefieres reducir frecuencia operativa o ajustar tamaño por ATR?",
            "¿Qué umbral de drawdown máximo utilizas para frenar nuevas entradas y revisar calibración?",
        )
        closing_q = cls._pick_variant(f"perf:{total_trades}:{dd}", questions)

        raw_post = (
            f"{hook_line}\n\n"
            f"Métricas verificadas (origen: {origin}):\n"
            f"• Tasa de acierto (Win Rate): {win_rate_pct:.1f}%\n"
            f"• Factor de beneficio (Profit Factor): {pf}\n"
            f"• Máxima caída observada (Drawdown): {dd} (cerrojo fiduciario: -6.4%)\n"
            f"• Sharpe por operación (no anualizado): {sh}\n\n"
            f"Lectura de disciplina:\n"
            f"{discipline_note} El rendimiento pasado no garantiza resultados futuros.\n\n"
            f"{closing_q}\n\n"
            f"{cls.SIGNATURE_PREFIX} | Reporte estadístico informativo (DYOR), no constituye asesoramiento financiero.\n"
            f"#GestionDeRiesgo #TradingCuantitativo #BinanceSquare"
        )
        return enforce_square_community_compliance(sanitize_for_square(raw_post, max_chars=None))

    @classmethod
    def generate_trade_close_post(
        cls,
        symbol: str,
        exit_price: float,
        pnl_pct: float,
        pnl_usdt: float | None = None,
        reason: str = "",
        sentiment_label: str = "Neutral",
        sentiment_score: float = 0.0,
        entry_price: float | None = None,
        strategy_mode: str = "",
        close_reason: str = "",
    ) -> str:
        """Arquetipo 4: Post-mortem sobrio de cierre táctico en español sin códigos internos crípticos."""
        base = cls._base_symbol(symbol)
        pair_display = f"{base}USDT" if not (symbol or "").upper().endswith(("USDT", "USDC", "FDUSD", "BUSD")) else (symbol or "").upper().lstrip("#$")
        exit_str = cls._format_price(exit_price)
        effective_reason = close_reason or reason
        reason_human_es = translate_close_reason_es(effective_reason)
        clean_sent = cls._clean_sentiment_label(sentiment_label)
        sent_score_str = f"{sentiment_score:+.2f}"

        if pnl_pct >= 0.0:
            outcome_tag = "Objetivo asegurado" if "profit" in effective_reason.lower() or "target" in effective_reason.lower() else "Cierre en positivo"
            management_note = (
                "La ejecución respetó el plan de salida reduciendo exposición ante zonas de oferta, "
                "priorizando la consistencia estadística sobre intentar capturar el último tick."
            )
        else:
            outcome_tag = "Invalidación respetada"
            management_note = (
                "El límite de riesgo cerró la exposición antes de una extensión adversa mayor. "
                "Aceptar pérdidas acotadas preserva liquidez para esperar la siguiente asimetría favorable."
            )

        entry_line = ""
        if entry_price is not None and entry_price > 0:
            entry_line = f"• Referencia de entrada previa: {cls._format_price(entry_price)} USDT\n"

        mode_label = cls._strategy_display(strategy_mode)
        mode_note = f" — {mode_label}" if mode_label else ""
        questions = (
            f"Tras un cierre por {reason_human_es}, ¿priorizas esperar nueva compresión de volatilidad antes de reevaluar ${base}?",
            f"¿Cómo calibras tus salidas parciales en ${base} para equilibrar protección de capital y recorrido tendencial?",
        )
        closing_q = cls._pick_variant(f"close:{base}:{pnl_pct:+.2f}", questions)

        raw_post = (
            f"Cierre en ${base} a {exit_str} USDT | Resultado: {pnl_pct:+.2f}% ({outcome_tag})\n\n"
            f"Resumen de ejecución ({pair_display}{mode_note}):\n"
            f"{entry_line}"
            f"• Precio de salida: {exit_str} USDT\n"
            f"• Variación neta: {pnl_pct:+.2f}%\n"
            f"• Motivo estructural: {reason_human_es}\n"
            f"• Contexto informativo (RSS): {clean_sent} ({sent_score_str})\n\n"
            f"Nota de gestión:\n"
            f"{management_note}\n\n"
            f"{closing_q}\n\n"
            f"{cls.SIGNATURE_PREFIX} | Bitácora operativa informativa (DYOR), no constituye asesoramiento financiero.\n"
            f"#GestionDeRiesgo #TradingCuantitativo #BinanceSquare"
        )
        return enforce_square_community_compliance(sanitize_for_square(raw_post, max_chars=None))

    @classmethod
    def generate_recalibration_note(
        cls,
        tuned_summary: list[str] | str,
        sentiment_label: str = "Neutral",
        sentiment_score: float = 0.0,
        symbols: list[str] | None = None,
        market_context: str = "",
    ) -> str:
        """Arquetipo 5: Nota metodológica de calibración walk-forward con máximo 2 cashtags y 3 hashtags."""
        raw_lines = tuned_summary if isinstance(tuned_summary, list) else [ln for ln in str(tuned_summary).splitlines() if ln.strip()]
        normalized_lines: list[str] = []
        extracted_bases: list[str] = []

        if symbols:
            for s in symbols:
                b = cls._base_symbol(str(s))
                if b and b not in cls._STABLE_OR_FIAT and b not in extracted_bases:
                    extracted_bases.append(b)

        strategy_token_map = {
            "active_momentum": "Momentum Activo",
            "turtle_breakout": "Ruptura de Canal",
            "connors_rsi": "Retroceso en Tendencia",
            "elder_triple": "Triple Pantalla de Elder",
            "williams_alligator": "Tendencia Alligator",
            "mean_reversion": "Reversión a la Media",
            "pullback_trend": "Retroceso en Tendencia",
            "trend_following": "Seguimiento de Tendencia",
        }
        for ln in raw_lines[:6]:
            raw_ln = str(ln)
            m_sym = re.search(r"\b([A-Z0-9]{2,12})(?:USDT|USDC)\b", raw_ln.upper())
            if m_sym:
                b = cls._base_symbol(m_sym.group(1))
                if b and b not in cls._STABLE_OR_FIAT and b not in extracted_bases:
                    extracted_bases.append(b)
            clean_ln = re.sub(r"#([A-Z0-9]{2,14})(?:USDT|USDC|FDUSD|BUSD)?\b", lambda m: cls._base_symbol(m.group(1)), raw_ln)
            clean_ln = clean_ln.replace(" (Buy the Dip)", "").replace("(Buy the Dip)", "").replace("Buy the Dip", "Retroceso en tendencia")
            clean_ln = clean_ln.replace("Target R:R:", "Ratio R:R objetivo:")
            for s_tok, s_disp in strategy_token_map.items():
                clean_ln = re.sub(rf"\b{re.escape(s_tok)}\b", s_disp, clean_ln, flags=re.IGNORECASE)
            clean_ln = re.sub(
                r"\b([a-z]{2,}(?:_[a-z0-9]{2,})+)\b",
                lambda m: m.group(1).replace("_", " "),
                clean_ln,
            )
            clean_ln = _sanitize_editorial_text(clean_ln, max_chars=240)
            if not clean_ln:
                continue
            if not clean_ln.startswith("•"):
                clean_ln = f"• {clean_ln.lstrip('- ')}"
            normalized_lines.append(clean_ln)

        if not normalized_lines:
            normalized_lines.append("• Cartera general: revisión walk-forward sin cambios estructurales fuera de rango.")

        cashtag_assets = [f"${b}" for b in extracted_bases[:2]]
        hook_assets = " / ".join(cashtag_assets) if cashtag_assets else "de cartera"
        summary_block = "\n".join(normalized_lines)
        clean_sent = cls._clean_sentiment_label(sentiment_label)
        sent_score_str = f"{sentiment_score:+.2f}"

        context_body = _sanitize_editorial_text(market_context, max_chars=450) if market_context else ""
        if not context_body:
            context_body = (
                "La calibración ajusta multiplicadores de invalidación por ATR y umbrales de asimetría en función "
                "de la volatilidad realizada reciente, evitando sobreoptimizar sobre ruido de corto plazo."
            )

        questions = (
            "¿Ajustas tus paradas por múltiplo de ATR cuando cambia la volatilidad realizada o mantienes distancias fijas?",
            "¿Con qué frecuencia revisas tus parámetros de entrada para evitar sobreajuste fuera de muestra?",
        )
        closing_q = cls._pick_variant(f"recal:{hook_assets}:{len(normalized_lines)}", questions)

        raw_post = (
            f"Calibración walk-forward {hook_assets} | Ajuste de parámetros ATR según régimen de volatilidad\n\n"
            f"Parámetros actualizados fuera de muestra:\n"
            f"{summary_block}\n"
            f"• Contexto informativo (RSS): {clean_sent} ({sent_score_str})\n\n"
            f"Nota metodológica:\n"
            f"{context_body}\n\n"
            f"{closing_q}\n\n"
            f"{cls.SIGNATURE_PREFIX} | Bitácora metodológica informativa (DYOR), no constituye asesoramiento financiero.\n"
            f"#TradingCuantitativo #GestionDeRiesgo #BinanceSquare"
        )
        return enforce_square_community_compliance(sanitize_for_square(raw_post, max_chars=None))

    @classmethod
    def generate_market_structure_digest(
        cls,
        btc_price: float,
        btc_change_pct: float,
        top_movers: list[dict[str, Any]],
        sentiment_label: str,
        sentiment_score: float,
        theme_idx: int = 0,
        btc_high: float | None = None,
        btc_low: float | None = None,
    ) -> str:
        """Arquetipo 6: Síntesis rotativa de estructura y disciplina de riesgo cuando trades < 30."""
        btc_str = cls._format_price(btc_price)
        btc_chg_str = f"{btc_change_pct:+.2f}%"
        clean_sent = cls._clean_sentiment_label(sentiment_label)
        sent_score_str = f"{sentiment_score:+.2f}"

        amp_pct = None
        if btc_high is not None and btc_low is not None and btc_low > 0 and btc_high >= btc_low:
            amp_pct = ((btc_high - btc_low) / btc_low) * 100.0

        positive_movers = [m for m in (top_movers or []) if float(m.get("change_pct", 0.0)) > 0]
        first_pos_non_btc = next(
            (
                cls._base_symbol(str(m.get("symbol", "")))
                for m in positive_movers
                if cls._base_symbol(str(m.get("symbol", ""))) not in {"BTC", ""}
                and cls._base_symbol(str(m.get("symbol", ""))) not in cls._STABLE_OR_FIAT
            ),
            "",
        )
        leader_disp = f" frente a liderazgo puntual en ${first_pos_non_btc}" if first_pos_non_btc else ""

        amp_text = f"{amp_pct:.2f}%" if amp_pct is not None else "rango contenido"
        theme = theme_idx % 3

        if theme == 0:
            hook = f"Disciplina de riesgo con $BTC en {btc_str} USDT ({btc_chg_str}) | Amplitud intradía {amp_text}"
            body = (
                f"Con $BTC marcando {btc_chg_str} y una amplitud reciente de {amp_text}{leader_disp}, "
                "dimensionar el tamaño de posición de forma inversa al ATR evita que una sola sacudida intradía comprometa "
                "el presupuesto semanal de riesgo bajo el cerrojo de drawdown de -6.4%."
            )
            question = "En jornadas con amplitud moderada, ¿reduces tamaño por operación o amplías el margen de invalidación por ATR?"
        elif theme == 1:
            hook = f"Amplitud de liquidez: {len(positive_movers)}/{max(1, len(top_movers or []))} líderes líquidos en positivo | $BTC {btc_chg_str}"
            if positive_movers:
                body = (
                    f"La dispersión entre $BTC ({btc_str} USDT) y los pares de mayor volumen muestra qué segmentos reciben demanda real{leader_disp}. "
                    "Operar rupturas sin respaldo de amplitud suele elevar la tasa de barridos falsos en resistencias cercanas."
                )
            else:
                body = (
                    f"Con amplitud defensiva en $BTC ({btc_str} USDT) y los pares de mayor volumen en terreno negativo, "
                    "la dispersión refleja rotación cautelosa y preservación de liquidez. "
                    "Forzar rupturas alcistas sin respaldo de amplitud suele elevar la tasa de barridos falsos en resistencias cercanas."
                )
            question = "¿Qué peso asignas a la amplitud de pares líderes antes de validar una ruptura en tu activo principal?"
        else:
            hook = f"Control de asimetría en $BTC ({btc_str} USDT) | Lectura de titulares RSS {sent_score_str}"
            body = (
                f"Con el flujo informativo en tono {clean_sent} ({sent_score_str}), la ventaja estadística no proviene de predecir titulares, "
                "sino de exigir niveles de invalidación verificables antes de comprometer liquidez."
            )
            question = "¿Exiges relación riesgo/beneficio mínima fija o adaptas el primer objetivo a la liquidez estructural cercana?"

        raw_post = (
            f"{hook}\n\n"
            f"Lectura de estructura y riesgo:\n"
            f"• Referencia $BTC: {btc_str} USDT ({btc_chg_str}) | Amplitud: {amp_text}\n"
            f"• Sentimiento informativo (titulares RSS): {clean_sent} ({sent_score_str})\n"
            f"• Marco fiduciario activo: límite de caída máxima en -6.4% y dimensionamiento por volatilidad\n\n"
            f"Criterio operativo:\n"
            f"{body}\n\n"
            f"{question}\n\n"
            f"{cls.SIGNATURE_PREFIX} | Síntesis educativa de mercado (DYOR), no constituye asesoramiento financiero.\n"
            f"#GestionDeRiesgo #TradingCuantitativo #BinanceSquare"
        )
        return enforce_square_community_compliance(sanitize_for_square(raw_post, max_chars=None))


def enforce_square_community_compliance(text: str) -> str:
    """Filtro estricto de cumplimiento comunitario para Binance Square OpenAPI (Prevención Código 30023 / 200001 / 220094 / 220095).

    Elimina en la frontera de red cualquier vector de redirección externa o captación fuera de plataforma:
    - Enlaces web externos (https://, github.io, t.me/, wa.me/, discord.gg/, dominios de terceros).
    - Invitaciones/CTAs a Telegram, WhatsApp, Discord, canales VIP, @handles y comandos (/subscribe, /plans, /vip),
      preservando menciones informativas legítimas de noticias (ej. "El CEO de Telegram..." o "Telegram mini-app").
    - Direcciones de billeteras cripto (TRC20 / ERC20 / BEP20).
    - Adapta nomenclatura de ejecución a lenguaje estrictamente analítico/educativo en reportes multilínea.
    - Deduplica cashtags ($COIN) a máximo 2 pares únicos (soporta $1000PEPE, excluye $USDT/$USD/$USDC).
    - Elimina hashtags excedentes (> 3) sin dejar palabras huérfanas (regla 220094) y asegura DYOR antes de truncar.
    """
    if not text:
        return ""

    out = _strip_external_ctas_and_links(text)

    # 5. En reportes multilínea estructurados, transformar terminología de señal operativa a análisis técnico educativo
    is_multiline_report = "\n" in out and len(out) > 120
    if is_multiline_report:
        replacements = [
            ("Niveles clave de la operación:", "Zonas técnicas de referencia en el gráfico:"),
            ("• Entrada de referencia:", "• Zona de equilibrio observada:"),
            ("• Stop Loss de protección:", "• Nivel de invalidación de estructura:"),
            ("• Primer objetivo:", "• Resistencia técnica 1:"),
            ("(tomamos parcial y protegemos en punto de entrada)", "(zona de liquidez primaria)"),
            ("• Segundo objetivo:", "• Resistencia técnica 2:"),
            ("• Tercer objetivo:", "• Resistencia técnica 3:"),
            ("Detectamos una configuración de compra (BUY)", "Observamos una estructura técnica alcista"),
        ]
        for old_str, new_str in replacements:
            out = out.replace(old_str, new_str)

    # 6. Convertir menciones #COIN a cashtags ($COIN), excluir stablecoins/fiat,
    # soportar prefijos numéricos ($1000PEPE, $1INCH) y deduplicar a máximo 2 pares únicos (error 220095).
    stable_or_fiat = {"USD", "USDT", "USDC", "FDUSD", "TUSD", "BUSD", "PYUSD", "DAI", "EUR"}

    def _replace_hash_pair(m: re.Match[str]) -> str:
        base = m.group(1)
        return base if base in stable_or_fiat else f"${base}"

    out = re.sub(r"#([A-Z0-9]{2,14})USDT\b", _replace_hash_pair, out)
    out = re.sub(
        r"#(1000PEPE|1000SATS|1000SHIB|1000FLOKI|1000BONK|1INCH|BTC|ETH|SOL|BNB|XRP|ADA|DOGE|AVAX|LINK|DOT|NEAR|SUI|PEPE|SHIB|TON|LTC|TRX|ARB|OP|APT|INJ|UNI|AAVE)\b",
        r"$\1",
        out,
    )
    out = re.sub(r"\$(USDT|USDC|USD|FDUSD|TUSD|BUSD|PYUSD|DAI|EUR)\b", r"\1", out)

    cashtag_pattern = re.compile(r"\$(?!\d+(?:[KMBT]|MM|BN)?\b)((?:[0-9]{1,5})?[A-Z]{2,10}(?:[0-9]{1,3})?)\b")
    cashtags = list(cashtag_pattern.finditer(out))
    if cashtags:
        seen_coins: list[str] = []
        out_parts: list[str] = []
        last_idx = 0
        for m in cashtags:
            sym = m.group(1)
            out_parts.append(out[last_idx:m.start()])
            if sym in seen_coins:
                out_parts.append(m.group(0))
            elif len(seen_coins) < 2:
                seen_coins.append(sym)
                out_parts.append(m.group(0))
            else:
                out_parts.append(sym)
            last_idx = m.end()
        out_parts.append(out[last_idx:])
        out = "".join(out_parts)

    # 7. Limitar hashtags a máximo 3 eliminando limpiamente los excedentes (Unicode español sin huérfanos; error 220094)
    matches = list(re.finditer(r"(?<!&)#(\w+)", out))
    if len(matches) > 3:
        out_parts = []
        last_idx = 0
        for i, m in enumerate(matches):
            out_parts.append(out[last_idx:m.start()])
            if i < 3:
                out_parts.append(m.group(0))
            last_idx = m.end()
        out_parts.append(out[last_idx:])
        out = "".join(out_parts)

    # 7b. Purgar ruido editorial (ArcaFid, FinBERT, frases/emojis promocionales) después de acotar hashtags
    out = _strip_editorial_noise(out)

    # 8. Asegurar descargo educativo (DYOR) ANTES de truncar por longitud
    if is_multiline_report:
        low_out = out.lower()
        if "no es asesoramiento financiero" not in low_out and "no constituye asesoramiento financiero" not in low_out:
            disclaimer = "Nota: Análisis cuantitativo estrictamente educativo e informativo (DYOR). No constituye asesoramiento financiero."
            hashtag_match = re.search(r"\n+(#\w+(?:[ \t]+#\w+)*)\s*$", out)
            if hashtag_match:
                prefix = out[:hashtag_match.start()].rstrip()
                suffix = hashtag_match.group(1).strip()
                out = f"{prefix}\n\n{disclaimer}\n\n{suffix}"
            else:
                out = f"{out.rstrip()}\n\n{disclaimer}"

    # 9. Normalizar espacios residuales y garantizar límite <= 1950 caracteres preservando DYOR/hashtags
    out = re.sub(r"[ \t]+\(\s*\)(?=[.,;:!?\s]|$)", "", out)
    out = re.sub(r"\(\s*\)", "", out)
    out = re.sub(r"(?<=\S)[ \t]{2,}", " ", out)
    out = re.sub(r"[ \t]+\n", "\n", out)
    out = re.sub(r"[ \t]+$", "", out, flags=re.MULTILINE)
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    if len(out) > 1950:
        out = sanitize_for_square(out, max_chars=1950)
    return out


class SquareRateLimiter:
    """Limitador de frecuencia híbrido con ventana deslizante horaria, espaciado de cooldown, deduplicación
    y disyuntor automático (Circuit Breaker) ante restricciones comunitarias (código 30023 / 200001).
    
    Persistencia atómica de estado en tabla `bot_state` de SQLite (ON CONFLICT DO UPDATE).
    """

    def __init__(
        self,
        db_path: str = "bot_events.sqlite3",
        rate_limit_per_hour: int = 5,
        min_cooldown_seconds: float = 900.0,
        priority_cooldown_seconds: float | None = None,
    ) -> None:
        self.db_path = db_path
        self.rate_limit_per_hour = rate_limit_per_hour
        self.min_cooldown_seconds = min_cooldown_seconds
        self.priority_cooldown_seconds = priority_cooldown_seconds
        self.last_post_ts: float = 0.0
        self.hourly_timestamps: list[float] = []
        self.recent_hashes: list[dict[str, Any]] = []
        self.restriction_until_ts: float = 0.0
        self.restriction_code: str = ""
        self._lock = threading.Lock()
        self._init_db_and_load_state()

    def _init_db_and_load_state(self) -> None:
        if not self.db_path:
            return
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            try:
                with conn:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS bot_state (
                            key TEXT PRIMARY KEY,
                            updated_ts TEXT NOT NULL,
                            value_json TEXT NOT NULL
                        );
                        """
                    )
                cur = conn.cursor()
                cur.execute("SELECT value_json FROM bot_state WHERE key = 'binance_square:rate_limit'")
                row = cur.fetchone()
                if row and row[0]:
                    data = json.loads(row[0])
                    self.last_post_ts = float(data.get("last_post_ts", 0.0))
                    self.hourly_timestamps = [float(ts) for ts in data.get("hourly_timestamps", [])]
                    self.recent_hashes = list(data.get("recent_hashes", []))
                    self.restriction_until_ts = float(data.get("restriction_until_ts", 0.0))
                    self.restriction_code = str(data.get("restriction_code", ""))
            finally:
                conn.close()
        except Exception as exc:
            logging.debug("Error inicializando estado SQLite de SquareRateLimiter: %s", exc)

    def _save_state(self) -> None:
        if not self.db_path:
            return
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            try:
                now_iso = datetime.now(timezone.utc).isoformat()
                payload = json.dumps(
                    {
                        "last_post_ts": self.last_post_ts,
                        "hourly_timestamps": self.hourly_timestamps,
                        "recent_hashes": self.recent_hashes,
                        "restriction_until_ts": self.restriction_until_ts,
                        "restriction_code": self.restriction_code,
                    }
                )
                with conn:
                    conn.execute(
                        """
                        INSERT INTO bot_state (key, updated_ts, value_json)
                        VALUES ('binance_square:rate_limit', ?, ?)
                        ON CONFLICT(key) DO UPDATE SET
                            updated_ts = EXCLUDED.updated_ts,
                            value_json = EXCLUDED.value_json;
                        """,
                        (now_iso, payload),
                    )
            finally:
                conn.close()
        except Exception as exc:
            logging.debug("Error guardando estado SQLite de SquareRateLimiter: %s", exc)

    def is_restricted(self) -> tuple[bool, str]:
        """Verifica si el disyuntor de protección comunitaria (30023 / 200001) está activo."""
        with self._lock:
            now = time.time()
            if self.restriction_until_ts > now:
                rem_min = max(1, int((self.restriction_until_ts - now) / 60.0))
                return True, (
                    f"Compliance circuit breaker active (code {self.restriction_code or '30023'}): "
                    f"paused for {rem_min}m to protect Binance Square account"
                )
            return False, "OK"

    def record_restriction(self, code: str, cooldown_hours: float = 24.0) -> None:
        """Activa una cuarentena preventiva tras recibir un código de restricción o advertencia comunitaria."""
        with self._lock:
            now = time.time()
            self.restriction_code = str(code)
            self.restriction_until_ts = now + max(float(cooldown_hours) * 3600.0, 300.0)
            self._save_state()

    def can_publish(self, text: str, is_priority_alert: bool = False) -> tuple[bool, str]:
        """Evalúa si una publicación cumple con el disyuntor de seguridad, límites de frecuencia, cooldown y deduplicación."""
        with self._lock:
            now = time.time()

            # 0. Verificar disyuntor de restricción comunitaria (código 30023 / 200001)
            if self.restriction_until_ts > now:
                rem_min = max(1, int((self.restriction_until_ts - now) / 60.0))
                return False, (
                    f"Compliance circuit breaker active (code {self.restriction_code or '30023'}): "
                    f"rate limit cooldown active for {rem_min}m"
                )

            # 1. Limpiar ventana deslizante horaria (últimos 3600 segundos)
            self.hourly_timestamps = [ts for ts in self.hourly_timestamps if now - ts < 3600.0]

            # 2. Verificar cupo máximo por hora
            if len(self.hourly_timestamps) >= self.rate_limit_per_hour:
                return False, f"Hourly rate limit exceeded: {len(self.hourly_timestamps)}/{self.rate_limit_per_hour} posts in the last hour"

            # 3. Verificar deduplicación de contenido (MD5 en ventana de 24 horas)
            content_hash = hashlib.md5(text.strip().encode("utf-8")).hexdigest()
            self.recent_hashes = [h for h in self.recent_hashes if now - float(h.get("ts", 0.0)) < 86400.0]
            for h in self.recent_hashes:
                if h.get("hash") == content_hash:
                    return False, "Duplicate content detected within 24 hours"

            # 4. Verificar tiempo de enfriamiento (cooldown)
            # Para min_cooldown <= 900s (15m) se mantiene 180s; si min_cooldown > 900s (ej. 60m) escala a 50% (min 900s)
            if is_priority_alert:
                if self.priority_cooldown_seconds is not None:
                    cooldown = min(self.min_cooldown_seconds, max(0.0, float(self.priority_cooldown_seconds)))
                elif self.min_cooldown_seconds <= 900.0:
                    cooldown = min(180.0, self.min_cooldown_seconds)
                else:
                    cooldown = max(900.0, self.min_cooldown_seconds * 0.5)
            else:
                cooldown = self.min_cooldown_seconds
            elapsed = now - self.last_post_ts
            if elapsed < cooldown and self.last_post_ts > 0.0:
                remaining = int(cooldown - elapsed)
                return False, f"Rate limit cooldown active: please wait {remaining}s before posting"

            return True, "OK"

    def record_published(self, text: str) -> None:
        """Registra una publicación confirmada actualizando contadores y persistiendo estado."""
        with self._lock:
            now = time.time()
            self.last_post_ts = now
            self.hourly_timestamps.append(now)
            content_hash = hashlib.md5(text.strip().encode("utf-8")).hexdigest()
            self.recent_hashes.append({"hash": content_hash, "ts": now})
            self._save_state()


class BinanceSquarePublisher:
    """Cliente HTTP robusto para la publicación autónoma en Binance Square OpenAPI.
    
    Implementa:
    - Validación de cabecera X-Square-OpenAPI-Key.
    - Filtro de cumplimiento comunitario (`enforce_square_community_compliance`) y disyuntor 30023.
    - Reintentos con retroceso exponencial y jitter ante errores HTTP 429, 500, 502, 503 y timeouts.
    - Degradación elegante en modo simulación/standby cuando la API no está configurada.
    - Registro de telemetría fiduciaria en la tabla `events` de SQLite (`bot_events.sqlite3`).
    """

    API_URL = "https://www.binance.com/bapi/composite/v1/public/pgc/openApi/content/add"
    RETRY_BACKOFF_BASE = 2.0

    def __init__(self, cfg: BotConfig) -> None:
        self.cfg = cfg
        self.api_key = (cfg.binance_square_api_key or "").strip()
        self.enabled = bool(cfg.binance_square_enabled and self.api_key)
        self.dry_run = getattr(cfg, "binance_square_dry_run", False)
        self.db_path = getattr(cfg, "event_db_path", "bot_events.sqlite3")
        self.retry_backoff_base = float(getattr(cfg, "binance_square_retry_backoff_seconds", self.RETRY_BACKOFF_BASE) or self.RETRY_BACKOFF_BASE)

        rate_limit = getattr(cfg, "binance_square_rate_limit_per_hour", 5)
        cooldown_min = getattr(cfg, "binance_square_min_cooldown_minutes", 15)
        priority_cooldown = getattr(cfg, "binance_square_priority_cooldown_seconds", None)
        self.rate_limiter = SquareRateLimiter(
            db_path=self.db_path,
            rate_limit_per_hour=rate_limit,
            min_cooldown_seconds=float(cooldown_min * 60.0),
            priority_cooldown_seconds=priority_cooldown,
        )

    def _backoff_seconds(self, attempt: int) -> float:
        base = self.retry_backoff_base * (2 ** (attempt - 1))
        jitter = random.uniform(0.05, 0.25) if self.retry_backoff_base >= 1.0 else random.uniform(0.01, 0.05)
        return base + jitter

    @staticmethod
    def _hours_until_utc_midnight() -> float:
        now_utc = datetime.now(timezone.utc)
        next_midnight = (now_utc + timedelta(days=1)).replace(hour=0, minute=0, second=5, microsecond=0)
        return max(0.25, (next_midnight - now_utc).total_seconds() / 3600.0)

    def sanitize_text(self, text: str, max_chars: int = 1950) -> str:
        return sanitize_for_square(text, max_chars=max_chars)

    def _record_event(self, mode: str, symbol: str, event: str, payload: dict[str, Any]) -> None:
        """Persiste eventos de telemetría en SQLite asegurando el cierre inmediato de la conexión."""
        if not self.db_path:
            return
        try:
            conn = sqlite3.connect(self.db_path, timeout=10.0)
            try:
                with conn:
                    conn.execute(
                        """
                        CREATE TABLE IF NOT EXISTS events (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            ts TEXT NOT NULL,
                            mode TEXT NOT NULL,
                            symbol TEXT NOT NULL,
                            event TEXT NOT NULL,
                            payload_json TEXT NOT NULL
                        );
                        """
                    )
                    now_iso = datetime.now(timezone.utc).isoformat()
                    payload_json = json.dumps(payload, default=str)
                    conn.execute(
                        "INSERT INTO events (ts, mode, symbol, event, payload_json) VALUES (?, ?, ?, ?, ?)",
                        (now_iso, mode, symbol, event, payload_json),
                    )
            finally:
                conn.close()
        except Exception as exc:
            logging.debug("Error registrando telemetría SQLite en BinanceSquarePublisher: %s", exc)

    def publish_post(
        self,
        text: str,
        is_priority_alert: bool = False,
        metadata: dict[str, Any] | None = None,
        check_rate_limit: bool = False,
    ) -> bool:
        """Envía una publicación a Binance Square OpenAPI con reintentos y telemetría SQLite.

        Retorna True si la publicación fue enviada o simulada exitosamente; False ante rechazo o error.
        """
        sym = (metadata or {}).get("symbol", "GLOBAL")

        # 1. Modo simulación / standby si el servicio está deshabilitado o la API Key está vacía
        if not self.enabled:
            if self.dry_run or (self.cfg.binance_square_enabled and not self.api_key):
                logging.info("[SIMULATION] Publicador de Binance Square en modo simulación (sin llamadas de red).")
                sim_text = sanitize_for_square(
                    enforce_square_community_compliance(sanitize_for_square(text, max_chars=None)),
                    max_chars=1950,
                )
                self._record_event(
                    mode="binance_square",
                    symbol=sym,
                    event="binance_square_simulation",
                    payload={"status": "simulated", "text": sim_text[:300], "metadata": metadata or {}},
                )
            return False

        # 1b. Verificar siempre si existe una restricción comunitaria activa para no insistir contra la API
        restricted, rest_reason = self.rate_limiter.is_restricted()
        if restricted:
            logging.warning("Publicación en Binance Square omitida por cuarentena de seguridad: %s", rest_reason)
            self._record_event(
                mode="binance_square",
                symbol=sym,
                event="binance_square_rate_limited",
                payload={"reason": rest_reason, "text": text[:300], "metadata": metadata or {}},
            )
            return False

        # 2. Normalizar -> cumplimiento comunitario -> truncar a <= 1950 -> guardia cuerpo vacío (220011)
        normalized_text = sanitize_for_square(text, max_chars=None)
        compliant_text = enforce_square_community_compliance(normalized_text)
        square_clean_text = sanitize_for_square(compliant_text, max_chars=1950).strip()

        if not square_clean_text:
            logging.warning(
                "Publicación en Binance Square omitida: contenido vacío tras sanitización/cumplimiento (prevención 220011)."
            )
            self._record_event(
                mode="binance_square",
                symbol=sym,
                event="binance_square_failed",
                payload={
                    "status": "validation_error",
                    "code": "220011",
                    "reason": "empty_body_after_compliance",
                    "metadata": metadata or {},
                },
            )
            return False

        # 3. Comprobación opcional de rate limit & dedup alineada sobre square_clean_text
        if check_rate_limit:
            can_pub, reason = self.rate_limiter.can_publish(square_clean_text, is_priority_alert=is_priority_alert)
            if not can_pub:
                logging.warning("Publicación en Binance Square bloqueada por rate limiter: %s", reason)
                self._record_event(
                    mode="binance_square",
                    symbol=sym,
                    event="binance_square_rate_limited",
                    payload={"reason": reason, "text": square_clean_text[:300], "metadata": metadata or {}},
                )
                return False

        headers = {
            "X-Square-OpenAPI-Key": self.api_key,
            "Content-Type": "application/json",
            "clienttype": "binanceSkill",
        }
        payload = {
            "bodyTextOnly": square_clean_text,
        }

        # 4. Modo dry-run explícito configurado
        if self.dry_run:
            logging.info("[DRY_RUN] Publicación en Binance Square simulada exitosamente: %s", square_clean_text[:100])
            self._record_event(
                mode="binance_square",
                symbol=sym,
                event="binance_square_simulation",
                payload={
                    "status": "dry_run",
                    "text": square_clean_text[:300],
                    "text_length": len(square_clean_text),
                    "metadata": metadata or {},
                },
            )
            self.rate_limiter.record_published(square_clean_text)
            return True

        # 4b. Guardia de seguridad en pruebas para impedir llamadas HTTP reales no mockeadas
        if _is_unmocked_test_http_call():
            logging.warning(
                "[TEST-SAFETY-GUARD] Llamada HTTP real a Binance Square bloqueada durante ejecución de pruebas."
            )
            self._record_event(
                mode="binance_square",
                symbol=sym,
                event="binance_square_simulation",
                payload={
                    "status": "test_guard_blocked",
                    "text": square_clean_text[:300],
                    "metadata": metadata or {},
                },
            )
            return False

        # 5. Envío HTTP con reintentos limpios y retroceso exponencial con jitter
        max_attempts = 4
        last_error_msg = ""

        for attempt in range(1, max_attempts + 1):
            try:
                logging.info("Enviando publicación a Binance Square (intento %d/%d)...", attempt, max_attempts)
                response = requests.post(
                    self.API_URL,
                    json=payload,
                    headers=headers,
                    timeout=15,
                )

                # Manejo de Rate Limit HTTP 429
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    try:
                        wait_seconds = float(retry_after) if retry_after else self._backoff_seconds(attempt)
                    except (ValueError, TypeError):
                        wait_seconds = self._backoff_seconds(attempt)

                    logging.warning("HTTP 429 en Binance Square. Esperando %.2fs antes de reintentar...", wait_seconds)
                    if attempt < max_attempts:
                        time.sleep(wait_seconds)
                        continue
                    else:
                        response.raise_for_status()

                # Manejo de errores de servidor HTTP 500, 502, 503
                if response.status_code in {500, 502, 503}:
                    wait_seconds = self._backoff_seconds(attempt)
                    logging.warning("HTTP %d en Binance Square. Esperando %.2fs para reintento...", response.status_code, wait_seconds)
                    if attempt < max_attempts:
                        time.sleep(wait_seconds)
                        continue
                    else:
                        response.raise_for_status()

                # HTTP 504 Gateway Timeout: no reintentar ciegamente para evitar publicaciones duplicadas
                if response.status_code == 504:
                    logging.warning(
                        "HTTP 504 Gateway Timeout en Binance Square: se omite reintento automático para evitar publicaciones duplicadas."
                    )
                    self._record_event(
                        mode="binance_square",
                        symbol=sym,
                        event="binance_square_failed",
                        payload={
                            "status": "gateway_timeout_no_retry",
                            "http_status": 504,
                            "reason": "504_avoid_duplicate_retry",
                            "metadata": metadata or {},
                        },
                    )
                    return False

                # Errores de cliente HTTP 400, 401, 403: no reintentar
                if response.status_code in {400, 401, 403}:
                    try:
                        err_json = response.json()
                    except Exception:
                        err_json = {"raw": response.text[:200]}
                    err_code = str(err_json.get("code", "")) if isinstance(err_json, dict) else ""
                    if err_code in {"220003", "220004", "10005"}:
                        self.rate_limiter.record_restriction(err_code, cooldown_hours=24.0)
                        logging.critical(
                            "Error crítico de credenciales/KYC Binance Square (código %s, HTTP %d). Cuarentena 24h: %s",
                            err_code,
                            response.status_code,
                            err_json,
                        )
                    else:
                        logging.error("Error HTTP %d de Binance Square (no recuperable): %s", response.status_code, err_json)
                    self._record_event(
                        mode="binance_square",
                        symbol=sym,
                        event="binance_square_failed",
                        payload={
                            "http_status": response.status_code,
                            "code": err_code,
                            "response": err_json,
                            "metadata": metadata or {},
                        },
                    )
                    return False

                # Validar códigos de respuesta HTTP exitosos
                response.raise_for_status()

                try:
                    res_data = response.json()
                except Exception:
                    res_data = {}

                # Verificar códigos de negocio de Binance OpenAPI
                is_success = (
                    res_data.get("code") == "000000"
                    or res_data.get("success") is True
                    or res_data.get("status") == "success"
                )

                if is_success:
                    post_id = ""
                    share_link = ""
                    if isinstance(res_data.get("data"), dict):
                        post_id = str(res_data["data"].get("id", ""))
                        share_link = str(res_data["data"].get("shareLink", ""))
                    logging.info(
                        "Publicación en Binance Square enviada con éxito (ID: %s, URL: %s).",
                        post_id or "N/A",
                        share_link or "N/A",
                    )
                    self.rate_limiter.record_published(square_clean_text)
                    self._record_event(
                        mode="binance_square",
                        symbol=sym,
                        event="binance_square_published",
                        payload={
                            "status": "published",
                            "post_id": post_id,
                            "share_link": share_link,
                            "api_response": res_data,
                            "metadata": metadata or {},
                        },
                    )
                    return True
                else:
                    err_code = str(res_data.get("code", ""))
                    if err_code == "10004":
                        last_error_msg = f"Binance Square transient error 10004: {res_data}"
                        if attempt < max_attempts:
                            wait_seconds = self._backoff_seconds(attempt)
                            logging.warning(
                                "Error transitorio de red Binance Square (código 10004, intento %d/%d). Reintentando en %.2fs...",
                                attempt,
                                max_attempts,
                                wait_seconds,
                            )
                            time.sleep(wait_seconds)
                            continue
                        logging.error("Error transitorio 10004 persistió tras %d intentos: %s", max_attempts, res_data)
                        self._record_event(
                            mode="binance_square",
                            symbol=sym,
                            event="binance_square_failed",
                            payload={
                                "status": "business_error",
                                "code": "10004",
                                "api_response": res_data,
                                "metadata": metadata or {},
                            },
                        )
                        return False
                    elif err_code == "30023":
                        self.rate_limiter.record_restriction("30023", cooldown_hours=24.0)
                        logging.warning(
                            "Aviso Binance Square: La cuenta tiene una restricción temporal comunitaria activa (código 30023). "
                            "Disyuntor activado por 24h para proteger la cuenta y evitar penalizaciones adicionales."
                        )
                    elif err_code in {"200001", "220094", "220095"}:
                        cooldown_h = 1.0 if err_code == "220095" else 6.0
                        self.rate_limiter.record_restriction(err_code, cooldown_hours=cooldown_h)
                        logging.warning(
                            "Aviso Binance Square: Código comunitario %s detectado. "
                            "Disyuntor preventivo activado por %.1fh: %s",
                            err_code,
                            cooldown_h,
                            res_data,
                        )
                    elif err_code == "220009":
                        cooldown_h = self._hours_until_utc_midnight()
                        self.rate_limiter.record_restriction("220009", cooldown_hours=cooldown_h)
                        logging.warning(
                            "Límite diario de publicaciones Binance Square alcanzado (código 220009). "
                            "Disyuntor activado por %.2fh hasta reinicio UTC.",
                            cooldown_h,
                        )
                    elif err_code in {"220003", "220004", "10005"}:
                        self.rate_limiter.record_restriction(err_code, cooldown_hours=24.0)
                        logging.critical(
                            "Error crítico de credenciales/KYC Binance Square (código %s). Cuarentena 24h: %s",
                            err_code,
                            res_data,
                        )
                    elif err_code in {"20002", "20022"}:
                        msg_detail = str(res_data.get("messageDetail") or res_data.get("message") or "")
                        logging.error(
                            "Publicación rechazada por filtro de palabras sensibles en Binance Square (código %s): %s | %s",
                            err_code,
                            msg_detail,
                            res_data,
                        )
                        self._record_event(
                            mode="binance_square",
                            symbol=sym,
                            event="binance_square_failed",
                            payload={
                                "status": "business_error",
                                "code": err_code,
                                "message_detail": msg_detail,
                                "api_response": res_data,
                                "metadata": metadata or {},
                            },
                        )
                        return False
                    else:
                        logging.error("Respuesta con código de error de negocio en Binance Square: %s", res_data)

                    self._record_event(
                        mode="binance_square",
                        symbol=sym,
                        event="binance_square_failed",
                        payload={
                            "status": "business_error",
                            "code": err_code,
                            "api_response": res_data,
                            "metadata": metadata or {},
                        },
                    )
                    return False

            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, ConnectionResetError) as net_err:
                last_error_msg = str(net_err)
                wait_seconds = self._backoff_seconds(attempt)
                logging.warning(
                    "Error de conexión con Binance Square (intento %d/%d): %s. Reintentando en %.2fs...",
                    attempt,
                    max_attempts,
                    net_err,
                    wait_seconds,
                )
                if attempt < max_attempts:
                    time.sleep(wait_seconds)
                    continue
            except Exception as e:
                last_error_msg = str(e)
                logging.error("Fallo inesperado al publicar en Binance Square: %s", e)
                break

        # Si agotó todos los intentos sin éxito
        self._record_event(
            mode="binance_square",
            symbol=sym,
            event="binance_square_failed",
            payload={"error": last_error_msg, "metadata": metadata or {}},
        )
        return False
