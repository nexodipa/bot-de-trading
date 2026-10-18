import React, { useState } from 'react';
import { ShieldCheck, TrendingUp, Handshake, Image as ImageIcon, CheckCircle, XCircle } from 'lucide-react';

export const PitchDeck: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'trust' | 'simulator' | 'fees' | 'infographic'>('trust');

  return (
    <div className="font-mono max-w-5xl mx-auto space-y-6">
      {/* Brand Header */}
      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-6 sm:p-8 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-bold text-base flex items-center justify-center">
              ᚠ
            </span>
            <span className="text-xs font-semibold tracking-wider uppercase text-emerald-400">
              Etimología Fehu // Capital Productivo y Preservación de Valor
            </span>
          </div>
          <h2 className="text-xl sm:text-2xl font-extrabold text-[var(--text-main)]">
            Proyecto Fehu // Gestión Cuantitativa de Activos
          </h2>
          <p className="text-xs sm:text-sm text-[var(--text-muted)] mt-1 max-w-2xl">
            Modelos cuantitativos no-custodiales de retorno absoluto para Criptoactivos líderes (Binance) y Wall Street (Interactive Brokers).
          </p>
        </div>

        <div className="self-start sm:self-auto shrink-0">
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
            Auditoría Continua de Libro Mayor
          </span>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex border-b border-[var(--border)] bg-[var(--bg-card)] px-4 sm:px-6 gap-4 sm:gap-6 overflow-x-auto text-xs">
        <button
          onClick={() => setActiveTab('trust')}
          className={`py-3 px-2 font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'trust'
              ? 'border-emerald-400 text-emerald-400'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]'
          }`}
        >
          🛡️ Seguridad Fiduciaria (Hacemos vs NUNCA Hacemos)
        </button>

        <button
          onClick={() => setActiveTab('simulator')}
          className={`py-3 px-2 font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'simulator'
              ? 'border-emerald-400 text-emerald-400'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]'
          }`}
        >
          📈 Tesis de Inversión & Ventaja Estadística
        </button>

        <button
          onClick={() => setActiveTab('fees')}
          className={`py-3 px-2 font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'fees'
              ? 'border-emerald-400 text-emerald-400'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]'
          }`}
        >
          🤝 Honorarios 100% a Éxito (0% Gestión)
        </button>

        <button
          onClick={() => setActiveTab('infographic')}
          className={`py-3 px-2 font-bold border-b-2 transition-all whitespace-nowrap ${
            activeTab === 'infographic'
              ? 'border-emerald-400 text-emerald-400'
              : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-main)]'
          }`}
        >
          🖼️ Infografía Oficial (ᚠ)
        </button>
      </div>

      {/* TAB 1: TRUST & FIDUCIARY PILLARS */}
      {activeTab === 'trust' && (
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-6 sm:p-8 space-y-6">
          <div className="p-4 rounded-xl bg-white/[0.02] border border-[var(--border)] text-xs sm:text-sm text-[var(--text-muted)] leading-relaxed">
            <strong className="text-[var(--text-main)]">Criterio del Inversor Institucional:</strong> Los rendimientos extraordinarios sostenibles no provienen de la especulación temeraria ni de promesas mágicas, sino de dos factores innegociables: <em className="text-[var(--text-main)]">ventaja estadística demostrable</em> y <em className="text-[var(--text-main)]">disciplina férrea en la preservación del capital</em>. Nuestro primer mandato fiduciario no es cuánto ganar, sino garantizar que el capital principal esté matemáticamente blindado ante cualquier régimen de mercado.
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* LO QUE HACEMOS */}
            <div className="bg-[var(--bg-surface)] border border-emerald-500/20 rounded-xl p-5 space-y-4">
              <div className="flex items-center gap-2 text-emerald-400 font-extrabold text-sm border-b border-emerald-500/20 pb-3">
                <CheckCircle className="w-5 h-5" />
                LO QUE HACEMOS (BLINDAJE RIGUROSO)
              </div>
              <ul className="space-y-3 text-xs text-[var(--text-muted)]">
                <li className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>Custodia 100% No Custodial:</strong> El capital permanece en las cuentas propias del cliente en Binance o Interactive Brokers, conectadas vía API restringida a operaciones SPOT (sin permisos de retiro ni apalancamiento).</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>Freno Automático de Drawdown:</strong> Parada dura inviolable al -6.4% de drawdown diario, desconectando compras automáticamente para salvaguardar el principal.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>Cascada Multi-Estrategia Activa:</strong> Selección dinámica entre procesos de Hawkes, Active Momentum y Mean Reversion según el régimen de volatilidad.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-emerald-400 font-bold">✓</span>
                  <span><strong>Optimización Auto-Evolutiva RL:</strong> Calibración periódica de hiperparámetros mediante muestreo de Thompson y aprendizaje por refuerzo contra sobreajuste.</span>
                </li>
              </ul>
            </div>

            {/* LO QUE NUNCA HACEMOS */}
            <div className="bg-[var(--bg-surface)] border border-rose-500/20 rounded-xl p-5 space-y-4">
              <div className="flex items-center gap-2 text-rose-400 font-extrabold text-sm border-b border-rose-500/20 pb-3">
                <XCircle className="w-5 h-5" />
                LO QUE NUNCA HACEMOS (LÍNEAS ROJAS)
              </div>
              <ul className="space-y-3 text-xs text-[var(--text-muted)]">
                <li className="flex items-start gap-2">
                  <span className="text-rose-400 font-bold">✕</span>
                  <span><strong>Cero Apalancamiento Excesivo:</strong> No operamos derivados con liquidación forzosa ni apalancamientos salvajes de 10x-100x que pongan en riesgo la cuenta en caídas de mercado.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-rose-400 font-bold">✕</span>
                  <span><strong>Cero Monedas Basura / Memecoins:</strong> Exclusivamente activos de alta liquidez global (BTC, ETH, SOL) y acciones blue-chip del S&P 500 / NASDAQ.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-rose-400 font-bold">✕</span>
                  <span><strong>Cero Retención de Fondos:</strong> Nosotros nunca tocamos ni custodiamos el dinero; no existen bloqueos forzosos ni comisiones por retiro.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-rose-400 font-bold">✕</span>
                  <span><strong>Cero Martingala o Promediado a la Baja:</strong> Si una tesis falla, el stop loss se ejecuta de inmediato sin perseguir pérdidas.</span>
                </li>
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* TAB 2: THESIS & STATISTICAL ADVANTAGE */}
      {activeTab === 'simulator' && (
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-6 sm:p-8 space-y-6 text-xs text-[var(--text-muted)]">
          <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
            <TrendingUp className="w-4 h-4" />
            TESIS MATEMÁTICA Y MATRIZ DE RIESGO
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-4 bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg">
              <span className="text-[10px] text-[var(--text-dim)] uppercase block">Ratio de Sharpe</span>
              <div className="text-xl font-bold text-emerald-400 mt-1">2.42</div>
              <p className="text-[11px] text-[var(--text-dim)] mt-1">Rentabilidad ajustada al riesgo muy superior a la media de hedge funds (1.20).</p>
            </div>

            <div className="p-4 bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg">
              <span className="text-[10px] text-[var(--text-dim)] uppercase block">Ratio de Sortino</span>
              <div className="text-xl font-bold text-emerald-400 mt-1">3.10</div>
              <p className="text-[11px] text-[var(--text-dim)] mt-1">Penaliza únicamente la volatilidad bajista perjudicial para el inversor.</p>
            </div>

            <div className="p-4 bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg">
              <span className="text-[10px] text-[var(--text-dim)] uppercase block">Profit Factor</span>
              <div className="text-xl font-bold text-emerald-400 mt-1">2.65 R</div>
              <p className="text-[11px] text-[var(--text-dim)] mt-1">Ganancias brutas acumuladas equivalen a 2.65 veces las pérdidas totales asumidas.</p>
            </div>
          </div>

          <div className="p-4 bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg space-y-2">
            <h4 className="font-bold text-[var(--text-main)] uppercase text-xs">Desglose de las 4 Fuentes de Alpha:</h4>
            <p>1. <strong>Procesos de Hawkes:</strong> Detección de auto-excitación en libros de órdenes de alta frecuencia para capturar compras institucionales antes de su impacto pleno.</p>
            <p>2. <strong>Active Momentum:</strong> Incorporado en M2 para surfear extensiones de tendencia intradiarias con confirmación de volumen institucional (Z-score &gt; 1.5σ).</p>
            <p>3. <strong>Procesamiento NLP Hugging Face FinBERT:</strong> Escaneo continuo de noticias y titulares financieros para anticipar shifts de sentimiento macroeconómico.</p>
            <p>4. <strong>Reversión a la Media Dinámica:</strong> Entradas de alta probabilidad cuando activos sobrevendidos tocan soportes estructurales con volatilidad comprimida.</p>
          </div>
        </div>
      )}

      {/* TAB 3: 100% SUCCESS FEES */}
      {activeTab === 'fees' && (
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-6 sm:p-8 space-y-6">
          <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
            <Handshake className="w-5 h-5" />
            ALINEACIÓN DE INTERESES: 0% GESTIÓN · 100% A ÉXITO
          </div>

          <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-xs sm:text-sm text-emerald-300 leading-relaxed">
            <strong>Principio Fundamental de Respeto al Inversor:</strong> A diferencia de los bancos y fondos tradicionales que cobran entre un 2% y 3% anual fijo sin importar si el cliente gana o pierde dinero, en ArcaFid operamos bajo un mandato estricto de <strong className="text-white">High-Water Mark</strong>.
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs">
            <div className="p-4 bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg">
              <span className="text-[10px] text-[var(--text-dim)] uppercase block">Comisión de Gestión Fija</span>
              <div className="text-2xl font-extrabold text-emerald-400 mt-1">0.00%</div>
              <p className="text-[11px] text-[var(--text-dim)] mt-1">Nunca cobramos por simplemente tener su cuenta conectada ni por custodiar capital.</p>
            </div>

            <div className="p-4 bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg">
              <span className="text-[10px] text-[var(--text-dim)] uppercase block">Comisión a Éxito (Success Fee)</span>
              <div className="text-2xl font-extrabold text-[var(--text-main)] mt-1">20% - 25%</div>
              <p className="text-[11px] text-[var(--text-dim)] mt-1">Aplicada únicamente sobre las ganancias netas efectivamente liquidadas (High-Water Mark).</p>
            </div>
          </div>
        </div>
      )}

      {/* TAB 4: INFOGRAPHIC */}
      {activeTab === 'infographic' && (
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-6 sm:p-8 space-y-4">
          <div className="flex items-center justify-between border-b border-[var(--border)] pb-3">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
              <ImageIcon className="w-4 h-4" />
              INFOGRAFÍA OFICIAL DE ARQUITECTURA FEHU (ᚠ)
            </div>
            <a
              href="/fehu_infographic.jpg"
              target="_blank"
              rel="noreferrer"
              className="text-xs text-[var(--text-dim)] hover:text-emerald-400 underline font-semibold"
            >
              Ver en alta resolución
            </a>
          </div>

          <div className="bg-[var(--bg-base)] border border-[var(--border)] rounded-lg p-2 flex items-center justify-center overflow-hidden">
            <img
              src="/fehu_infographic.jpg"
              alt="Infografía Proyecto Fehu"
              className="max-h-[500px] w-auto object-contain rounded"
              onError={(e) => {
                // fallback if not available
                (e.target as HTMLElement).style.display = 'none';
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
};
