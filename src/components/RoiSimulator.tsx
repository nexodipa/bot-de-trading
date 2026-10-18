import React, { useState } from 'react';
import { Currency, CURRENCY_MAP, ViewMode } from '../types';
import { calculateRoi } from '../services/quantEngine';
import { formatMoney } from '../services/humanFormatters';
import { Calculator, ArrowRight, DollarSign, Sparkles, CheckCircle2 } from 'lucide-react';

interface RoiSimulatorProps {
  currency: Currency;
  onOpenDeposit: () => void;
  viewMode?: ViewMode;
}

export const RoiSimulator: React.FC<RoiSimulatorProps> = ({ currency, onOpenDeposit, viewMode = 'simple' }) => {
  const [capitalUsd, setCapitalUsd] = useState<number>(10000);
  const [months, setMonths] = useState<number>(12);
  const [isCompound, setIsCompound] = useState<boolean>(true);

  const curr = CURRENCY_MAP[currency];
  const convertedCapital = capitalUsd * curr.rate;
  const result = calculateRoi(convertedCapital, months, isCompound);

  const presets = [1000, 5000, 10000, 25000, 50000];

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-5 sm:p-6 mb-8 font-mono">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-4 mb-6">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)] flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
            Calculadora Práctica para Inversores
          </span>
          <h2 className="text-base sm:text-lg font-extrabold text-[var(--text-main)] flex items-center gap-2">
            SIMULA CUÁNTO PUEDE CRECER TU DINERO
          </h2>
        </div>

        {/* Toggle Mode with Friendly Names */}
        <div className="flex bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-1 text-xs">
          <button
            onClick={() => setIsCompound(true)}
            className={`px-3 py-1.5 rounded font-bold transition-all ${
              isCompound
                ? 'bg-emerald-500 text-black shadow-sm'
                : 'text-[var(--text-muted)] hover:text-[var(--text-main)]'
            }`}
            title="Reinvertir las ganancias automáticamente cada mes para que crezca exponencialmente"
          >
            Reinvertir Ganancias (Compuesto)
          </button>
          <button
            onClick={() => setIsCompound(false)}
            className={`px-3 py-1.5 rounded font-bold transition-all ${
              !isCompound
                ? 'bg-emerald-500 text-black shadow-sm'
                : 'text-[var(--text-muted)] hover:text-[var(--text-main)]'
            }`}
            title="Retirar las ganancias mes a mes a tu cuenta bancaria"
          >
            Retirar Mes a Mes (Distribución)
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
        {/* Sliders Area */}
        <div className="space-y-6">
          {/* Quick Preset Buttons */}
          <div>
            <span className="text-[10px] text-[var(--text-dim)] uppercase block mb-1.5 font-bold">
              Montos Comunes de Ejemplo:
            </span>
            <div className="flex flex-wrap gap-2">
              {presets.map((p) => (
                <button
                  key={p}
                  onClick={() => setCapitalUsd(p)}
                  className={`px-2.5 py-1 rounded text-xs border transition-all ${
                    capitalUsd === p
                      ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400 font-bold'
                      : 'border-[var(--border)] bg-[var(--bg-surface)] text-[var(--text-muted)] hover:text-[var(--text-main)]'
                  }`}
                >
                  ${p.toLocaleString()} USD
                </button>
              ))}
            </div>
          </div>

          {/* Capital Slider */}
          <div>
            <div className="flex justify-between text-xs mb-2">
              <span className="text-[var(--text-muted)] font-semibold uppercase">¿Cuánto dinero quieres poner a trabajar?:</span>
              <span className="text-sm font-extrabold text-emerald-400">
                {curr.symbol}{convertedCapital.toLocaleString('es-ES', { maximumFractionDigits: curr.decimals })} {currency}
              </span>
            </div>
            <input
              type="range"
              min="1000"
              max="150000"
              step="1000"
              value={capitalUsd}
              onChange={(e) => setCapitalUsd(Number(e.target.value))}
              className="w-full h-2.5 bg-[var(--bg-surface)] rounded-lg appearance-none cursor-pointer accent-emerald-500 border border-[var(--border)]"
            />
            <div className="flex justify-between text-[10px] text-[var(--text-dim)] mt-1.5 font-mono">
              <span>{curr.symbol}{(1000 * curr.rate).toLocaleString('es')} Mínimo</span>
              <span>{curr.symbol}{(50000 * curr.rate).toLocaleString('es')}</span>
              <span>{curr.symbol}{(150000 * curr.rate).toLocaleString('es')} Institucional</span>
            </div>
          </div>

          {/* Timeframe Slider */}
          <div>
            <div className="flex justify-between text-xs mb-2">
              <span className="text-[var(--text-muted)] font-semibold uppercase">¿Por cuánto tiempo?:</span>
              <span className="text-sm font-extrabold text-sky-400">{months} Meses ({months >= 12 ? `${(months/12).toFixed(1)} Años` : 'Mediano Plazo'})</span>
            </div>
            <input
              type="range"
              min="3"
              max="36"
              step="1"
              value={months}
              onChange={(e) => setMonths(Number(e.target.value))}
              className="w-full h-2.5 bg-[var(--bg-surface)] rounded-lg appearance-none cursor-pointer accent-sky-500 border border-[var(--border)]"
            />
            <div className="flex justify-between text-[10px] text-[var(--text-dim)] mt-1.5 font-mono">
              <span>3 Meses (Trimestral)</span>
              <span>12 Meses (1 Año)</span>
              <span>36 Meses (3 Años)</span>
            </div>
          </div>

          <div className="p-3.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border)] text-xs text-[var(--text-muted)] leading-relaxed font-sans">
            <span className="font-bold text-[var(--text-main)]">📌 En cristiano: </span>
            Con una asignación de {curr.symbol}{convertedCapital.toLocaleString('es-ES', { maximumFractionDigits: 0 })} {currency} a {months} meses, 
            obtendrías aproximadamente <strong className="text-emerald-400">+{curr.symbol}{result.profit.toLocaleString('es-ES', { maximumFractionDigits: 0 })} de ganancia neta</strong>, equivalente a <strong className="text-[var(--text-main)]">+{curr.symbol}{result.avgMonthlyProfit.toLocaleString('es-ES', { maximumFractionDigits: 0 })} cada mes</strong> para tus gastos o estilo de vida.
          </div>
        </div>

        {/* Results Card */}
        <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-2xl p-6 shadow-md flex flex-col justify-between">
          <div className="border-b border-[var(--border)] pb-4 mb-4">
            <span className="text-[11px] text-[var(--text-dim)] uppercase block mb-1 font-semibold">
              Tu Dinero Final Estimado ({months} meses)
            </span>
            <div className="text-3xl sm:text-4xl font-extrabold text-[var(--text-main)] tracking-tight">
              {curr.symbol}{result.finalCapital.toLocaleString('es-ES', { minimumFractionDigits: curr.decimals, maximumFractionDigits: curr.decimals })}
            </div>
            <div className="text-sm text-emerald-400 font-bold mt-1.5 flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4" />
              +{curr.symbol}{result.profit.toLocaleString('es-ES', { minimumFractionDigits: curr.decimals, maximumFractionDigits: curr.decimals })}{' '}
              (+{result.roiPct.toFixed(1)}% de beneficio neto total)
            </div>
          </div>

          <div className="space-y-3 mb-6 text-xs">
            <div className="flex justify-between py-1.5 border-b border-[var(--border)]">
              <span className="text-[var(--text-dim)]">Ingreso mensual equivalente:</span>
              <span className="font-bold text-sky-400">
                ~ {curr.symbol}{result.avgMonthlyProfit.toLocaleString('es-ES', { minimumFractionDigits: curr.decimals, maximumFractionDigits: curr.decimals })} / mes
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-[var(--border)]">
              <span className="text-[var(--text-dim)]">Comisión que pagas si no ganas:</span>
              <span className="font-bold text-emerald-400">$0 (Cero costo si no hay ganancias)</span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-[var(--border)]">
              <span className="text-[var(--text-dim)]">¿Dónde queda tu dinero?:</span>
              <span className="font-bold text-[var(--text-main)]">En tu cuenta propia de Binance / Broker</span>
            </div>
          </div>

          <button
            onClick={onOpenDeposit}
            className="w-full py-3.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-black font-extrabold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all shadow-lg hover:shadow-emerald-500/20"
          >
            <span>Iniciar con este Monto</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
