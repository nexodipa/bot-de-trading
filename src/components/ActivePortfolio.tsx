import React from 'react';
import { Position, Currency, CURRENCY_MAP, ViewMode } from '../types';
import { formatMoney } from '../services/humanFormatters';
import { TrendingUp, ShieldAlert, CheckCircle2, HelpCircle } from 'lucide-react';

interface ActivePortfolioProps {
  positions: Position[];
  currency: Currency;
  viewMode?: ViewMode;
}

export const ActivePortfolio: React.FC<ActivePortfolioProps> = ({ positions, currency, viewMode = 'simple' }) => {
  const curr = CURRENCY_MAP[currency];
  const totalPnlUsdt = positions.reduce((acc, p) => acc + p.pnlUsdt, 0);
  const totalPnlConverted = totalPnlUsdt * curr.rate;

  const getFriendlyStatus = (status: Position['status']) => {
    switch (status) {
      case 'TARGET_1_HIT':
        return { label: 'Meta 1 Cumplida (Ganancia Parcial Asegurada)', color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' };
      case 'TRAILING_STOP':
        return { label: 'Protegiendo Ganancias en Subida', color: 'text-sky-400 bg-sky-500/10 border-sky-500/20' };
      case 'ACTIVE':
      default:
        return { label: 'Operación Abierta Activa', color: 'text-zinc-300 bg-zinc-800/40 border-zinc-700' };
    }
  };

  const getFriendlyAsset = (symbol: string) => {
    switch (symbol) {
      case 'SOL/USDT':
        return { name: 'Solana', type: 'Criptoactivo Líder (Binance)', tag: 'Alta Velocidad' };
      case 'NVDA':
        return { name: 'Nvidia Corp', type: 'Acción de Wall Street (IBKR)', tag: 'Líder en IA' };
      case 'ETH/USDT':
        return { name: 'Ethereum', type: 'Criptoactivo Líder (Binance)', tag: 'Smart Contracts' };
      case 'MSFT':
        return { name: 'Microsoft Corp', type: 'Acción de Wall Street (IBKR)', tag: 'Blue-Chip' };
      default:
        return { name: symbol, type: 'Activo Diversificado', tag: 'Spot' };
    }
  };

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-5 sm:p-6 mb-8 font-mono">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-4 mb-4">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)] flex items-center gap-1.5">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
            Tus Inversiones Actuales en Tiempo Real
          </span>
          <h2 className="text-base sm:text-lg font-extrabold text-[var(--text-main)] flex items-center gap-2">
            CARTERA ACTIVA DIVERSIFICADA (CRIPTO + WALL STREET)
          </h2>
        </div>

        <div className="flex items-center gap-3 bg-[var(--bg-surface)] p-2.5 rounded-lg border border-[var(--border)]">
          <div className="text-right">
            <span className="text-[10px] text-[var(--text-dim)] uppercase block font-semibold">
              Ganancia Flotante de Hoy
            </span>
            <span className="text-sm sm:text-base font-extrabold text-emerald-400">
              +{curr.symbol}{totalPnlConverted.toLocaleString('es-ES', { minimumFractionDigits: curr.decimals, maximumFractionDigits: curr.decimals })} {currency}
            </span>
          </div>
        </div>
      </div>

      {/* Everyday Explanation Card */}
      <div className="p-3.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border)] text-xs text-[var(--text-muted)] font-sans mb-4 flex items-start gap-2.5">
        <HelpCircle className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-[var(--text-main)]">¿Cómo trabaja esta tabla?: </strong>
          Muestra los activos que el algoritmo ha comprado porque detectó buenas probabilidades de subida.
          Todas las compras tienen un límite de pérdida automático (stop loss) y se venden solas en cuanto tocan la meta de beneficio para ingresar dinero a tu cuenta.
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-[var(--border)] text-[var(--text-dim)] uppercase text-[10px]">
              <th className="py-2.5 px-3">Empresa o Moneda</th>
              <th className="py-2.5 px-3">Mercado / Broker</th>
              <th className="py-2.5 px-3 text-right">Precio de Compra</th>
              <th className="py-2.5 px-3 text-right">Precio Actual</th>
              <th className="py-2.5 px-3 text-right">Tu Ganancia</th>
              <th className="py-2.5 px-3 text-right">% de Tu Cartera</th>
              <th className="py-2.5 px-3 text-center">Estado de la Operación</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border)]">
            {positions.map((p) => {
              const isProfit = p.pnlPct >= 0;
              const convertedPnl = p.pnlUsdt * curr.rate;
              const friendly = getFriendlyAsset(p.symbol);
              const statusInfo = getFriendlyStatus(p.status);

              return (
                <tr key={p.id} className="hover:bg-[var(--bg-card-hover)] transition-colors">
                  <td className="py-3 px-3 font-bold text-[var(--text-main)]">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
                      <div>
                        <div className="font-bold text-[var(--text-main)]">{friendly.name}</div>
                        <div className="text-[10px] text-[var(--text-dim)] font-mono">{p.symbol}</div>
                      </div>
                    </div>
                  </td>
                  <td className="py-3 px-3 text-[var(--text-muted)] text-[11px]">
                    <span className="px-1.5 py-0.5 rounded bg-[var(--bg-surface)] border border-[var(--border)] block w-fit">
                      {friendly.type}
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right text-[var(--text-muted)] font-mono">
                    ${p.entryPrice.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="py-3 px-3 text-right font-bold text-[var(--text-main)] font-mono">
                    ${p.currentPrice.toLocaleString('es-ES', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>
                  <td className="py-3 px-3 text-right font-bold font-mono">
                    <span className={isProfit ? 'text-emerald-400' : 'text-rose-400'}>
                      {isProfit ? '+' : ''}{curr.symbol}{convertedPnl.toLocaleString('es-ES', { minimumFractionDigits: curr.decimals, maximumFractionDigits: curr.decimals })}{' '}
                      ({isProfit ? '+' : ''}{p.pnlPct.toFixed(2)}%)
                    </span>
                  </td>
                  <td className="py-3 px-3 text-right text-[var(--text-muted)] font-mono">
                    {p.allocationPct.toFixed(1)}%
                  </td>
                  <td className="py-3 px-3 text-center">
                    <span className={`text-[10px] font-semibold px-2.5 py-1 rounded-full border inline-block ${statusInfo.color}`}>
                      {statusInfo.label}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};
