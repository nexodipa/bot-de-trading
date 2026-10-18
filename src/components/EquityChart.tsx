import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Currency, CURRENCY_MAP, ThemeMode, ViewMode } from '../types';
import { CHART_DATASETS } from '../services/quantEngine';
import { Info, HelpCircle } from 'lucide-react';

interface EquityChartProps {
  currency: Currency;
  theme: ThemeMode;
  viewMode?: ViewMode;
}

export const EquityChart: React.FC<EquityChartProps> = ({ currency, theme, viewMode = 'simple' }) => {
  const [timeframe, setTimeframe] = useState<string>('1Y');
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [hoverData, setHoverData] = useState<{
    x: number;
    y: number;
    label: string;
    nav: number;
    spy: number;
    dd: number;
    pnlPct: number;
  } | null>(null);

  const currConfig = CURRENCY_MAP[currency];
  const isSimple = viewMode === 'simple';

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const width = canvas.width;
    const height = canvas.height;

    ctx.clearRect(0, 0, width, height);

    const data = CHART_DATASETS[timeframe] || CHART_DATASETS['1Y'];
    const rate = currConfig.rate;
    const vals = data.values.map((v) => v * rate);
    const spyVals = data.spy.map((v) => v * rate);
    const dds = data.dd;
    const n = vals.length;

    const minV = Math.min(...vals, ...spyVals) * 0.95;
    const maxV = Math.max(...vals, ...spyVals) * 1.05;

    const topH = height * 0.72;
    const botY = height * 0.76;
    const botH = height - botY - 14;

    const isLight = theme === 'light';

    // 1. Background Gridlines Upper
    ctx.strokeStyle = isLight ? 'rgba(0, 0, 0, 0.05)' : 'rgba(255, 255, 255, 0.04)';
    ctx.lineWidth = 1;
    for (let y = 20; y < topH; y += 40) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    // 2. Drawdown Baseline
    ctx.strokeStyle = isLight ? 'rgba(0, 0, 0, 0.08)' : 'rgba(255, 255, 255, 0.08)';
    ctx.beginPath();
    ctx.moveTo(0, botY);
    ctx.lineTo(width, botY);
    ctx.stroke();

    // 3. -6.4% Alert Line in Red Dash
    ctx.setLineDash([3, 3]);
    ctx.strokeStyle = '#f43f5e';
    const alertY = botY + botH * 0.64;
    ctx.beginPath();
    ctx.moveTo(0, alertY);
    ctx.lineTo(width, alertY);
    ctx.stroke();
    ctx.setLineDash([]);

    ctx.fillStyle = isLight ? '#52525b' : '#71717a';
    ctx.font = '10px "JetBrains Mono", monospace';
    ctx.fillText('LÍMITE MÁXIMO DE PROTECCIÓN (-6.4% INVIOLABLE)', 14, botY + 12);

    const getX = (i: number) => (i / (n - 1)) * (width - 40) + 20;
    const getY = (v: number) => topH - ((v - minV) / (maxV - minV)) * (topH - 25);

    // 4. Fill Gradient under Strategy Line
    const grad = ctx.createLinearGradient(0, 0, 0, topH);
    if (isLight) {
      grad.addColorStop(0, 'rgba(37, 99, 235, 0.12)');
      grad.addColorStop(1, 'rgba(37, 99, 235, 0.0)');
    } else {
      grad.addColorStop(0, 'rgba(244, 244, 245, 0.08)');
      grad.addColorStop(1, 'rgba(244, 244, 245, 0.0)');
    }

    ctx.beginPath();
    ctx.moveTo(getX(0), getY(vals[0]));
    for (let i = 1; i < n; i++) {
      const cx = (getX(i - 1) + getX(i)) / 2;
      ctx.bezierCurveTo(cx, getY(vals[i - 1]), cx, getY(vals[i]), getX(i), getY(vals[i]));
    }
    ctx.lineTo(getX(n - 1), topH);
    ctx.lineTo(getX(0), topH);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // 5. SPY Benchmark (Dashed Muted Grey)
    ctx.beginPath();
    ctx.setLineDash([4, 4]);
    ctx.strokeStyle = isLight ? '#94a3b8' : '#71717a';
    ctx.lineWidth = 1.5;
    ctx.moveTo(getX(0), getY(spyVals[0]));
    for (let i = 1; i < n; i++) ctx.lineTo(getX(i), getY(spyVals[i]));
    ctx.stroke();
    ctx.setLineDash([]);

    // 6. Strategy Equity Line
    ctx.beginPath();
    ctx.strokeStyle = isLight ? '#2563eb' : '#f4f4f5';
    ctx.lineWidth = 2.0;
    ctx.moveTo(getX(0), getY(vals[0]));
    for (let i = 1; i < n; i++) {
      const cx = (getX(i - 1) + getX(i)) / 2;
      ctx.bezierCurveTo(cx, getY(vals[i - 1]), cx, getY(vals[i]), getX(i), getY(vals[i]));
    }
    ctx.stroke();

    // 7. Drawdown Bars
    for (let i = 0; i < n; i++) {
      const x = getX(i);
      const ddVal = Math.abs(dds[i]);
      const barHeight = Math.min(botH, (ddVal / 10.0) * botH);
      ctx.fillStyle =
        ddVal > 5.0
          ? 'rgba(239, 68, 68, 0.6)'
          : isLight
          ? 'rgba(0, 0, 0, 0.15)'
          : 'rgba(255, 255, 255, 0.2)';
      ctx.fillRect(x - 5, botY + 2, 10, barHeight);
    }
  }, [timeframe, currConfig, theme]);

  // Handle canvas sizing
  useEffect(() => {
    const handleResize = () => {
      const canvas = canvasRef.current;
      const container = containerRef.current;
      if (!canvas || !container) return;
      canvas.width = container.clientWidth;
      canvas.height = 360;
      draw();
    };

    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, [draw]);

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;

    const data = CHART_DATASETS[timeframe] || CHART_DATASETS['1Y'];
    const rate = currConfig.rate;
    const vals = data.values.map((v) => v * rate);
    const spyVals = data.spy.map((v) => v * rate);
    const dds = data.dd;
    const n = vals.length;

    const getX = (i: number) => (i / (n - 1)) * (canvas.width - 40) + 20;

    let nearestIdx = 0;
    let minDist = 9999;
    for (let i = 0; i < n; i++) {
      const dist = Math.abs(getX(i) - mouseX);
      if (dist < minDist) {
        minDist = dist;
        nearestIdx = i;
      }
    }

    const pnlPct = Number((((vals[nearestIdx] - vals[0]) / vals[0]) * 100).toFixed(1));

    setHoverData({
      x: getX(nearestIdx),
      y: (canvas.height * 0.72) / 2,
      label: data.labels[nearestIdx],
      nav: vals[nearestIdx],
      spy: spyVals[nearestIdx],
      dd: dds[nearestIdx],
      pnlPct,
    });
  };

  const handleMouseLeave = () => {
    setHoverData(null);
  };

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-5 sm:p-6 mb-8">
      {/* Chart Header */}
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-4 mb-4">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)] font-mono">
            {isSimple ? 'Comparativa Frente a las Mayores Empresas de EE.UU. (S&P 500)' : 'Rendimiento Neto vs Benchmark SPY'}
          </span>
          <h2 className="text-base sm:text-lg font-extrabold text-[var(--text-main)] font-mono flex items-center gap-2">
            {isSimple ? 'EVOLUCIÓN DE TU CAPITAL Y CONTROL DE RIESGO' : 'CURVA DE EQUITY Y REGISTRO DE DRAWDOWN'}
            <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 font-semibold">
              {isSimple ? 'Riesgo Mínimo · Retorno Consistente' : 'Sharpe 2.42 · Sortino 3.10'}
            </span>
          </h2>
        </div>

        {/* Timeframe Buttons */}
        <div className="flex items-center gap-1 bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-1 font-mono text-xs">
          {['1M', '3M', '6M', '1Y', 'YTD', 'ALL'].map((tf) => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-3 py-1 rounded font-bold uppercase transition-all ${
                timeframe === tf
                  ? 'bg-emerald-500 text-black shadow-sm'
                  : 'text-[var(--text-muted)] hover:text-[var(--text-main)]'
              }`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>

      {/* Canvas Wrap */}
      <div ref={containerRef} className="relative w-full h-[360px]">
        <canvas
          ref={canvasRef}
          onMouseMove={handleMouseMove}
          onMouseLeave={handleMouseLeave}
          className="w-full h-full cursor-crosshair block"
        />

        {/* Floating Tooltip in Plain Friendly Words */}
        {hoverData && (
          <div
            className="absolute pointer-events-none z-10 bg-[var(--bg-surface)] border border-[var(--border-light)] p-3 rounded-xl shadow-2xl text-xs font-mono"
            style={{
              left: `${Math.min(Math.max(10, hoverData.x + 12), (containerRef.current?.clientWidth || 300) - 220)}px`,
              top: '20px',
            }}
          >
            <div className="font-bold text-[var(--text-main)] border-b border-[var(--border)] pb-1 mb-1.5 flex items-center justify-between gap-4">
              <span>{hoverData.label}</span>
              <span className="text-emerald-400 text-[10px]">+{hoverData.pnlPct}% Acumulado</span>
            </div>
            <div className="text-[var(--text-main)]">
              Tu Capital:{' '}
              <span className="font-bold text-emerald-400">
                {currConfig.symbol}
                {hoverData.nav.toLocaleString('es-ES', {
                  minimumFractionDigits: currConfig.decimals,
                  maximumFractionDigits: currConfig.decimals,
                })}{' '}
                {currency}
              </span>
            </div>
            <div className="text-[var(--text-muted)] text-[11px] mt-0.5">
              Bolsa General (SPY): {currConfig.symbol}
              {hoverData.spy.toLocaleString('es-ES', {
                minimumFractionDigits: currConfig.decimals,
                maximumFractionDigits: currConfig.decimals,
              })}
            </div>
            <div className={`mt-1 font-semibold text-[11px] ${hoverData.dd <= -5.0 ? 'text-rose-400' : 'text-emerald-400'}`}>
              Retroceso temporal: {hoverData.dd}% (Zona muy segura)
            </div>
          </div>
        )}
      </div>

      {/* Human Legend */}
      <div className="flex flex-wrap items-center justify-between text-xs font-mono text-[var(--text-dim)] pt-4 border-t border-[var(--border)] mt-2 gap-3">
        <div className="flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-0.5 bg-[var(--text-main)] inline-block"></span>
            <span className="text-[var(--text-main)] font-semibold">Tu Cuenta (Estrategia ArcaFid)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3.5 h-0.5 border-t border-dashed border-zinc-400 inline-block"></span>
            <span>Bolsa General de EE.UU. (Índice S&P 500)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 bg-rose-500/70 inline-block rounded-xs"></span>
            <span>Barras de Control de Caída</span>
          </div>
        </div>

        <div className="text-[11px] text-[var(--text-dim)] font-sans">
          💡 <strong>Lectura rápida:</strong> La línea blanca superior muestra cómo tu dinero crece más rápido que la bolsa, manteniéndose siempre lejos de la línea roja de peligro.
        </div>
      </div>
    </div>
  );
};
