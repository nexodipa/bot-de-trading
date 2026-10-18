import React, { useState } from 'react';
import { InvestorProfile, Currency, ViewMode } from '../types';
import { formatMoney, METRIC_EXPLANATIONS } from '../services/humanFormatters';
import { ShieldCheck, TrendingUp, HelpCircle, Lock, Wallet, ArrowUpRight, CheckCircle2, Info } from 'lucide-react';

interface InvestorOverviewHumanCardProps {
  investor: InvestorProfile;
  currency: Currency;
  viewMode: ViewMode;
  onToggleViewMode: () => void;
  onOpenDeposit: () => void;
}

export const InvestorOverviewHumanCard: React.FC<InvestorOverviewHumanCardProps> = ({
  investor,
  currency,
  viewMode,
  onToggleViewMode,
  onOpenDeposit,
}) => {
  const [showHelpModal, setShowHelpModal] = useState(false);

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-5 sm:p-7 mb-8 shadow-sm">
      {/* Top Banner with greeting and Mode Switcher */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-5 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse"></span>
            <span className="text-xs font-bold text-emerald-400 uppercase tracking-wider font-mono">
              Resumen de Cuenta Fiduciaria
            </span>
            <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-semibold">
              Verificado y Protegido
            </span>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-[var(--text-main)] tracking-tight">
            Hola, {investor.name}. Tu patrimonio está rindiendo de forma segura.
          </h2>
          <p className="text-xs sm:text-sm text-[var(--text-muted)] mt-1">
            Cuenta: <span className="font-mono font-bold text-[var(--text-main)]">{investor.accountNumber}</span> · Nivel: <span className="font-semibold">{investor.tier}</span>
          </p>
        </div>

        {/* Mode switcher: Modo Fácil vs Modo Pro */}
        <div className="flex items-center gap-2 bg-[var(--bg-surface)] border border-[var(--border)] p-1.5 rounded-lg">
          <button
            onClick={() => {
              if (viewMode !== 'simple') onToggleViewMode();
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              viewMode === 'simple'
                ? 'bg-emerald-500 text-black font-bold shadow-sm'
                : 'text-[var(--text-muted)] hover:text-[var(--text-main)]'
            }`}
          >
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Formato Fácil (Para Personas)</span>
          </button>

          <button
            onClick={() => {
              if (viewMode !== 'pro') onToggleViewMode();
            }}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold transition-all ${
              viewMode === 'pro'
                ? 'bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] font-bold shadow-sm'
                : 'text-[var(--text-muted)] hover:text-[var(--text-main)]'
            }`}
          >
            <span>Modo Experto (Cuantitativo)</span>
          </button>
        </div>
      </div>

      {/* 4 Friendly Key Indicators for Everyday People */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Card 1: Total Money */}
        <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl p-4 flex flex-col justify-between hover:border-emerald-500/30 transition-all">
          <div>
            <div className="flex items-center justify-between text-[var(--text-muted)] text-xs mb-1">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Tu Dinero Total</span>
              <Wallet className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-[var(--text-main)] font-mono">
              {formatMoney(investor.totalEquity, currency)}
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-[var(--border)] text-xs">
            <span className="text-emerald-400 font-bold">
              +{formatMoney(investor.netProfit, currency)} ({investor.roiPct >= 0 ? '+' : ''}{investor.roiPct}%)
            </span>
            <span className="text-[var(--text-dim)] block text-[11px] mt-0.5">
              Ganancia neta acumulada en tu favor
            </span>
          </div>
        </div>

        {/* Card 2: Protection Shield */}
        <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl p-4 flex flex-col justify-between hover:border-emerald-500/30 transition-all">
          <div>
            <div className="flex items-center justify-between text-[var(--text-muted)] text-xs mb-1">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Blindaje de Seguridad</span>
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-xl sm:text-2xl font-extrabold text-emerald-400 font-mono">
              100% ACTIVO
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-[var(--border)] text-xs">
            <span className="text-[var(--text-main)] font-bold">Máximo riesgo acotado a -6.4%</span>
            <span className="text-[var(--text-dim)] block text-[11px] mt-0.5">
              Si el mercado cae fuerte, el bot frena y protege tu capital
            </span>
          </div>
        </div>

        {/* Card 3: Monthly Income Potential */}
        <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl p-4 flex flex-col justify-between hover:border-sky-500/30 transition-all">
          <div>
            <div className="flex items-center justify-between text-[var(--text-muted)] text-xs mb-1">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Rendimiento Promedio</span>
              <TrendingUp className="w-4 h-4 text-sky-400" />
            </div>
            <div className="text-2xl sm:text-3xl font-extrabold text-sky-400 font-mono">
              +5.20% <span className="text-xs text-[var(--text-muted)] font-normal">/ mes</span>
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-[var(--border)] text-xs">
            <span className="text-[var(--text-main)] font-bold">
              ~ {formatMoney(investor.totalEquity * 0.052, currency)} al mes
            </span>
            <span className="text-[var(--text-dim)] block text-[11px] mt-0.5">
              Disponible para reinvertir o retirar a tu banco
            </span>
          </div>
        </div>

        {/* Card 4: Non-custodial Ownership */}
        <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl p-4 flex flex-col justify-between hover:border-indigo-500/30 transition-all">
          <div>
            <div className="flex items-center justify-between text-[var(--text-muted)] text-xs mb-1">
              <span className="font-semibold uppercase tracking-wider text-[11px]">Custodia & Propiedad</span>
              <Lock className="w-4 h-4 text-indigo-400" />
            </div>
            <div className="text-xl sm:text-2xl font-extrabold text-[var(--text-main)]">
              En Tu Poder
            </div>
          </div>
          <div className="mt-3 pt-3 border-t border-[var(--border)] text-xs">
            <span className="text-emerald-400 font-bold">0% de riesgo de retención</span>
            <span className="text-[var(--text-dim)] block text-[11px] mt-0.5">
              Tus fondos están en tu Binance o broker propio
            </span>
          </div>
        </div>
      </div>

      {/* Everyday Language Explanations Bar */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border)] text-xs">
        <div className="flex items-center gap-2 text-[var(--text-muted)]">
          <Info className="w-4 h-4 text-sky-400 shrink-0" />
          <span>
            <strong>¿Tienes dudas sobre los números?</strong> Hemos preparado un glosario simple para que entiendas exactamente cómo trabaja tu dinero.
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowHelpModal(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text-main)] hover:bg-[var(--bg-card-hover)] font-semibold transition-colors"
          >
            <HelpCircle className="w-3.5 h-3.5 text-sky-400" />
            <span>Ver Glosario en Lenguaje Sencillo</span>
          </button>

          <button
            onClick={onOpenDeposit}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-500 hover:bg-emerald-600 text-black font-bold uppercase transition-all shadow-sm"
          >
            <span>Añadir o Retirar Fondos</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Help Modal in Everyday Language */}
      {showHelpModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl max-w-2xl w-full p-6 sm:p-8 max-h-[85vh] overflow-y-auto shadow-2xl">
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-4 mb-5">
              <div>
                <h3 className="text-lg font-bold text-[var(--text-main)] flex items-center gap-2">
                  <HelpCircle className="w-5 h-5 text-emerald-400" />
                  Glosario Fácil: Tu Dinero Explicado con Palabras Cotidianas
                </h3>
                <p className="text-xs text-[var(--text-muted)] mt-1">
                  Sin tecnicismos aburridos ni fórmulas difíciles. Aquí tienes qué significa cada cosa.
                </p>
              </div>
              <button
                onClick={() => setShowHelpModal(false)}
                className="p-1 rounded text-[var(--text-muted)] hover:text-[var(--text-main)]"
              >
                ✕
              </button>
            </div>

            <div className="space-y-4 text-xs sm:text-sm">
              {Object.entries(METRIC_EXPLANATIONS).map(([key, exp]) => (
                <div key={key} className="p-4 rounded-xl bg-[var(--bg-surface)] border border-[var(--border)]">
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="font-bold text-[var(--text-main)] text-sm">{exp.humanName}</span>
                    <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold">
                      {exp.title}
                    </span>
                  </div>
                  <p className="text-[var(--text-muted)] leading-relaxed mb-2">
                    {exp.humanExplanation}
                  </p>
                  <div className="p-2.5 rounded bg-emerald-500/5 border border-emerald-500/10 text-emerald-300 text-xs flex items-start gap-2">
                    <span className="shrink-0 font-bold">💡 Ejemplo cotidiano:</span>
                    <span>{exp.everydayAnalogy}</span>
                  </div>
                </div>
              ))}
            </div>

            <button
              onClick={() => setShowHelpModal(false)}
              className="w-full mt-6 py-2.5 rounded-lg bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] font-bold text-xs uppercase"
            >
              Entendido, volver al panel
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
