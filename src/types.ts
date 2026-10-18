export type Currency = 'USD' | 'EUR' | 'GBP' | 'BTC';

export interface CurrencyConfig {
  symbol: string;
  rate: number;
  decimals: number;
}

export const CURRENCY_MAP: Record<Currency, CurrencyConfig> = {
  USD: { symbol: '$', rate: 1.0, decimals: 2 },
  EUR: { symbol: '€', rate: 0.92, decimals: 2 },
  GBP: { symbol: '£', rate: 0.79, decimals: 2 },
  BTC: { symbol: '₿', rate: 0.0000154, decimals: 4 },
};

export type ThemeMode = 'dark' | 'light';

export type ViewMode = 'simple' | 'pro';

export type AppTab = 'portal' | 'workstation' | 'unified' | 'pitch';

export interface MarketSession {
  city: string;
  name: string;
  isOpen: boolean;
  timeStr: string;
  utcOffset: string;
}

export interface TickerData {
  symbol: string;
  name: string;
  price: number;
  change24h: number;
  high24h: number;
  low24h: number;
  volume24h: string;
  assetClass: 'crypto' | 'equity' | 'index';
  isLive: boolean;
}

export interface Position {
  id: string;
  symbol: string;
  assetClass: 'Crypto Spot' | 'NASDAQ Equity' | 'NYSE Equity' | 'Spot Trend';
  type: string;
  side: 'LONG' | 'SHORT';
  entryPrice: number;
  currentPrice: number;
  qty: number;
  pnlUsdt: number;
  pnlPct: number;
  allocationPct: number;
  status: 'ACTIVE' | 'TARGET_1_HIT' | 'TRAILING_STOP';
  openedAt: string;
}

export interface StrategyWeights {
  alphaHawkes: number;
  momentumTrend: number;
  huggingfaceSentiment: number;
  meanReversion: number;
  atrStopMultiplier: number;
  confidenceThreshold: number;
}

export interface EvolutionState {
  generation: number;
  loss: number;
  reward: number;
  huggingfaceNlp: {
    label: string;
    sentimentScore: number;
    rawHeadlinesAnalyzed: number;
  };
  weights: StrategyWeights;
  lastTrainedAt: string;
  trainingLogs: Array<{
    generation: number;
    reward: number;
    loss: number;
    timestamp: string;
  }>;
}

export interface OrderBookLevel {
  price: number;
  size: number;
  total: number;
}

export interface OrderBook {
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  midPrice: number;
  spreadBps: number;
  spreadUsd: number;
  lastUpdated: string;
}

export interface InvestorProfile {
  name: string;
  email: string;
  tier: string;
  status: string;
  initialDeposit: number;
  totalEquity: number;
  netProfit: number;
  roiPct: number;
  availableCash: number;
  walletUsdt: string;
  kycLevel: string;
  accountNumber: string;
}

export interface ScannerSignal {
  symbol: string;
  assetClass: 'Crypto' | 'Equity';
  action: 'BUY' | 'WAIT' | 'MOMENTUM_ENTRY';
  confidence: number;
  entryQuality: number;
  rsi: number;
  atr: number;
  volumeZ: number;
  activeStrategy: string;
  reason: string;
  timestamp: string;
}

export interface EarnPosition {
  asset: string;
  amount: number;
  aprPct: number;
  type: 'FLEXIBLE' | 'LOCKED';
  durationDays?: number;
}

export interface EarnMovement {
  id: string;
  action: 'SWEEP_AUTO' | 'SUBSCRIBE' | 'INTEREST_PAYOUT';
  asset: string;
  amount: number;
  timestamp: string;
}

export interface IbkrPosition {
  symbol: string;
  qty: number;
  avgCost: number;
  marketPrice: number;
  unrealizedPnl: number;
}

export interface SystemLog {
  id: string;
  timestamp: string;
  level: 'INFO' | 'SUCCESS' | 'WARN' | 'EXEC';
  source: 'RISK' | 'STRATEGY' | 'BINANCE' | 'IBKR' | 'TELEMETRY';
  message: string;
}

export interface CircuitBreakerStatus {
  maxDailyDrawdown: number; // e.g. -6.4%
  currentDailyDrawdown: number;
  dayStartEquity: number;
  currentEquity: number;
  isBreached: boolean;
  consecutiveLosses: number;
  maxConsecutiveLosses: number;
  safeFloorApplied: boolean;
  cascadingActive: boolean;
}
