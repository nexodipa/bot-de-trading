import React, { useState, useEffect } from 'react';
import { MarketSession } from '../types';

export const MarketSessionsBar: React.FC = () => {
  const [sessions, setSessions] = useState<MarketSession[]>([]);

  useEffect(() => {
    const updateSessions = () => {
      const now = new Date();
      const utcHours = now.getUTCHours();
      const utcMins = now.getUTCMinutes();
      const currentUtcDec = utcHours + utcMins / 60;

      // Tokyo: UTC+9 (00:00 - 06:00 UTC)
      // London: UTC+1 (07:00 - 15:30 UTC)
      // New York: UTC-4 (13:30 - 20:00 UTC)
      // Sydney: UTC+10 (22:00 - 06:00 UTC)
      const tokyoOpen = currentUtcDec >= 0 && currentUtcDec < 6;
      const londonOpen = currentUtcDec >= 7 && currentUtcDec < 15.5;
      const nyOpen = currentUtcDec >= 13.5 && currentUtcDec < 20;
      const sydneyOpen = currentUtcDec >= 22 || currentUtcDec < 6;

      const formatTime = (offsetHours: number) => {
        const d = new Date(now.getTime() + offsetHours * 3600000);
        return d.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit', timeZone: 'UTC' });
      };

      setSessions([
        { city: 'TOKIO', name: 'TSE', isOpen: tokyoOpen, timeStr: formatTime(9), utcOffset: 'UTC+9' },
        { city: 'LONDRES', name: 'LSE', isOpen: londonOpen, timeStr: formatTime(1), utcOffset: 'UTC+1' },
        { city: 'NUEVA YORK', name: 'NYSE/NSDQ', isOpen: nyOpen, timeStr: formatTime(-4), utcOffset: 'UTC-4' },
        { city: 'SÍDNEY', name: 'ASX', isOpen: sydneyOpen, timeStr: formatTime(10), utcOffset: 'UTC+10' },
      ]);
    };

    updateSessions();
    const interval = setInterval(updateSessions, 15000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-[var(--bg-surface)] border-b border-[var(--border)] px-4 sm:px-8 py-1.5 flex flex-wrap items-center justify-between text-xs font-mono gap-2">
      {/* Sessions list */}
      <div className="flex items-center gap-4 sm:gap-6 flex-wrap">
        <span className="text-[10px] text-[var(--text-dim)] font-bold uppercase tracking-wider">
          Sesiones Globales:
        </span>
        {sessions.map((s) => (
          <div key={s.city} className="flex items-center gap-1.5 text-[11px]">
            <span
              className={`w-2 h-2 rounded-full inline-block ${
                s.isOpen ? 'bg-emerald-500 shadow-sm shadow-emerald-500/50 animate-pulse' : 'bg-zinc-600'
              }`}
            />
            <span className="text-[var(--text-dim)] font-semibold">{s.city}</span>
            <span className="text-[var(--text-main)] font-bold">{s.timeStr}</span>
            <span
              className={`text-[9px] px-1 py-0.2 rounded font-bold uppercase ${
                s.isOpen ? 'text-emerald-400 bg-emerald-500/10' : 'text-zinc-500 bg-zinc-800/40'
              }`}
            >
              {s.isOpen ? 'ABIERTO' : 'CERRADO'}
            </span>
          </div>
        ))}
      </div>

      {/* Real-time Fiduciary Telemetry */}
      <div className="flex items-center gap-3 text-[11px] text-[var(--text-muted)]">
        <span className="flex items-center gap-1.5">
          <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
          <span>MOTOR: <strong className="text-[var(--text-main)]">HÍBRIDO 24/7</strong></span>
        </span>
        <span className="hidden lg:inline text-[var(--border-light)]">|</span>
        <span className="hidden lg:inline">
          DRAWDOWN CAP: <strong className="text-rose-400">-6.40%</strong>
        </span>
        <span className="hidden lg:inline text-[var(--border-light)]">|</span>
        <span className="hidden lg:inline">
          FALLBACK: <strong className="text-emerald-400">ACTIVE MOMENTUM</strong>
        </span>
      </div>
    </div>
  );
};
