import React from 'react';
import { Currency, CURRENCY_MAP } from '../types';

interface UnifiedPanelProps {
  currency: Currency;
}

export const UnifiedPanel: React.FC<UnifiedPanelProps> = ({ currency }) => {
  const curr = CURRENCY_MAP[currency];

  const binancePnl = 842.50 * curr.rate;
  const earnTotal = 12500.0 * curr.rate;
  const ibkrNetLiq = 48520.0 * curr.rate;
  const ibkrCash = 14200.0 * curr.rate;

  return (
    <div className="font-mono space-y-6">
      {/* Consolidated Top KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded p-4">
          <div className="text-[10px] text-[var(--text-dim)] uppercase mb-1">PnL Realizado Binance</div>
          <div className="text-xl sm:text-2xl font-extrabold text-emerald-400">
            +{curr.symbol}{binancePnl.toLocaleString('es', { minimumFractionDigits: curr.decimals, maximumFractionDigits: curr.decimals })}
          </div>
          <div className="text-[10px] text-[var(--text-dim)] mt-1">42 trades cerrados · 0 pausas</div>
        </div>

        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded p-4">
          <div className="text-[10px] text-[var(--text-dim)] uppercase mb-1">Saldo en Binance Earn</div>
          <div className="text-xl sm:text-2xl font-extrabold text-[var(--text-main)]">
            {curr.symbol}{earnTotal.toLocaleString('es', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
          </div>
          <div className="text-[10px] text-[var(--text-dim)] mt-1">Flex 8,500 · Locked 4,000 USDT</div>
        </div>

        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded p-4">
          <div className="text-[10px] text-[var(--text-dim)] uppercase mb-1">Patrimonio Neto IBKR</div>
          <div className="text-xl sm:text-2xl font-extrabold text-sky-400">
            {curr.symbol}{ibkrNetLiq.toLocaleString('es', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}
          </div>
          <div className="text-[10px] text-[var(--text-dim)] mt-1">Efectivo {curr.symbol}{ibkrCash.toLocaleString('es', { minimumFractionDigits: 0, maximumFractionDigits: 0 })} · Gateway Conectado</div>
        </div>

        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded p-4">
          <div className="text-[10px] text-[var(--text-dim)] uppercase mb-1">Tasa de Acierto (Win Rate)</div>
          <div className="text-xl sm:text-2xl font-extrabold text-emerald-400">78.5%</div>
          <div className="text-[10px] text-[var(--text-dim)] mt-1">Ratio Beneficio/Riesgo: 2.65 R</div>
        </div>
      </div>

      {/* 3 Unified Cards: Binance, Earn, IBKR */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Card 1: Binance Spot Trading */}
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded p-4 sm:p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-3 mb-3">
              <h3 className="text-xs sm:text-sm font-bold text-[var(--text-main)] flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-sky-400"></span>
                Binance · Trading Spot
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase font-bold">
                EN VIVO
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--text-dim)]">Entradas / Salidas:</span>
                <span className="text-[var(--text-main)] font-bold">54 / 42</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--text-dim)]">PnL Realizado Neto:</span>
                <span className="text-emerald-400 font-bold">+{curr.symbol}{binancePnl.toLocaleString('es', { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--text-dim)]">Win Rate:</span>
                <span className="text-[var(--text-main)] font-bold">78.5%</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--text-dim)]">Pausas por Riesgo:</span>
                <span className="text-emerald-400 font-bold">0 (Safe Init Activo)</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--text-dim)]">Errores de API:</span>
                <span className="text-[var(--text-main)] font-bold">0</span>
              </div>
            </div>

            <div className="mt-4">
              <span className="text-[10px] text-[var(--text-dim)] uppercase block mb-1.5 font-bold">Rendimiento por Par</span>
              <table className="w-full text-[11px] text-left">
                <thead>
                  <tr className="text-[var(--text-dim)] border-b border-[var(--border)]">
                    <th className="py-1">Par</th>
                    <th className="py-1 text-center">C / V</th>
                    <th className="py-1 text-right">PnL</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  <tr>
                    <td className="py-1.5 font-bold">SOL/USDT</td>
                    <td className="py-1.5 text-center text-[var(--text-dim)]">18 / 14</td>
                    <td className="py-1.5 text-right text-emerald-400 font-bold">+$480.20</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 font-bold">BTC/USDT</td>
                    <td className="py-1.5 text-center text-[var(--text-dim)]">22 / 18</td>
                    <td className="py-1.5 text-right text-emerald-400 font-bold">+$242.10</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 font-bold">ETH/USDT</td>
                    <td className="py-1.5 text-center text-[var(--text-dim)]">14 / 10</td>
                    <td className="py-1.5 text-right text-emerald-400 font-bold">+$120.20</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Card 2: Binance Earn */}
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded p-4 sm:p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-3 mb-3">
              <h3 className="text-xs sm:text-sm font-bold text-[var(--text-main)] flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-400"></span>
                Binance · Earn & Staking
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 uppercase font-bold">
                AUTO-SWEEP ON
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--text-dim)]">Saldo Total Generando Yield:</span>
                <span className="text-[var(--text-main)] font-bold">12,500.00 USDT</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--text-dim)]">Flexible / Locked:</span>
                <span className="text-[var(--text-main)] font-bold">8,500 / 4,000 USDT</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--text-dim)]">Barridos Automáticos:</span>
                <span className="text-emerald-400 font-bold">128 ejecutados</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--text-dim)]">Tasa Promedio Ponderada:</span>
                <span className="text-emerald-400 font-bold">8.45% APR</span>
              </div>
            </div>

            <div className="mt-4">
              <span className="text-[10px] text-[var(--text-dim)] uppercase block mb-1.5 font-bold">Posiciones Staking</span>
              <table className="w-full text-[11px] text-left">
                <thead>
                  <tr className="text-[var(--text-dim)] border-b border-[var(--border)]">
                    <th className="py-1">Activo</th>
                    <th className="py-1 text-center">Tipo</th>
                    <th className="py-1 text-right">APR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  <tr>
                    <td className="py-1.5 font-bold">USDT Flexible</td>
                    <td className="py-1.5 text-center text-[var(--text-dim)]">Liquidez</td>
                    <td className="py-1.5 text-right text-emerald-400 font-bold">7.20%</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 font-bold">BNB Vault</td>
                    <td className="py-1.5 text-center text-[var(--text-dim)]">Staking</td>
                    <td className="py-1.5 text-right text-emerald-400 font-bold">11.80%</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 font-bold">SOL Locked 30D</td>
                    <td className="py-1.5 text-center text-[var(--text-dim)]">30 Días</td>
                    <td className="py-1.5 text-right text-emerald-400 font-bold">9.15%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Card 3: Interactive Brokers */}
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded p-4 sm:p-5 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between border-b border-[var(--border)] pb-3 mb-3">
              <h3 className="text-xs sm:text-sm font-bold text-[var(--text-main)] flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-purple-400"></span>
                Interactive Brokers (IBKR)
              </h3>
              <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 uppercase font-bold">
                TWS API SYNC
              </span>
            </div>

            <div className="space-y-2 text-xs">
              <div className="flex justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--text-dim)]">Patrimonio Neto Total:</span>
                <span className="text-sky-400 font-bold">${(48520.0).toLocaleString('es', { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--text-dim)]">Efectivo No Asignado:</span>
                <span className="text-[var(--text-main)] font-bold">${(14200.0).toLocaleString('es', { minimumFractionDigits: 2 })}</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--text-dim)]">Órdenes / Ejecuciones:</span>
                <span className="text-[var(--text-main)] font-bold">18 / 0 Errores</span>
              </div>
              <div className="flex justify-between py-1 border-b border-[var(--border)]">
                <span className="text-[var(--text-dim)]">Sincronización Acciones:</span>
                <span className="text-emerald-400 font-bold">#NVDA, #MSFT, #AAPL</span>
              </div>
            </div>

            <div className="mt-4">
              <span className="text-[10px] text-[var(--text-dim)] uppercase block mb-1.5 font-bold">Posiciones de Wall Street</span>
              <table className="w-full text-[11px] text-left">
                <thead>
                  <tr className="text-[var(--text-dim)] border-b border-[var(--border)]">
                    <th className="py-1">Acción</th>
                    <th className="py-1 text-center">Títulos</th>
                    <th className="py-1 text-right">PnL No Realiz.</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--border)]">
                  <tr>
                    <td className="py-1.5 font-bold">#NVDA</td>
                    <td className="py-1.5 text-center text-[var(--text-dim)]">18 acciones</td>
                    <td className="py-1.5 text-right text-emerald-400 font-bold">+$109.80</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 font-bold">#MSFT</td>
                    <td className="py-1.5 text-center text-[var(--text-dim)]">3 acciones</td>
                    <td className="py-1.5 text-right text-emerald-400 font-bold">+$15.30</td>
                  </tr>
                  <tr>
                    <td className="py-1.5 font-bold">#AAPL</td>
                    <td className="py-1.5 text-center text-[var(--text-dim)]">12 acciones</td>
                    <td className="py-1.5 text-right text-emerald-400 font-bold">+$44.60</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
