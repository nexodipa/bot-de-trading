import React from 'react';
import { ShieldCheck, Lock, Cpu, TrendingUp } from 'lucide-react';
import { ViewMode } from '../types';

interface CircuitBreakersBannerProps {
  viewMode?: ViewMode;
}

export const CircuitBreakersBanner: React.FC<CircuitBreakersBannerProps> = ({ viewMode = 'simple' }) => {
  const isSimple = viewMode === 'simple';

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-4 sm:p-5 mb-8 text-xs font-mono">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--border)] pb-3 mb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400" />
          <span className="font-extrabold uppercase tracking-wider text-[var(--text-main)]">
            {isSimple ? 'ESCUDOS Y CERROJOS DE SEGURIDAD (CÓMO PROTEGEMOS TU DINERO)' : 'CERROJOS FIDUCIARIOS INSTITUCIONALES (PROTOCOLOS DE CAPITAL SEGURO)'}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 text-[10px] font-bold">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            {isSimple ? 'PROTECCIÓN 24 HORAS ACTIVA' : 'AUDITORÍA MATEMÁTICA ACTIVA'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Guard 1 */}
        <div className="bg-[var(--bg-surface)] p-3.5 rounded-lg border border-[var(--border)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-[var(--text-muted)] uppercase font-semibold">
                {isSimple ? 'Freno de Emergencia Máximo' : 'Límite Drawdown Diario'}
              </span>
              <Lock className="w-3.5 h-3.5 text-rose-400" />
            </div>
            <div className="text-base font-bold text-rose-400">
              {isSimple ? 'LÍMITE -6.4% MÁXIMO' : '-6.40% MAX'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-dim)] mt-2 font-sans leading-relaxed">
            {isSimple
              ? 'Si el mercado mundial cae repentinamente, el bot detiene las compras de inmediato. Tu capital principal queda a salvo.'
              : 'Freno de parada fiduciario inviolable con corte automático de operaciones ante caídas abruptas.'}
          </div>
        </div>

        {/* Guard 2 */}
        <div className="bg-[var(--bg-surface)] p-3.5 rounded-lg border border-[var(--border)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-[var(--text-muted)] uppercase font-semibold">
                {isSimple ? 'Colchón de Seguridad Garantizado' : 'Equity Auto-Init M1'}
              </span>
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            </div>
            <div className="text-base font-bold text-emerald-400">
              {isSimple ? '$10.000 USD PISO' : '$10,000 BASE'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-dim)] mt-2 font-sans leading-relaxed">
            {isSimple
              ? 'Si hay micro-cortes de internet en los servidores del broker, la cuenta no se traba ni entra en error; mantiene su base segura.'
              : 'Protección ante caídas de API: resuelve piso positivo seguro sin congelar el bot ni generar alarmas espurias.'}
          </div>
        </div>

        {/* Guard 3 */}
        <div className="bg-[var(--bg-surface)] p-3.5 rounded-lg border border-[var(--border)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-[var(--text-muted)] uppercase font-semibold">
                {isSimple ? 'Aprovechamiento de Oportunidades' : 'Cascada Multi-Estrategia'}
              </span>
              <TrendingUp className="w-3.5 h-3.5 text-sky-400" />
            </div>
            <div className="text-base font-bold text-sky-400">
              {isSimple ? 'IMPULSO DE TENDENCIA' : 'MOMENTUM CONTINUATION'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-dim)] mt-2 font-sans leading-relaxed">
            {isSimple
              ? 'El sistema no se queda inactivo sin hacer nada: si ve una subida clara con compras de inversores fuertes, entra para ganar.'
              : 'Evita bloqueo pasivo en \'hold\' evaluando flujo de volumen y continuación de tendencia positiva.'}
          </div>
        </div>

        {/* Guard 4 */}
        <div className="bg-[var(--bg-surface)] p-3.5 rounded-lg border border-[var(--border)] flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-1">
              <span className="text-[10px] text-[var(--text-muted)] uppercase font-semibold">
                {isSimple ? 'Filtro Anti-Falsas Alarmas' : 'Inmunidad de Auto-Tuning'}
              </span>
              <Cpu className="w-3.5 h-3.5 text-amber-400" />
            </div>
            <div className="text-base font-bold text-amber-400">
              {isSimple ? 'CRITERIO EQUILIBRADO' : 'CLAMPED ≤0.55'}
            </div>
          </div>
          <div className="text-[11px] text-[var(--text-dim)] mt-2 font-sans leading-relaxed">
            {isSimple
              ? 'Evita que el algoritmo se vuelva demasiado temeroso o imprudente; exige pruebas reales antes de hacer cada operación.'
              : 'Protege contra sobre-optimización y umbrales inalcanzables en baja volatilidad.'}
          </div>
        </div>
      </div>
    </div>
  );
};
