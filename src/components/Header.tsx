import React from 'react';
import { Currency, CURRENCY_MAP, ThemeMode, AppTab, ViewMode } from '../types';
import { Shield, Activity, Layers, FileText, Moon, Sun, ArrowUpRight, HelpCircle } from 'lucide-react';

interface HeaderProps {
  currentTab: AppTab;
  setTab: (tab: AppTab) => void;
  currency: Currency;
  setCurrency: (curr: Currency) => void;
  theme: ThemeMode;
  toggleTheme: () => void;
  viewMode: ViewMode;
  setViewMode: (mode: ViewMode) => void;
  onOpenDeposit: () => void;
  onOpenReport: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  currentTab,
  setTab,
  currency,
  setCurrency,
  theme,
  toggleTheme,
  viewMode,
  setViewMode,
  onOpenDeposit,
  onOpenReport,
}) => {
  return (
    <header className="sticky top-0 z-50 bg-[var(--bg-surface)] border-b border-[var(--border)] px-4 sm:px-8 py-3 flex flex-wrap items-center justify-between gap-3 backdrop-blur-md">
      {/* Brand Crest & Title */}
      <div className="flex items-center gap-3">
        <div className="w-9 h-9 rounded bg-[var(--bg-card)] border border-[var(--border)] flex items-center justify-center font-bold text-base text-[var(--text-main)] shadow-inner">
          <span className="font-mono text-emerald-400 font-extrabold text-lg">ᚠ</span>
        </div>
        <div className="brand-text">
          <h1 className="text-xs sm:text-sm font-extrabold tracking-wider uppercase text-[var(--text-main)] font-mono flex items-center gap-2">
            ARCAFID QUANTITATIVE
            <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
              ALPHA ENGINE
            </span>
          </h1>
          <p className="text-[10px] text-[var(--text-muted)] uppercase tracking-wider font-semibold font-mono">
            Gestión Cuantitativa No-Custodial · Cripto & Wall Street
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <nav className="flex items-center gap-1 sm:gap-2">
        <button
          onClick={() => setTab('portal')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono font-bold uppercase tracking-wider transition-all ${
            currentTab === 'portal'
              ? 'bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] shadow-sm'
              : 'text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-card)]'
          }`}
        >
          <Shield className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Portal</span> Inversor
        </button>

        <button
          onClick={() => setTab('workstation')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono font-bold uppercase tracking-wider transition-all ${
            currentTab === 'workstation'
              ? 'bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] shadow-sm'
              : 'text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-card)]'
          }`}
        >
          <Activity className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Mando &</span> Control
        </button>

        <button
          onClick={() => setTab('unified')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono font-bold uppercase tracking-wider transition-all ${
            currentTab === 'unified'
              ? 'bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] shadow-sm'
              : 'text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-card)]'
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Panel</span> Unificado
        </button>

        <button
          onClick={() => setTab('pitch')}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-mono font-bold uppercase tracking-wider transition-all ${
            currentTab === 'pitch'
              ? 'bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] shadow-sm'
              : 'text-[var(--text-muted)] hover:text-[var(--text-main)] hover:bg-[var(--bg-card)]'
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          Tesis <span className="hidden sm:inline">Fehu</span>
        </button>
      </nav>

      {/* Right Controls: Currency, Mode, Theme, Action Buttons */}
      <div className="flex items-center gap-2">
        {/* Currency Switcher */}
        <div className="flex bg-[var(--bg-card)] border border-[var(--border)] rounded p-0.5 font-mono text-[11px]">
          {(Object.keys(CURRENCY_MAP) as Currency[]).map((curr) => (
            <button
              key={curr}
              onClick={() => setCurrency(curr)}
              className={`px-2 py-1 rounded transition-all font-semibold ${
                currency === curr
                  ? 'bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)]'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-main)]'
              }`}
            >
              {curr}
            </button>
          ))}
        </div>

        {/* View Mode Toggle: Fácil vs Pro */}
        <button
          onClick={() => setViewMode(viewMode === 'simple' ? 'pro' : 'simple')}
          className={`hidden sm:inline-flex items-center gap-1 px-2.5 py-1 rounded text-[11px] font-semibold border transition-all ${
            viewMode === 'simple'
              ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-400'
              : 'border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-muted)] hover:text-[var(--text-main)]'
          }`}
          title="Cambia las etiquetas técnicas a lenguaje comprensible para cualquier persona"
        >
          <span>{viewMode === 'simple' ? 'Modo Fácil' : 'Modo Pro'}</span>
        </button>

        {/* Theme Switcher */}
        <button
          onClick={toggleTheme}
          title="Alternar tema Terminal / Institucional"
          className="p-1.5 rounded bg-[var(--bg-card)] border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--text-main)] transition-colors"
        >
          {theme === 'dark' ? <Sun className="w-4 h-4 text-amber-400" /> : <Moon className="w-4 h-4 text-indigo-500" />}
        </button>

        {/* Report Button */}
        <button
          onClick={onOpenReport}
          className="hidden md:inline-flex items-center gap-1.5 px-3 py-1.5 rounded border border-[var(--border)] bg-[var(--bg-card)] text-[var(--text-main)] hover:bg-[var(--bg-card-hover)] font-mono text-xs font-bold uppercase transition-all"
        >
          Auditoría
        </button>

        {/* Deposit Button */}
        <button
          onClick={onOpenDeposit}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded bg-emerald-500 hover:bg-emerald-600 text-black font-mono text-xs font-bold uppercase tracking-wider transition-all shadow"
        >
          <span>Depositar</span>
          <ArrowUpRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </header>
  );
};
