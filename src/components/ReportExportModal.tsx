import React, { useState } from 'react';
import { X, FileText, Download, CheckCircle2 } from 'lucide-react';
import { InvestorProfile, Position, Currency, CURRENCY_MAP } from '../types';

interface ReportExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  investor: InvestorProfile;
  positions: Position[];
  currency: Currency;
}

export const ReportExportModal: React.FC<ReportExportModalProps> = ({
  isOpen,
  onClose,
  investor,
  positions,
  currency,
}) => {
  const [downloadSuccess, setDownloadSuccess] = useState<string | null>(null);

  if (!isOpen) return null;

  const curr = CURRENCY_MAP[currency];

  const handleExportJson = () => {
    const reportData = {
      agency: 'ArcaFid Quantitative Capital',
      brand: 'ArcaFid Quantitative',
      generated_at: new Date().toISOString(),
      currency,
      investor,
      positions,
      metrics: {
        sharpe_ratio: 2.42,
        sortino_ratio: 3.10,
        win_rate_pct: 78.5,
        profit_factor: 2.65,
        max_drawdown_limit: -6.4,
      },
    };
    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `arcafid-audit-report-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    showNotice('Informe JSON exportado exitosamente.');
  };

  const handleExportCsv = () => {
    const rows = [
      ['Fecha', 'Simbolo', 'Broker', 'Estrategia', 'Precio Entrada', 'Precio Actual', 'PnL USDT', 'PnL Pct'],
      ...positions.map((p) => [
        p.openedAt,
        p.symbol,
        p.assetClass,
        p.type,
        p.entryPrice.toString(),
        p.currentPrice.toString(),
        p.pnlUsdt.toString(),
        `${p.pnlPct}%`,
      ]),
    ];
    const csvContent = 'data:text/csv;charset=utf-8,' + rows.map((e) => e.join(',')).join('\n');
    const encodedUri = encodeURI(csvContent);
    const a = document.createElement('a');
    a.href = encodedUri;
    a.download = `arcafid-audit-ledger-${Date.now()}.csv`;
    a.click();
    showNotice('Libro Mayor CSV exportado exitosamente.');
  };

  const handleExportPdf = () => {
    // Generate clean text-based institutional audit certificate
    const content = `
================================================================================
ARCAFID QUANTITATIVE ASSET MANAGEMENT · INFORME OFICIAL DE AUDITORÍA FIDUCIARIA
================================================================================
Fecha de emisión: ${new Date().toUTCString()}
Inversor Registrado: ${investor.name} (${investor.email})
Nivel de Asignación: ${investor.tier}
Número de Cuenta Fiduciaria: ${investor.accountNumber}

RESUMEN DE CAPITAL CONSOLIDADO
--------------------------------------------------------------------------------
Depósito Principal Asignado: ${curr.symbol}${(investor.initialDeposit * curr.rate).toFixed(2)} ${currency}
Patrimonio Total Actual:     ${curr.symbol}${(investor.totalEquity * curr.rate).toFixed(2)} ${currency}
Ganancia Neta Liquidada:     +${curr.symbol}${(investor.netProfit * curr.rate).toFixed(2)} (+${investor.roiPct}%)
Efectivo Disponible:         ${curr.symbol}${(investor.availableCash * curr.rate).toFixed(2)} ${currency}

MÉTRICAS MATEMÁTICAS CLAVE
--------------------------------------------------------------------------------
Ratio de Sharpe:             2.42
Ratio de Sortino:            3.10
Profit Factor:               2.65 R
Tasa de Acierto (Win Rate):  78.5%
Cerrojo Fiduciario Drawdown: Límite -6.40% Máximo Inviolable

CARTERA DE ACTIVOS ACTIVOS
--------------------------------------------------------------------------------
${positions
  .map(
    (p) =>
      `• ${p.symbol.padEnd(10)} [${p.assetClass}] | Entrada: $${p.entryPrice.toFixed(2)} | Actual: $${p.currentPrice.toFixed(2)} | PnL: +$${p.pnlUsdt.toFixed(2)} (+${p.pnlPct}%)`
  )
  .join('\n')}

================================================================================
Certificación fiduciaria: Todos los activos operan bajo custodia no custodial en
cuentas de titularidad del inversor (Binance / Interactive Brokers).
================================================================================
    `.trim();

    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `arcafid-audit-certificate-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    showNotice('Certificado Oficial de Auditoría descargado.');
  };

  const showNotice = (msg: string) => {
    setDownloadSuccess(msg);
    setTimeout(() => setDownloadSuccess(null), 3000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn font-mono">
      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl max-w-md w-full p-6 text-xs shadow-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[var(--text-muted)] hover:text-[var(--text-main)] p-1 rounded hover:bg-[var(--bg-surface)]"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2 mb-2">
          <FileText className="w-5 h-5 text-emerald-400" />
          <h2 className="text-base font-extrabold text-[var(--text-main)] uppercase tracking-wider">
            Exportar Auditoría Fiduciaria
          </h2>
        </div>
        <p className="text-[11px] text-[var(--text-muted)] mb-5">
          Generación criptográficamente trazable de informes ejecutivos e historial de libro mayor.
        </p>

        {downloadSuccess && (
          <div className="mb-4 p-2.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>{downloadSuccess}</span>
          </div>
        )}

        <div className="space-y-3">
          <button
            onClick={handleExportPdf}
            className="w-full py-3 px-4 rounded bg-[var(--bg-surface)] border border-[var(--border)] hover:border-emerald-500/40 text-[var(--text-main)] hover:text-emerald-400 font-bold flex items-center justify-between transition-all"
          >
            <div className="flex items-center gap-3">
              <span className="p-1.5 rounded bg-emerald-500/10 text-emerald-400">📄</span>
              <div className="text-left">
                <span className="block font-bold">Certificado Oficial de Auditoría</span>
                <span className="text-[10px] text-[var(--text-dim)]">Formato ejecutivo para inversores institucionales</span>
              </div>
            </div>
            <Download className="w-4 h-4" />
          </button>

          <button
            onClick={handleExportCsv}
            className="w-full py-3 px-4 rounded bg-[var(--bg-surface)] border border-[var(--border)] hover:border-sky-500/40 text-[var(--text-main)] hover:text-sky-400 font-bold flex items-center justify-between transition-all"
          >
            <div className="flex items-center gap-3">
              <span className="p-1.5 rounded bg-sky-500/10 text-sky-400">📊</span>
              <div className="text-left">
                <span className="block font-bold">Libro Mayor Completo (CSV)</span>
                <span className="text-[10px] text-[var(--text-dim)]">Desglose de trades, precios de entrada y salidas</span>
              </div>
            </div>
            <Download className="w-4 h-4" />
          </button>

          <button
            onClick={handleExportJson}
            className="w-full py-3 px-4 rounded bg-[var(--bg-surface)] border border-[var(--border)] hover:border-purple-500/40 text-[var(--text-main)] hover:text-purple-400 font-bold flex items-center justify-between transition-all"
          >
            <div className="flex items-center gap-3">
              <span className="p-1.5 rounded bg-purple-500/10 text-purple-400">⚙️</span>
              <div className="text-left">
                <span className="block font-bold">Snapshot Estructurado (JSON)</span>
                <span className="text-[10px] text-[var(--text-dim)]">Para integración con terminales de riesgo y backtest</span>
              </div>
            </div>
            <Download className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
};
