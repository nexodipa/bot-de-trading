from __future__ import annotations

import logging
import time
from typing import Any

import pandas as pd

from bot.indicators import ema, rsi


class QuantitativeDCAAccumulator:
    """Acumulador DCA cuantitativo condicionado a sobreventa extrema.

    No compra a ciegas por calendario; solo ejecuta micro-compras cuando:
    - RSI(14) <= `rsi_threshold` (por defecto 28.0) en velas cerradas.
    - Precio actual está por debajo de EMA(200) * 0.92 (descuento frente a tendencia larga).
    - Se cumplió el cooldown persistido en SQLite (`cooldown_hours`, por defecto 72h).
    """

    def __init__(
        self,
        rsi_threshold: float = 28.0,
        cooldown_hours: int = 72,
        quote_usdt: float = 6.0,
        ema_discount_ratio: float = 0.92,
    ) -> None:
        self.rsi_threshold = float(rsi_threshold)
        self.cooldown_seconds = max(3600, int(cooldown_hours) * 3600)
        self.quote_usdt = float(quote_usdt)
        self.ema_discount_ratio = float(ema_discount_ratio)

    def should_accumulate(
        self,
        symbol: str,
        df: pd.DataFrame,
        last_buy_ts: float = 0.0,
        now_ts: float | None = None,
    ) -> tuple[bool, dict[str, Any]]:
        now = time.time() if now_ts is None else float(now_ts)
        if last_buy_ts > 0 and (now - last_buy_ts) < self.cooldown_seconds:
            rem_h = round((self.cooldown_seconds - (now - last_buy_ts)) / 3600.0, 1)
            return False, {"reason": "dca_cooldown_active", "remaining_hours": rem_h}

        if df is None or len(df) < 205:
            return False, {"reason": "insufficient_history"}

        close_s = df["close"].astype(float)
        current_price = float(close_s.iloc[-1])
        rsi_val = float(rsi(close_s, 14).iloc[-1])
        ema200_val = float(ema(close_s, 200).iloc[-1])

        if pd.isna(rsi_val) or pd.isna(ema200_val) or ema200_val <= 0:
            return False, {"reason": "invalid_indicators"}

        if rsi_val > self.rsi_threshold:
            return False, {"reason": "rsi_above_threshold", "rsi": round(rsi_val, 2)}

        if current_price > ema200_val * self.ema_discount_ratio:
            return False, {
                "reason": "no_deep_ema_discount",
                "price": current_price,
                "ema200_target": round(ema200_val * self.ema_discount_ratio, 2),
            }

        return True, {
            "reason": "extreme_oversold_dca_authorized",
            "symbol": symbol.upper(),
            "price": current_price,
            "rsi": round(rsi_val, 2),
            "ema200": round(ema200_val, 2),
        }

    def execute_if_eligible(
        self,
        symbol: str,
        data_client: Any,
        exec_client: Any,
        state_store: Any = None,
        earn_manager: Any = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        sym = symbol.upper()
        state_key = f"dca:last_buy:{sym}"
        last_ts = 0.0
        if state_store is not None:
            try:
                saved = state_store.load_state(state_key)
                if isinstance(saved, dict):
                    last_ts = float(saved.get("ts", 0.0))
            except Exception:
                last_ts = 0.0

        df = data_client.get_klines(sym, "4h", 250)
        closed_df = df.iloc[:-1].copy() if df is not None and len(df) > 1 else df
        ok, meta = self.should_accumulate(sym, closed_df, last_buy_ts=last_ts)
        if not ok:
            return {"event": "dca_skip", "symbol": sym, **meta}

        price = float(meta["price"])
        if earn_manager is not None:
            try:
                earn_manager.ensure_quote_available("USDT", self.quote_usdt)
            except Exception:
                pass

        quote_free, _ = exec_client.get_asset_balance_values("USDT")
        if quote_free < self.quote_usdt:
            return {
                "event": "dca_skip",
                "symbol": sym,
                "reason": "insufficient_usdt",
                "quote_free": quote_free,
            }

        filters = exec_client.get_symbol_filters(sym)
        raw_qty = self.quote_usdt / price
        qty = exec_client.normalize_quantity(raw_qty, filters)
        if not exec_client.quantity_is_valid(qty, filters) or not exec_client.notional_is_valid(qty, price, filters):
            return {"event": "dca_skip", "symbol": sym, "reason": "filters_rejected"}

        if dry_run:
            return {"event": "dca_buy_simulation", "symbol": sym, "qty": qty, "price": price, **meta}

        order = exec_client.create_market_buy(sym, qty)
        if state_store is not None:
            try:
                state_store.save_state(state_key, {"ts": time.time(), "price": price, "qty": qty})
            except Exception:
                pass
        logging.info("[%s] DCA Cuantitativo ejecutado: %.6f a ~$%.2f (RSI=%.2f)", sym, qty, price, meta["rsi"])
        return {"event": "dca_buy", "symbol": sym, "qty": qty, "price": price, "order": order, **meta}
