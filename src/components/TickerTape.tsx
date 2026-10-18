import React, { useState, useEffect } from 'react';
import { TickerData } from '../types';
import { INITIAL_TICKERS } from '../services/quantEngine';

interface TickerTapeProps {
  tickers?: TickerData[];
}

export const TickerTape: React.FC<TickerTapeProps> = ({ tickers: initial = INITIAL_TICKERS }) => {
  const [tickers, setTickers] = useState<TickerData[]>(initial);

  // Micro-fluctuation simulation
  useEffect(() => {
    const interval = setInterval(() => {
      setTickers((prev) =>
        prev.map((t) => {
          if (!t.isLive) return t;
          const deltaPct = (Math.random() - 0.49) * 0.12;
          const newPrice = Number((t.price * (1 + deltaPct / 100)).toFixed(2));
          const newChange = Number((t.change24h + deltaPct * 0.2).toFixed(2));
          return {
            ...t,
            price: newPrice,
            change24h: newChange,
          };
        })
      );
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-[var(--bg-base)] border-b border-[var(--border)] px-4 sm:px-8 py-2 overflow-x-auto whitespace-nowrap flex items-center gap-6 text-xs font-mono select-none">
      <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase text-[var(--text-dim)] border-r border-[var(--border)] pr-4">
        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping"></span>
        STREAM EN VIVO
      </div>

      {tickers.map((t) => {
        const isUp = t.change24h >= 0;
        return (
          <div key={t.symbol} className="inline-flex items-center gap-2 border-r border-[var(--border)] pr-5">
            <span className="font-bold text-[var(--text-main)]">{t.symbol}</span>
            <span className="text-[var(--text-muted)] font-mono">
              ${t.price.toLocaleString('es', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </span>
            <span
              className={`font-bold flex items-center text-[11px] ${
                isUp ? 'text-emerald-400' : 'text-rose-400'
              }`}
            >
              {isUp ? '▲ +' : '▼ '}
              {t.change24h.toFixed(2)}%
            </span>
            <span className="text-[9px] px-1 py-0.5 rounded bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text-dim)] uppercase">
              {t.assetClass === 'crypto' ? 'BINANCE' : 'IBKR'}
            </span>
          </div>
        );
      })}
    </div>
  );
};
