from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import requests


@dataclass(frozen=True)
class FundingOpportunity:
    symbol: str
    mark_price: float
    funding_rate_8h: float
    annualized_apr_pct: float
    next_funding_time_ms: int


class FundingRateArbitrageMonitor:
    """Monitor y planificador Delta-Neutral (Spot Long + Perp Short 1x) para arbitraje de Funding Rate.

    Diseñado bajo disciplina fiduciaria:
    - Exige capital mínimo (`min_capital_usdt`, por defecto $200 USDT) para evitar riesgo de liquidación en Futures.
    - Apalancamiento efectivo 1x (50% Spot + 50% Margen Perpetuo) sin exposición direccional neta.
    """

    FAPI_PREMIUM_INDEX_URL = "https://fapi.binance.com/fapi/v1/premiumIndex"

    def __init__(
        self,
        min_apr_pct: float = 12.0,
        min_capital_usdt: float = 200.0,
        max_allocation_pct: float = 0.25,
    ) -> None:
        self.min_apr_pct = float(min_apr_pct)
        self.min_capital_usdt = float(min_capital_usdt)
        self.max_allocation_pct = float(max_allocation_pct)

    @staticmethod
    def compute_annualized_apr(funding_rate_8h: float) -> float:
        """Convierte tasa de financiación de 8h (3 liquidaciones/día) a APR anualizado en %."""
        return float(funding_rate_8h) * 3.0 * 365.0 * 100.0

    def fetch_funding_opportunities(
        self,
        symbols: list[str] | None = None,
        min_apr_pct: float | None = None,
        timeout: float = 8.0,
    ) -> list[FundingOpportunity]:
        threshold = self.min_apr_pct if min_apr_pct is None else float(min_apr_pct)
        target_set = {s.upper() for s in symbols} if symbols else None

        resp = requests.get(self.FAPI_PREMIUM_INDEX_URL, timeout=timeout)
        resp.raise_for_status()
        raw_items = resp.json()
        if not isinstance(raw_items, list):
            return []

        opportunities: list[FundingOpportunity] = []
        for item in raw_items:
            sym = str(item.get("symbol", "")).upper()
            if not sym.endswith("USDT"):
                continue
            if target_set is not None and sym not in target_set:
                continue
            try:
                rate = float(item.get("lastFundingRate", 0.0))
                mark = float(item.get("markPrice", 0.0))
                next_ts = int(item.get("nextFundingTime", 0))
            except (ValueError, TypeError):
                continue

            if mark <= 0 or rate <= 0:
                continue

            apr = self.compute_annualized_apr(rate)
            if apr >= threshold:
                opportunities.append(
                    FundingOpportunity(
                        symbol=sym,
                        mark_price=mark,
                        funding_rate_8h=rate,
                        annualized_apr_pct=round(apr, 2),
                        next_funding_time_ms=next_ts,
                    )
                )

        opportunities.sort(key=lambda o: o.annualized_apr_pct, reverse=True)
        return opportunities

    def evaluate_allocation(
        self,
        capital_usdt: float,
        opportunity: FundingOpportunity,
        maker_fee_rate: float = 0.00075,
    ) -> dict[str, Any]:
        """Evalúa viabilidad fiduciaria y calcula la cobertura exacta 1:1 Spot/Perp."""
        cap = float(capital_usdt)
        if cap < self.min_capital_usdt:
            return {
                "eligible": False,
                "reason": "below_min_fiduciary_capital",
                "capital_usdt": cap,
                "min_required_usdt": self.min_capital_usdt,
                "symbol": opportunity.symbol,
                "apr_pct": opportunity.annualized_apr_pct,
            }

        alloc_usdt = cap * min(max(self.max_allocation_pct, 0.05), 0.50)
        leg_usdt = alloc_usdt / 2.0
        hedge_qty = leg_usdt / opportunity.mark_price

        # Costo de entrada/salida (4 patas: spot buy/sell + perp short/cover)
        roundtrip_fee_usdt = leg_usdt * maker_fee_rate * 4.0
        expected_daily_yield_usdt = leg_usdt * opportunity.funding_rate_8h * 3.0
        break_even_days = (
            round(roundtrip_fee_usdt / expected_daily_yield_usdt, 2)
            if expected_daily_yield_usdt > 0
            else 999.0
        )

        return {
            "eligible": True,
            "symbol": opportunity.symbol,
            "apr_pct": opportunity.annualized_apr_pct,
            "allocated_usdt": round(alloc_usdt, 2),
            "spot_leg_usdt": round(leg_usdt, 2),
            "perp_margin_usdt": round(leg_usdt, 2),
            "hedge_qty": round(hedge_qty, 6),
            "expected_daily_yield_usdt": round(expected_daily_yield_usdt, 4),
            "roundtrip_fee_usdt": round(roundtrip_fee_usdt, 4),
            "break_even_days": break_even_days,
        }
