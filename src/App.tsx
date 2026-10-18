import React, { useState, useEffect } from 'react';
import { Currency, ThemeMode, AppTab, ViewMode, Position, EvolutionState, ScannerSignal, SystemLog, InvestorProfile } from './types';
import { Header } from './components/Header';
import { MarketSessionsBar } from './components/MarketSessionsBar';
import { TickerTape } from './components/TickerTape';
import { InvestorOverviewHumanCard } from './components/InvestorOverviewHumanCard';
import { CircuitBreakersBanner } from './components/CircuitBreakersBanner';
import { EquityChart } from './components/EquityChart';
import { ActivePortfolio } from './components/ActivePortfolio';
import { AutoEvolutionPanel } from './components/AutoEvolutionPanel';
import { RoiSimulator } from './components/RoiSimulator';
import { OrderBookSimulator } from './components/OrderBookSimulator';
import { AdminWorkstation } from './components/AdminWorkstation';
import { UnifiedPanel } from './components/UnifiedPanel';
import { PitchDeck } from './components/PitchDeck';
import { DepositModal } from './components/DepositModal';
import { ReportExportModal } from './components/ReportExportModal';
import { INITIAL_POSITIONS, INITIAL_EVOLUTION, INITIAL_SIGNALS, INITIAL_LOGS } from './services/quantEngine';

