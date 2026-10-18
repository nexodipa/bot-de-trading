import React, { useState, useEffect } from 'react';
import { OrderBook } from '../types';
import { generateOrderBook } from '../services/quantEngine';

export const OrderBookSimulator: React.FC = () => {
  const [orderBook, setOrderBook] = useState<OrderBook>(generateOrderBook());

  useEffect(() => {
    const interval = setInterval(() => {
      setOrderBook((prev) => generateOrderBook(prev.midPrice));
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  const maxTotal = Math.max(
    ...orderBook.bids.map((b) => b.total),
    ...orderBook.asks.map((a) => a.total),
    5.0
  );

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded p-4 sm:p-6 mb-8 font-mono">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-3 mb-4">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)]">
            Microestructura de Mercado L2 (Binance Liquidity Gateway)
          </span>
          <h2 className="text-base font-extrabold text-[var(--text-main)] flex items-center gap-2">
            LIBRO DE ÓRDENES & PROFUNDIDAD INSTITUCIONAL
          </h2>
        </div>

        <div className="flex items-center gap-4 text-xs">
          <div>
            <span className="text-[10px] text-[var(--text-dim)] uppercase block">Spread Activo</span>
            <span className="text-emerald-400 font-bold">
              {orderBook.spreadBps} BPS (${orderBook.spreadUsd})
            </span>
          </div>
          <div>
            <span className="text-[10px] text-[var(--text-dim)] uppercase block">Mid Price</span>
            <span className="text-base font-extrabold text-[var(--text-main)]">
              ${orderBook.midPrice.toLocaleString('es', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        {/* Bids (Buys) */}
        <div className="bg-[var(--bg-surface)] p-3 rounded border border-[var(--border)]">
          <div className="flex justify-between text-[10px] text-[var(--text-dim)] uppercase border-b border-[var(--border)] pb-1.5 mb-2 font-bold">
            <span>Volumen Btc</span>
            <span>Total Acum</span>
            <span className="text-right text-emerald-400">Precio Bid (Compra)</span>
          </div>
          <div className="space-y-1.5">
            {orderBook.bids.map((b, idx) => {
              const widthPct = Math.min(100, (b.total / maxTotal) * 100);
              return (
                <div key={idx} className="relative flex justify-between py-1 px-1.5 rounded overflow-hidden">
                  <div
                    className="absolute inset-y-0 right-0 bg-emerald-500/10 pointer-events-none transition-all duration-300"
                    style={{ width: `${widthPct}%` }}
                  />
                  <span className="relative z-10 text-[var(--text-muted)]">{b.size.toFixed(3)}</span>
                  <span className="relative z-10 text-[var(--text-dim)]">{b.total.toFixed(3)}</span>
                  <span className="relative z-10 text-emerald-400 font-bold text-right">
                    ${b.price.toFixed(2)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Asks (Sells) */}
        <div className="bg-[var(--bg-surface)] p-3 rounded border border-[var(--border)]">
          <div className="flex justify-between text-[10px] text-[var(--text-dim)] uppercase border-b border-[var(--border)] pb-1.5 mb-2 font-bold">
            <span className="text-rose-400">Precio Ask (Venta)</span>
            <span>Volumen Btc</span>
            <span className="text-right">Total Acum</span>
          </div>
          <div className="space-y-1.5">
            {orderBook.asks.map((a, idx) => {
              const widthPct = Math.min(100, (a.total / maxTotal) * 100);
              return (
                <div key={idx} className="relative flex justify-between py-1 px-1.5 rounded overflow-hidden">
                  <div
                    className="absolute inset-y-0 left-0 bg-rose-500/10 pointer-events-none transition-all duration-300"
                    style={{ width: `${widthPct}%` }}
                  />
                  <span className="relative z-10 text-rose-400 font-bold">${a.price.toFixed(2)}</span>
                  <span className="relative z-10 text-[var(--text-muted)]">{a.size.toFixed(3)}</span>
                  <span className="relative z-10 text-[var(--text-dim)] text-right">{a.total.toFixed(3)}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
