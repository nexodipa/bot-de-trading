from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class GridPlan:
    symbol: str
    lower_bound: float
    upper_bound: float
    stop_loss_bound: float
    buy_levels: list[float]
    sell_levels: list[float]
    quote_per_order: float
    step_pct: float


def build_range_grid(
    symbol: str,
    current_price: float,
    atr_value: float,
    levels: int = 5,
    atr_mult: float = 2.0,
    total_quote_budget: float = 25.0,
    min_notional: float = 5.0,
) -> GridPlan | None:
    """Construye una malla cuantitativa acotada por ATR para mercados en régimen lateral (range).

    Garantiza:
    - Espaciado mínimo neto >= 0.45% por escalón (cubre comisiones maker/taker y spread).
    - Ajuste automático del número de niveles si el presupuesto es reducido para cumplir `min_notional`.
    - Banda de invalidación estructural (`stop_loss_bound`) debajo del rango para evitar atrapamiento en ruptura bajista.
    """
    if current_price <= 0 or atr_value <= 0 or total_quote_budget < min_notional:
        return None

    half_band = max(atr_value * max(atr_mult, 1.0), current_price * 0.015)
    lower = max(current_price - half_band, current_price * 0.50)
    upper = current_price + half_band
    stop_loss_bound = max(lower - atr_value, lower * 0.95)

    max_affordable_buys = max(1, int(total_quote_budget // max(min_notional, 1.0)))
    effective_levels = min(max(2, int(levels)), max_affordable_buys * 2)

    step = (upper - lower) / effective_levels
    step_pct = step / current_price
    if step_pct < 0.0045:
        # Ensanchar rango mínimo para asegurar margen neto positivo tras comisiones
        half_band = current_price * 0.0045 * (effective_levels / 2.0)
        lower = max(current_price - half_band, current_price * 0.50)
        upper = current_price + half_band
        step = (upper - lower) / effective_levels
        step_pct = step / current_price

    all_rungs = [round(lower + i * step, 8) for i in range(effective_levels + 1)]
    buy_levels = [p for p in all_rungs if p < current_price * 0.998][:max_affordable_buys]
    sell_levels = [p for p in all_rungs if p > current_price * 1.002]

    if not buy_levels:
        buy_levels = [round(lower, 8)]
    if not sell_levels:
        sell_levels = [round(upper, 8)]

    quote_per_order = round(total_quote_budget / len(buy_levels), 4)
    if quote_per_order < min_notional:
        return None

    return GridPlan(
        symbol=symbol.upper(),
        lower_bound=round(lower, 8),
        upper_bound=round(upper, 8),
        stop_loss_bound=round(stop_loss_bound, 8),
        buy_levels=buy_levels,
        sell_levels=sell_levels,
        quote_per_order=quote_per_order,
        step_pct=round(step_pct, 6),
    )


class QuantitativeRangeGrid:
    """Ejecutor y supervisor de Grid Trading Cuantitativo para activos en consolidación lateral."""

    def __init__(
        self,
        levels: int = 5,
        atr_mult: float = 2.0,
        max_quote_usdt: float = 25.0,
    ) -> None:
        self.levels = levels
        self.atr_mult = atr_mult
        self.max_quote_usdt = max_quote_usdt
        self.active_plans: dict[str, GridPlan] = {}

    def evaluate_step(
        self,
        symbol: str,
        df: pd.DataFrame,
        regime_label: str,
        atr_value: float,
        quote_free: float,
        exec_client: Any = None,
        filters: Any = None,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        sym = symbol.upper()
        if df is None or df.empty:
            return {"event": "grid_skip", "reason": "no_data"}

        current_price = float(df["close"].iloc[-1])

        # Protección ante ruptura estructural si ya existía una malla activa
        if sym in self.active_plans:
            plan = self.active_plans[sym]
            if current_price <= plan.stop_loss_bound or regime_label != "range":
                self._cancel_open_grid(sym, exec_client=exec_client, dry_run=dry_run)
                del self.active_plans[sym]
                return {
                    "event": "grid_breakout_stop",
                    "symbol": sym,
                    "price": current_price,
                    "regime": regime_label,
                    "stop_loss_bound": plan.stop_loss_bound,
                }

        if regime_label != "range":
            return {"event": "grid_idle", "symbol": sym, "reason": f"regime_{regime_label}"}

        min_notional = float(getattr(filters, "min_notional", 5.0) or 5.0)
        budget = min(float(quote_free), float(self.max_quote_usdt))
        if budget < min_notional:
            return {
                "event": "grid_skip",
                "symbol": sym,
                "reason": "insufficient_quote_for_min_notional",
                "quote_free": quote_free,
                "min_notional": min_notional,
            }

        plan = self.active_plans.get(sym)
        if plan is None:
            plan = build_range_grid(
                symbol=sym,
                current_price=current_price,
                atr_value=atr_value,
                levels=self.levels,
                atr_mult=self.atr_mult,
                total_quote_budget=budget,
                min_notional=min_notional,
            )
            if plan is None:
                return {"event": "grid_skip", "symbol": sym, "reason": "grid_parameters_not_viable"}
            self.active_plans[sym] = plan

        placed_orders: list[dict[str, Any]] = []
        if not dry_run and exec_client is not None and filters is not None:
            for idx, buy_px in enumerate(plan.buy_levels):
                raw_qty = plan.quote_per_order / buy_px
                qty = exec_client.normalize_quantity(raw_qty, filters)
                if not exec_client.quantity_is_valid(qty, filters) or not exec_client.notional_is_valid(qty, buy_px, filters):
                    continue
                price_str = exec_client.format_price(buy_px, filters)
                try:
                    res = exec_client.create_limit_maker_buy(sym, qty, price_str)
                    placed_orders.append({"side": "BUY", "price": price_str, "qty": qty, "orderId": res.get("orderId")})
                except Exception as exc:
                    logging.debug("[%s] Grid LIMIT_MAKER nivel %d omitido: %s", sym, idx, exc)

        return {
            "event": "grid_active",
            "symbol": sym,
            "dry_run": dry_run,
            "lower_bound": plan.lower_bound,
            "upper_bound": plan.upper_bound,
            "step_pct": plan.step_pct,
            "buy_levels": plan.buy_levels,
            "sell_levels": plan.sell_levels,
            "quote_per_order": plan.quote_per_order,
            "placed_orders": placed_orders,
        }

    @staticmethod
    def _cancel_open_grid(symbol: str, exec_client: Any = None, dry_run: bool = True) -> None:
        if dry_run or exec_client is None:
            return
        try:
            open_orders = exec_client.get_open_orders(symbol)
            for ord_obj in open_orders:
                oid = ord_obj.get("orderId")
                if oid is not None:
                    exec_client.cancel_order(symbol, int(oid))
        except Exception as exc:
            logging.warning("[%s] Error cancelando órdenes de Grid: %s", symbol, exc)