export const App: React.FC = () => {
  const [currentTab, setTab] = useState<AppTab>('portal');
  const [currency, setCurrency] = useState<Currency>('USD');
  const [theme, setTheme] = useState<ThemeMode>('dark');
  const [viewMode, setViewMode] = useState<ViewMode>('simple');

  const [positions, setPositions] = useState<Position[]>(INITIAL_POSITIONS);
  const [evolution, setEvolution] = useState<EvolutionState>(INITIAL_EVOLUTION);
  const [signals, setSignals] = useState<ScannerSignal[]>(INITIAL_SIGNALS);
  const [logs, setLogs] = useState<SystemLog[]>(INITIAL_LOGS);
  const [isTraining, setIsTraining] = useState<boolean>(false);

  const [isDepositOpen, setIsDepositOpen] = useState<boolean>(false);
  const [isReportOpen, setIsReportOpen] = useState<boolean>(false);

  const [investor, setInvestor] = useState<InvestorProfile>({
    name: 'Alejandro Dupont',
    email: 'dupont.investor@arcafid.com',
    tier: 'Syndicate Multi-Asset',
    status: 'VERIFICADO / ACTIVO',
    initialDeposit: 5000.0,
    totalEquity: 5782.50,
    netProfit: 782.50,
    roiPct: 15.65,
    availableCash: 2140.0,
    walletUsdt: 'TLZ8vG3QJ5YF9r7wA1xN2kM4p6Bc7De9Fg',
    kycLevel: 'TIER-3 INSTITUTIONAL',
    accountNumber: 'ARC-FID-88914',
  });

  // Apply theme to document
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  // Step Auto-Evolution RL
  const handleStepEvolution = () => {
    setIsTraining(true);
    setTimeout(() => {
      setEvolution((prev) => {
        const nextGen = prev.generation + 1;
        const newLoss = Math.max(0.015, prev.loss - 0.0017 + (Math.random() - 0.5) * 0.0005);
        const newReward = Number((prev.reward + 0.08 + Math.random() * 0.04).toFixed(2));

        // Adjust weights slightly via simulated Thompson Sampling
        const hw = Math.min(0.42, Math.max(0.28, prev.weights.alphaHawkes + (Math.random() - 0.48) * 0.02));
        const mo = Math.min(0.42, Math.max(0.28, prev.weights.momentumTrend + (Math.random() - 0.48) * 0.02));
        const se = Math.min(0.25, Math.max(0.15, prev.weights.huggingfaceSentiment + (Math.random() - 0.5) * 0.01));
        const mr = Number(Math.max(0.05, 1 - (hw + mo + se)).toFixed(2));

        return {
          ...prev,
          generation: nextGen,
          loss: Number(newLoss.toFixed(4)),
          reward: newReward,
          weights: {
            ...prev.weights,
            alphaHawkes: Number(hw.toFixed(2)),
            momentumTrend: Number(mo.toFixed(2)),
            huggingfaceSentiment: Number(se.toFixed(2)),
            meanReversion: mr,
            atrStopMultiplier: Number((1.80 + Math.random() * 0.1).toFixed(2)),
          },
          lastTrainedAt: new Date().toLocaleTimeString('es'),
          trainingLogs: [
            ...prev.trainingLogs,
            {
              generation: nextGen,
              reward: newReward,
              loss: Number(newLoss.toFixed(4)),
              timestamp: new Date().toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' }),
            },
          ],
        };
      });

      // Add audit log
      setLogs((prev) => [
        {
          id: Date.now().toString(),
          timestamp: new Date().toLocaleTimeString('es'),
          level: 'SUCCESS',
          source: 'STRATEGY',
          message: `IA adaptativa: Ciclo de aprendizaje Gen #${evolution.generation + 1} completado. Parámetros recalibrados.`,
        },
        ...prev.slice(0, 40),
      ]);

      setIsTraining(false);
    }, 1200);
  };

  // Handle deposit submission
  const handleSuccessDeposit = (amount: number, tier: string, txid: string) => {
    setInvestor((prev) => ({
      ...prev,
      initialDeposit: prev.initialDeposit + amount,
      totalEquity: prev.totalEquity + amount,
      tier,
    }));

    setLogs((prev) => [
      {
        id: Date.now().toString(),
        timestamp: new Date().toLocaleTimeString('es'),
        level: 'EXEC',
        source: 'BINANCE',
        message: `Depósito conciliado on-chain: +$${amount.toLocaleString()} USDT asignados a tu cuenta (TXID: ${txid.substring(0, 10)}...).`,
      },
      ...prev.slice(0, 40),
    ]);
  };

  // Trigger manual market scan
  const handleTriggerScan = () => {
    setSignals((prev) =>
      prev.map((s) => ({
        ...s,
        rsi: Number((45 + Math.random() * 25).toFixed(1)),
        volumeZ: Number((0.8 + Math.random() * 2.2).toFixed(2)),
        timestamp: 'Hace segundos',
      }))
    );
    setLogs((prev) => [
      {
        id: Date.now().toString(),
        timestamp: new Date().toLocaleTimeString('es'),
        level: 'INFO',
        source: 'STRATEGY',
        message: 'Escaneo de mercado ejecutado: Filtros de volumen y régimen de volatilidad actualizados.',
      },
      ...prev.slice(0, 40),
    ]);
  };

  return (
    <div className="min-h-screen bg-[var(--bg-base)] text-[var(--text-main)] flex flex-col transition-colors duration-200">
      {/* Institutional Top Header */}
      <Header
        currentTab={currentTab}
        setTab={setTab}
        currency={currency}
        setCurrency={setCurrency}
        theme={theme}
        toggleTheme={toggleTheme}
        viewMode={viewMode}
        setViewMode={setViewMode}
        onOpenDeposit={() => setIsDepositOpen(true)}
        onOpenReport={() => setIsReportOpen(true)}
      />

      {/* Global Market Clocks & Live Ticker */}
      <MarketSessionsBar />
      <TickerTape />

      {/* Main Content Area */}
      <main className="flex-1 max-w-[1400px] w-full mx-auto px-4 sm:px-8 py-6">
        {currentTab === 'portal' && (
          <div className="animate-fadeIn">
            {/* Friendly Human Overview Card */}
            <InvestorOverviewHumanCard
              investor={investor}
              currency={currency}
              viewMode={viewMode}
              onToggleViewMode={() => setViewMode(viewMode === 'simple' ? 'pro' : 'simple')}
              onOpenDeposit={() => setIsDepositOpen(true)}
            />

            {/* Fiduciary Circuit Breakers in Plain Words */}
            <CircuitBreakersBanner viewMode={viewMode} />

            {/* Live Interactive Equity & Drawdown Chart */}
            <EquityChart currency={currency} theme={theme} viewMode={viewMode} />

            {/* Active Multi-Broker Portfolio */}
            <ActivePortfolio positions={positions} currency={currency} viewMode={viewMode} />

            {/* Quantitative Simulator & Order Book Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <RoiSimulator currency={currency} onOpenDeposit={() => setIsDepositOpen(true)} viewMode={viewMode} />
              <OrderBookSimulator />
            </div>

            {/* Reinforcement Learning & NLP Engine */}
            <AutoEvolutionPanel
              evolution={evolution}
              onStepEvolution={handleStepEvolution}
              isTraining={isTraining}
              viewMode={viewMode}
            />
          </div>
        )}

        {currentTab === 'workstation' && (
          <div className="animate-fadeIn">
            <AdminWorkstation
              signals={signals}
              logs={logs}
              onTriggerScan={handleTriggerScan}
            />
          </div>
        )}

        {currentTab === 'unified' && (
          <div className="animate-fadeIn">
            <UnifiedPanel currency={currency} />
          </div>
        )}

        {currentTab === 'pitch' && (
          <div className="animate-fadeIn">
            <PitchDeck />
          </div>
        )}
      </main>

      {/* Institutional Footer */}
      <footer className="border-t border-[var(--border)] bg-[var(--bg-surface)] py-6 px-4 sm:px-8 text-xs font-mono text-[var(--text-dim)]">
        <div className="max-w-[1400px] mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-[var(--text-main)]">ARCAFID QUANTITATIVE ASSET MANAGEMENT</span>
            <span>·</span>
            <span>Licencia Algorítmica Syndicate No-Custodial</span>
          </div>

          <div className="flex items-center gap-4 text-[11px]">
            <span>Binance Gateway v2.4</span>
            <span>·</span>
            <span>Interactive Brokers TWS API v10.19</span>
            <span>·</span>
            <span>Telegram Bot Telemetry Armed</span>
          </div>
        </div>
      </footer>

      {/* Modals */}
      <DepositModal
        isOpen={isDepositOpen}
        onClose={() => setIsDepositOpen(false)}
        onSuccessDeposit={handleSuccessDeposit}
      />

      <ReportExportModal
        isOpen={isReportOpen}
        onClose={() => setIsReportOpen(false)}
        investor={investor}
        positions={positions}
        currency={currency}
      />
    </div>
  );
};

export default App;
