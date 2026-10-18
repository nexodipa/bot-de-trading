import React, { useState } from 'react';
import { ScannerSignal, SystemLog, Position } from '../types';
import { Play, Pause, RefreshCw, AlertTriangle, ShieldCheck, Activity, Terminal, Radio } from 'lucide-react';

interface AdminWorkstationProps {
  signals: ScannerSignal[];
  logs: SystemLog[];
  onTriggerScan: () => void;
}

export const AdminWorkstation: React.FC<AdminWorkstationProps> = ({
  signals,
  logs,
  onTriggerScan,
}) => {
  const [isLiveActive, setIsLiveActive] = useState<boolean>(true);
  const [strategyMode, setStrategyMode] = useState<string>('hybrid_cascading');
  const [autoTuneImmunity, setAutoTuneImmunity] = useState<boolean>(true);
  const [actionNotice, setActionNotice] = useState<string | null>(null);

  const triggerNotice = (msg: string) => {
    setActionNotice(msg);
    setTimeout(() => setActionNotice(null), 4000);
  };

  return (
    <div className="font-mono space-y-6">
      {/* Top Banner & Control Status */}
      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded p-4 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-4 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className={`w-2.5 h-2.5 rounded-full ${isLiveActive ? 'bg-emerald-400 animate-pulse' : 'bg-rose-400'}`} />
              <h2 className="text-base sm:text-lg font-extrabold text-[var(--text-main)] uppercase tracking-wider">
                Centro de Mando & Control Operativo · Quant Engine
              </h2>
            </div>
            <p className="text-xs text-[var(--text-dim)] mt-1">
              Supervisión en tiempo real de Binance Spot Engine + Interactive Brokers Equities Sync.
            </p>
          </div>

          {/* Quick Actions */}
          <div className="flex items-center gap-2 flex-wrap">
            <button
              onClick={() => {
                setIsLiveActive(!isLiveActive);
                triggerNotice(
                  isLiveActive
                    ? 'Operaciones pausadas voluntariamente por el operador.'
                    : 'Motor reactivado: Evaluación sistemática armada.'
                );
              }}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-bold uppercase transition-all ${
                isLiveActive
                  ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20 hover:bg-rose-500/20'
                  : 'bg-emerald-500 text-black hover:bg-emerald-600'
              }`}
            >
              {isLiveActive ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              {isLiveActive ? 'Pausar Ejecución' : 'Armar Trading en Vivo'}
            </button>

            <button
              onClick={() => {
                onTriggerScan();
                triggerNotice('Escaneo multidimensional ejecutado: 12 pares sincronizados.');
              }}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[var(--bg-surface)] border border-[var(--border)] text-[var(--text-main)] hover:bg-[var(--bg-card-hover)] text-xs font-bold uppercase transition-all"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Escanear Mercados
            </button>
          </div>
        </div>

        {actionNotice && (
          <div className="mb-4 p-2.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
            <Activity className="w-4 h-4 shrink-0" />
            <span>{actionNotice}</span>
          </div>
        )}

        {/* Engine KPI Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <div className="bg-[var(--bg-surface)] p-3 rounded border border-[var(--border)]">
            <span className="text-[10px] text-[var(--text-dim)] uppercase block">Estado Motor</span>
            <span className={`text-sm font-extrabold ${isLiveActive ? 'text-emerald-400' : 'text-rose-400'}`}>
              {isLiveActive ? 'EJECUCIÓN ACTIVA' : 'STANDBY OPERADOR'}
            </span>
          </div>

          <div className="bg-[var(--bg-surface)] p-3 rounded border border-[var(--border)]">
            <span className="text-[10px] text-[var(--text-dim)] uppercase block">Equity Base M1</span>
            <span className="text-sm font-extrabold text-[var(--text-main)]">$10,000.00</span>
          </div>

          <div className="bg-[var(--bg-surface)] p-3 rounded border border-[var(--border)]">
            <span className="text-[10px] text-[var(--text-dim)] uppercase block">Win Rate (Histórico)</span>
            <span className="text-sm font-extrabold text-emerald-400">78.5% (42/54)</span>
          </div>

          <div className="bg-[var(--bg-surface)] p-3 rounded border border-[var(--border)]">
            <span className="text-[10px] text-[var(--text-dim)] uppercase block">Pérdidas Consecutivas</span>
            <span className="text-sm font-extrabold text-emerald-400">0 / 3 Máx</span>
          </div>

          <div className="bg-[var(--bg-surface)] p-3 rounded border border-[var(--border)]">
            <span className="text-[10px] text-[var(--text-dim)] uppercase block">Drawdown Intradiario</span>
            <span className="text-sm font-extrabold text-emerald-400">-0.24% (-6.4% Cap)</span>
          </div>

          <div className="bg-[var(--bg-surface)] p-3 rounded border border-[var(--border)]">
            <span className="text-[10px] text-[var(--text-dim)] uppercase block">Modo de Cascada</span>
            <span className="text-sm font-extrabold text-sky-400">ACTIVE MOMENTUM</span>
          </div>
        </div>
      </div>

      {/* Multi-Strategy Scanner Section */}
      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded p-4 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] pb-3 mb-4">
          <div>
            <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)]">
              Detección Cuantitativa de Alpha & Señales M2
            </span>
            <h3 className="text-sm sm:text-base font-extrabold text-[var(--text-main)] uppercase">
              Escáner de Activos & Diagnóstico de Régimen
            </h3>
          </div>
          <span className="text-xs text-[var(--text-dim)]">
            Filtro de Inactividad en Lenguaje Natural Fiduciario
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs border-collapse">
            <thead>
              <tr className="border-b border-[var(--border)] text-[var(--text-dim)] uppercase text-[10px]">
                <th className="py-2 px-3">Símbolo</th>
                <th className="py-2 px-3">Clase</th>
                <th className="py-2 px-3 text-center">Acción</th>
                <th className="py-2 px-3 text-right">Confianza</th>
                <th className="py-2 px-3 text-right">Calidad Entrada</th>
                <th className="py-2 px-3 text-right">RSI (14)</th>
                <th className="py-2 px-3 text-right">Volumen Z</th>
                <th className="py-2 px-3">Estrategia Desplegada</th>
                <th className="py-2 px-3">Diagnóstico Fiduciario</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {signals.map((s, idx) => (
                <tr key={idx} className="hover:bg-[var(--bg-card-hover)] transition-colors">
                  <td className="py-3 px-3 font-bold text-[var(--text-main)]">{s.symbol}</td>
                  <td className="py-3 px-3 text-[var(--text-dim)] text-[11px]">{s.assetClass}</td>
                  <td className="py-3 px-3 text-center">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                        s.action === 'MOMENTUM_ENTRY'
                          ? 'bg-sky-500/10 text-sky-400 border border-sky-500/30'
                          : s.action === 'BUY'
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                          : 'bg-zinc-800/50 text-zinc-400 border border-zinc-700/50'
                      }`}
                    >
                      {s.action}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right font-bold text-[var(--text-main)]">
                    {(s.confidence * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 px-3 text-right text-[var(--text-muted)]">
                    {(s.entryQuality * 100).toFixed(1)}%
                  </td>
                  <td className="py-3 px-3 text-right text-[var(--text-muted)]">{s.rsi.toFixed(1)}</td>
                  <td className="py-3 px-3 text-right text-[var(--text-muted)]">{s.volumeZ.toFixed(2)}σ</td>
                  <td className="py-3 px-3 text-sky-400 font-semibold text-[11px]">{s.activeStrategy}</td>
                  <td className="py-3 px-3 text-[var(--text-dim)] text-[11px] max-w-xs truncate" title={s.reason}>
                    {s.reason}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Terminal & Telemetry Logs */}
      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded p-4 sm:p-6">
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-3 mb-3">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-emerald-400" />
            <h3 className="text-xs sm:text-sm font-extrabold text-[var(--text-main)] uppercase">
              Registro de Auditoría & Telemetría en Tiempo Real
            </h3>
          </div>
          <span className="text-[10px] text-[var(--text-dim)]">Formato en Lenguaje Natural Sin Jerga Críptica</span>
        </div>

        <div className="bg-[var(--bg-base)] border border-[var(--border)] rounded p-3 h-48 overflow-y-auto space-y-1.5 text-xs font-mono">
          {logs.map((log) => {
            const badgeColor =
              log.level === 'SUCCESS'
                ? 'text-emerald-400'
                : log.level === 'EXEC'
                ? 'text-sky-400'
                : log.level === 'WARN'
                ? 'text-amber-400'
                : 'text-zinc-400';
            return (
              <div key={log.id} className="flex items-start gap-2 py-0.5 leading-relaxed">
                <span className="text-[var(--text-dim)] text-[10px] shrink-0">{log.timestamp}</span>
                <span className={`text-[10px] font-bold shrink-0 ${badgeColor}`}>[{log.source}]</span>
                <span className="text-[var(--text-main)] text-[11px]">{log.message}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
