import { StrategyWeights, EvolutionState, OrderBook, TickerData, Position, ScannerSignal, SystemLog, CircuitBreakerStatus } from '../types';

export const CHART_DATASETS: Record<string, { labels: string[]; values: number[]; spy: number[]; dd: number[] }> = {
  '1M': {
    labels: ['Día 1', 'Día 5', 'Día 10', 'Día 15', 'Día 20', 'Día 25', 'Día 30'],
    values: [1750, 1762, 1780, 1795, 1810, 1828, 1842.50],
    spy:    [1750, 1753, 1758, 1760, 1768, 1772, 1775.20],
    dd:     [-0.2, -0.8, -0.4, -0.6, -0.3, -0.5, -0.2],
  },
  '3M': {
    labels: ['Jul 01', 'Jul 15', 'Ago 01', 'Ago 15', 'Sep 01', 'Sep 15'],
    values: [1620, 1660, 1710, 1750, 1790, 1842.50],
    spy:    [1620, 1635, 1650, 1670, 1690, 1710.00],
    dd:     [-1.2, -2.4, -1.8, -3.1, -1.5, -0.4],
  },
  '6M': {
    labels: ['Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep'],
    values: [1420, 1490, 1560, 1650, 1740, 1842.50],
    spy:    [1420, 1450, 1480, 1520, 1560, 1600.00],
    dd:     [-2.5, -4.1, -2.8, -3.4, -1.9, -0.5],
  },
  '1Y': {
    labels: ['Oct', 'Nov', 'Dic', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep'],
    values: [1000, 1060, 1140, 1220, 1310, 1390, 1480, 1570, 1660, 1740, 1810, 1842.50],
    spy:    [1000, 1020, 1045, 1070, 1085, 1105, 1120, 1135, 1145, 1160, 1175, 1190.00],
    dd:     [-1.5, -3.2, -2.1, -5.4, -3.8, -6.4, -4.2, -2.8, -3.5, -1.8, -2.1, -0.4],
  },
  'YTD': {
    labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep'],
    values: [1220, 1310, 1390, 1480, 1570, 1660, 1740, 1810, 1842.50],
    spy:    [1070, 1085, 1105, 1120, 1135, 1145, 1160, 1175, 1190.00],
    dd:     [-2.1, -5.4, -3.8, -6.4, -4.2, -2.8, -3.5, -1.8, -0.4],
  },
  'ALL': {
    labels: ['2025 Q1', '2025 Q2', '2025 Q3', '2025 Q4', '2026 Q1', '2026 Q2', '2026 Q3'],
    values: [1000, 1240, 1480, 1720, 1980, 2240, 2520.00],
    spy:    [1000, 1050, 1100, 1140, 1180, 1220, 1260.00],
    dd:     [-2.1, -4.5, -3.2, -5.8, -6.4, -3.9, -0.5],
  },
};

export const INITIAL_TICKERS: TickerData[] = [
  { symbol: 'BTC/USDT', name: 'Bitcoin Spot', price: 60520.10, change24h: 3.42, high24h: 61200, low24h: 58900, volume24h: '1.42B', assetClass: 'crypto', isLive: true },
  { symbol: 'ETH/USDT', name: 'Ethereum Spot', price: 2640.50, change24h: 2.15, high24h: 2680, low24h: 2570, volume24h: '840M', assetClass: 'crypto', isLive: true },
  { symbol: 'SOL/USDT', name: 'Solana Spot', price: 148.80, change24h: 6.02, high24h: 152.40, low24h: 139.10, volume24h: '410M', assetClass: 'crypto', isLive: true },
  { symbol: 'NVDA', name: 'Nvidia Corp (IBKR)', price: 128.50, change24h: 4.41, high24h: 130.10, low24h: 123.00, volume24h: '2.8B', assetClass: 'equity', isLive: true },
  { symbol: 'AAPL', name: 'Apple Inc (IBKR)', price: 228.40, change24h: 0.85, high24h: 230.10, low24h: 226.50, volume24h: '1.2B', assetClass: 'equity', isLive: true },
  { symbol: 'MSFT', name: 'Microsoft (IBKR)', price: 442.20, change24h: 1.12, high24h: 445.00, low24h: 438.90, volume24h: '980M', assetClass: 'equity', isLive: true },
  { symbol: 'TSLA', name: 'Tesla Inc (IBKR)', price: 245.80, change24h: -1.24, high24h: 251.00, low24h: 242.10, volume24h: '1.9B', assetClass: 'equity', isLive: true },
  { symbol: 'SPY', name: 'S&P 500 ETF (Ref)', price: 582.40, change24h: 0.62, high24h: 584.10, low24h: 580.20, volume24h: '5.2B', assetClass: 'index', isLive: true },
];

export const INITIAL_POSITIONS: Position[] = [
  {
    id: 'pos-1',
    symbol: 'SOL/USDT',
    assetClass: 'Crypto Spot',
    type: 'Spot Momentum',
    side: 'LONG',
    entryPrice: 144.50,
    currentPrice: 148.80,
    qty: 12.5,
    pnlUsdt: 53.75,
    pnlPct: 6.02,
    allocationPct: 22.4,
    status: 'ACTIVE',
    openedAt: '2026-10-18 04:12 UTC',
  },
  {
    id: 'pos-2',
    symbol: 'NVDA',
    assetClass: 'NASDAQ Equity',
    type: 'Volume Flow Breakout',
    side: 'LONG',
    entryPrice: 122.40,
    currentPrice: 128.50,
    qty: 18.0,
    pnlUsdt: 109.80,
    pnlPct: 4.41,
    allocationPct: 28.6,
    status: 'TARGET_1_HIT',
    openedAt: '2026-10-17 14:30 UTC',
  },
  {
    id: 'pos-3',
    symbol: 'ETH/USDT',
    assetClass: 'Spot Trend',
    type: 'Hawkes Trend Following',
    side: 'LONG',
    entryPrice: 2580.00,
    currentPrice: 2640.50,
    qty: 0.65,
    pnlUsdt: 39.32,
    pnlPct: 3.48,
    allocationPct: 20.8,
    status: 'TRAILING_STOP',
    openedAt: '2026-10-18 06:45 UTC',
  },
  {
    id: 'pos-4',
    symbol: 'MSFT',
    assetClass: 'NASDAQ Equity',
    type: 'Mean Reversion EMA20',
    side: 'LONG',
    entryPrice: 437.10,
    currentPrice: 442.20,
    qty: 3.0,
    pnlUsdt: 15.30,
    pnlPct: 1.17,
    allocationPct: 16.5,
    status: 'ACTIVE',
    openedAt: '2026-10-18 08:15 UTC',
  },
];

export const INITIAL_EVOLUTION: EvolutionState = {
  generation: 48,
  loss: 0.0382,
  reward: 1.84,
  huggingfaceNlp: {
    label: 'ALCISTA INSTITUCIONAL',
    sentimentScore: 0.78,
    rawHeadlinesAnalyzed: 284,
  },
  weights: {
    alphaHawkes: 0.35,
    momentumTrend: 0.35,
    huggingfaceSentiment: 0.20,
    meanReversion: 0.10,
    atrStopMultiplier: 1.85,
    confidenceThreshold: 0.72,
  },
  lastTrainedAt: '2026-10-18 09:20:14',
  trainingLogs: [
    { generation: 45, reward: 1.62, loss: 0.0441, timestamp: '10:45' },
    { generation: 46, reward: 1.70, loss: 0.0412, timestamp: '11:15' },
    { generation: 47, reward: 1.76, loss: 0.0398, timestamp: '11:45' },
    { generation: 48, reward: 1.84, loss: 0.0382, timestamp: '12:15' },
  ],
};

export const INITIAL_SIGNALS: ScannerSignal[] = [
  {
    symbol: 'SOL/USDT',
    assetClass: 'Crypto',
    action: 'MOMENTUM_ENTRY',
    confidence: 0.84,
    entryQuality: 0.79,
    rsi: 58.4,
    atr: 2.14,
    volumeZ: 2.85,
    activeStrategy: 'Active Momentum Continuation',
    reason: 'Ruptura alcista con volumen Z-score superior a 2.5σ y confirmación de flujo institucional.',
    timestamp: 'Hace 4 min',
  },
  {
    symbol: 'NVDA',
    assetClass: 'Equity',
    action: 'BUY',
    confidence: 0.78,
    entryQuality: 0.74,
    rsi: 52.1,
    atr: 1.65,
    volumeZ: 1.94,
    activeStrategy: 'Cascading Hawkes Process',
    reason: 'Cluster de órdenes institucionales en libro IBKR, superación de EMA20.',
    timestamp: 'Hace 11 min',
  },
  {
    symbol: 'ETH/USDT',
    assetClass: 'Crypto',
    action: 'BUY',
    confidence: 0.76,
    entryQuality: 0.71,
    rsi: 55.6,
    atr: 24.5,
    volumeZ: 1.62,
    activeStrategy: 'Trend Following Multi-TF',
    reason: 'Filtro macro BTC en régimen alcista (+3.42%), rechazo de soporte dinámico.',
    timestamp: 'Hace 19 min',
  },
  {
    symbol: 'MSFT',
    assetClass: 'Equity',
    action: 'WAIT',
    confidence: 0.52,
    entryQuality: 0.48,
    rsi: 48.2,
    atr: 3.80,
    volumeZ: 0.88,
    activeStrategy: 'Mean Reversion Safeguard',
    reason: 'Consolidación lateral; se mantiene sin operar debido a compresión de volatilidad.',
    timestamp: 'Hace 26 min',
  },
  {
    symbol: 'TSLA',
    assetClass: 'Equity',
    action: 'WAIT',
    confidence: 0.44,
    entryQuality: 0.41,
    rsi: 43.1,
    atr: 4.95,
    volumeZ: -0.45,
    activeStrategy: 'Risk Guard Isolation',
    reason: 'Retracción intradiaria; se mantiene sin operar debido a divergencia en flujo de volumen.',
    timestamp: 'Hace 38 min',
  },
];

export const INITIAL_LOGS: SystemLog[] = [
  { id: '1', timestamp: '09:32:15', level: 'SUCCESS', source: 'STRATEGY', message: 'Cascading Multi-Strategy Fallback: SOL/USDT activado vía Active Momentum (Confianza 84%).' },
  { id: '2', timestamp: '09:30:00', level: 'INFO', source: 'RISK', message: 'RiskManager.can_trade(): Equity auto-init asegurado ($10,000.00 base). Límite de Drawdown seguro a -6.40%.' },
  { id: '3', timestamp: '09:28:44', level: 'EXEC', source: 'BINANCE', message: 'Orden spot ejecutada: BUY 12.5 SOL @ 144.50 USDT (Slippage: 0.012%).' },
  { id: '4', timestamp: '09:25:10', level: 'INFO', source: 'IBKR', message: 'IBKR Gateway conectado: Sesión Wall Street activa (#NVDA, #AAPL, #MSFT monitoreados).' },
  { id: '5', timestamp: '09:20:14', level: 'SUCCESS', source: 'TELEMETRY', message: 'Auto-Evolution RL: Pesos recalculados Gen #48. Pérdida reducida a 0.0382.' },
  { id: '6', timestamp: '09:15:30', level: 'INFO', source: 'STRATEGY', message: 'MSFT se mantiene sin operar debido a baja fuerza de tendencia en marco intradiario.' },
];

export function generateOrderBook(baseMid: number = 60520.10): OrderBook {
  const variation = (Math.random() - 0.5) * 6;
  const mid = baseMid + variation;
  const spreadBps = Number((0.15 + Math.random() * 0.06).toFixed(2));
  const spreadUsd = Number((mid * (spreadBps / 10000)).toFixed(2));

  const bids = [];
  const asks = [];

  let cumBid = 0;
  for (let i = 1; i <= 6; i++) {
    const price = Number((mid - (i * spreadUsd * 0.9)).toFixed(2));
    const size = Number((0.45 + Math.random() * 1.8).toFixed(3));
    cumBid += size;
    bids.push({ price, size, total: Number(cumBid.toFixed(3)) });
  }

  let cumAsk = 0;
  for (let i = 1; i <= 6; i++) {
    const price = Number((mid + (i * spreadUsd * 0.9)).toFixed(2));
    const size = Number((0.40 + Math.random() * 1.7).toFixed(3));
    cumAsk += size;
    asks.push({ price, size, total: Number(cumAsk.toFixed(3)) });
  }

  return {
    bids,
    asks,
    midPrice: Number(mid.toFixed(2)),
    spreadBps,
    spreadUsd,
    lastUpdated: new Date().toLocaleTimeString('es'),
  };
}

export function calculateRoi(capital: number, months: number, isCompound: boolean) {
  const monthlyRate = 0.052; // 5.2% average net monthly alpha
  let finalCapital = capital;

  if (isCompound) {
    finalCapital = capital * Math.pow(1 + monthlyRate, months);
  } else {
    finalCapital = capital * (1 + monthlyRate * months);
  }

  const profit = finalCapital - capital;
  const roiPct = (profit / capital) * 100;
  const avgMonthlyProfit = profit / months;

  return {
    finalCapital,
    profit,
    roiPct,
    avgMonthlyProfit,
  };
}
