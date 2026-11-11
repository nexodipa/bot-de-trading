"""Métricas de rendimiento calculadas únicamente a partir de operaciones reales.

Ninguna cifra se inventa ni se rellena con valores por defecto: si no hay datos
suficientes, las métricas estadísticas se devuelven como ``None`` y el
consumidor debe mostrar "sin datos suficientes" en lugar de un número.
"""
from __future__ import annotations

import json
import math
import sqlite3
from datetime import datetime
from typing import Any, Iterable

# Mínimo de operaciones cerradas para publicar ratios estadísticos. Con menos,
# Sharpe / win rate no tienen significado estadístico.
MIN_TRADES_FOR_STATS = 30


def _num(value: Any) -> float | None:
    try:
        v = float(value)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def compute_performance(
    trades: Iterable[dict[str, Any]],
    initial_equity: float = 0.0,
    min_trades: int = MIN_TRADES_FOR_STATS,
) -> dict[str, Any]:
    """Calcula métricas desde una lista de trades cerrados.

    Cada trade necesita al menos ``pnl`` (moneda de cuenta); ``pnl_pct`` y
    ``exit_time`` son opcionales. Los trades se ordenan por ``exit_time`` si existe.
    """
    rows = [t for t in trades if _num(t.get("pnl")) is not None]
    rows.sort(key=lambda t: str(t.get("exit_time") or ""))
    n = len(rows)
    pnls = [float(t["pnl"]) for t in rows]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    gross_win = sum(wins)
    gross_loss = -sum(losses)

    # Curva de equity por trade -> máximo drawdown
    max_dd_pct: float | None = None
    if n and initial_equity > 0:
        equity = initial_equity
        peak = equity
        worst = 0.0
        for p in pnls:
            equity += p
            peak = max(peak, equity)
            if peak > 0:
                worst = min(worst, (equity - peak) / peak)
        max_dd_pct = round(worst * 100.0, 2)

    sufficient = n >= min_trades
    sharpe = sortino = None
    returns: list[float] = []
    for t, p in zip(rows, pnls):
        pct = _num(t.get("pnl_pct"))
        if pct is not None:
            returns.append(pct / 100.0)
        elif initial_equity > 0:
            returns.append(p / initial_equity)
    if sufficient and len(returns) >= 2:
        mean = sum(returns) / len(returns)
        var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        std = math.sqrt(var)
        # Sharpe por operación (no anualizado): honesto y comparable entre muestras.
        sharpe = round(mean / std, 3) if std > 0 else None
        downside = [min(r, 0.0) for r in returns]
        dstd = math.sqrt(sum(d * d for d in downside) / len(downside))
        sortino = round(mean / dstd, 3) if dstd > 0 else None

    return {
        "total_trades": n,
        "sufficient_data": sufficient,
        "min_trades_required": min_trades,
        "net_pnl": round(sum(pnls), 2),
        "win_rate_pct": round(len(wins) / n * 100.0, 1) if sufficient else None,
        "profit_factor": (round(gross_win / gross_loss, 2) if sufficient and gross_loss > 0 else None),
        "sharpe_per_trade": sharpe,
        "sortino_per_trade": sortino,
        "max_drawdown_pct": max_dd_pct if sufficient else None,
        "source": "closed_trades",
    }


def load_closed_trades(db_path: str) -> list[dict[str, Any]]:
    """Lee trades cerrados reales de la tabla ``trades`` (vacía si no existe)."""
    try:
        con = sqlite3.connect(db_path)
        try:
            cur = con.execute(
                "SELECT symbol, entry_time, exit_time, entry_price, exit_price, "
                "quantity, pnl, pnl_pct, reason FROM trades ORDER BY exit_time"
            )
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
        finally:
            con.close()
    except sqlite3.Error:
        return []


def load_paper_trades(db_path: str) -> list[dict[str, Any]]:
    """Trades del último estado de paper trading guardado (si existe)."""
    try:
        con = sqlite3.connect(db_path)
        try:
            # 1. Priorizar lectura directa desde bot_state ('paper:%'), donde se persiste la lista completa de trades
            cur = con.cursor()
            cur.execute(
                "SELECT value_json FROM bot_state WHERE key LIKE 'paper:%' ORDER BY updated_ts DESC LIMIT 1"
            )
            row = cur.fetchone()
            if row and row[0]:
                payload = json.loads(row[0])
                trades = payload.get("trades") or (
                    payload.get("value", {}).get("trades")
                    if isinstance(payload.get("value"), dict)
                    else None
                )
                if isinstance(trades, list):
                    clean = [t for t in trades if isinstance(t, dict)]
                    if clean:
                        return clean

            # 2. Fallback a eventos de telemetría asegurando que 'trades' sea una lista y no un entero (conteo)
            cur.execute(
                "SELECT payload_json FROM events WHERE mode='paper' "
                "AND payload_json LIKE '%\"trades\"%' ORDER BY id DESC LIMIT 10"
            )
            rows = cur.fetchall()
            for r in rows:
                payload = json.loads(r[0])
                trades = payload.get("trades")
                if trades is None and isinstance(payload.get("value"), dict):
                    trades = payload["value"].get("trades")
                if isinstance(trades, list):
                    clean = [t for t in trades if isinstance(t, dict)]
                    if clean:
                        return clean
            return []
        finally:
            con.close()
    except (sqlite3.Error, ValueError):
        return []


def get_real_performance(db_path: str, initial_equity: float = 0.0) -> dict[str, Any]:
    """Métricas reales: trades live si los hay; si no, paper (etiquetado como tal)."""
    live = load_closed_trades(db_path)
    if live:
        perf = compute_performance(live, initial_equity)
        perf["source"] = "live_closed_trades"
        return perf
    paper = load_paper_trades(db_path)
    perf = compute_performance(paper, initial_equity)
    perf["source"] = "paper_trading" if paper else "no_trades"
    return perf


def format_metric(value: float | None, suffix: str = "", digits: int = 1) -> str:
    return "n/d" if value is None else f"{value:.{digits}f}{suffix}"


def generated_at() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"
