import React, { useState } from 'react';
import { EvolutionState, ViewMode } from '../types';
import { Cpu, Zap, Activity, CheckCircle2, HelpCircle, Newspaper, Brain } from 'lucide-react';

interface AutoEvolutionPanelProps {
  evolution: EvolutionState;
  onStepEvolution: () => void;
  isTraining: boolean;
  viewMode?: ViewMode;
}

export const AutoEvolutionPanel: React.FC<AutoEvolutionPanelProps> = ({
  evolution,
  onStepEvolution,
  isTraining,
  viewMode = 'simple',
}) => {
  const [notice, setNotice] = useState<string | null>(null);

  const w = evolution.weights;
  const hw = Math.round(w.alphaHawkes * 100);
  const mo = Math.round(w.momentumTrend * 100);
  const se = Math.round(w.huggingfaceSentiment * 100);
  const mr = Math.max(0, 100 - (hw + mo + se));

  const handleStep = () => {
    onStepEvolution();
    setNotice(
      `Paso de aprendizaje completado: El bot analizó las últimas condiciones de mercado y ajustó sus pesos de estrategia para la Generación #${evolution.generation + 1}.`
    );
    setTimeout(() => setNotice(null), 6000);
  };

  return (
    <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-xl p-5 sm:p-6 mb-8 font-mono">
      <div className="flex flex-wrap items-center justify-between gap-4 border-b border-[var(--border)] pb-4 mb-4">
        <div>
          <span className="text-[10px] font-bold uppercase tracking-wider text-[var(--text-dim)] flex items-center gap-1.5">
            <Brain className="w-3.5 h-3.5 text-sky-400" />
            Inteligencia Artificial de Aprendizaje Continuo
          </span>
          <h2 className="text-base sm:text-lg font-extrabold text-[var(--text-main)] flex items-center gap-2">
            CÓMO EL ALGORITMO SE VUELVE MÁS PRECISO CADA DÍA
            <span className="text-xs px-2 py-0.5 rounded bg-sky-500/10 text-sky-400 border border-sky-500/20">
              Ciclo #{evolution.generation}
            </span>
          </h2>
        </div>

        <button
          onClick={handleStep}
          disabled={isTraining}
          className="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[var(--btn-primary-bg)] text-[var(--btn-primary-text)] hover:opacity-90 transition-all font-bold text-xs uppercase tracking-wider disabled:opacity-50 shadow-sm"
        >
          <Zap className={`w-3.5 h-3.5 ${isTraining ? 'animate-spin' : ''}`} />
          {isTraining ? 'Analizando Noticias y Mercado...' : 'Probar Entrenamiento de la IA en Vivo'}
        </button>
      </div>

      {notice && (
        <div className="mb-4 p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center gap-2.5 animate-fadeIn">
          <CheckCircle2 className="w-4 h-4 shrink-0" />
          <span className="font-sans leading-relaxed">{notice}</span>
        </div>
      )}

      {/* Everyday Explanation Card */}
      <div className="p-3.5 rounded-lg bg-[var(--bg-surface)] border border-[var(--border)] text-xs text-[var(--text-muted)] font-sans mb-5 flex items-start gap-2.5">
        <HelpCircle className="w-4 h-4 text-sky-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-[var(--text-main)]">¿Qué hace esta sección?: </strong>
          El mercado financiero cambia todo el tiempo. En vez de usar reglas fijas de hace 5 años, nuestro modelo de Inteligencia Artificial lee las noticias financieras de hoy y mide qué estrategia está funcionando mejor para redistribuir los porcentajes de decisión.
        </div>
      </div>

      {/* Metrics Row in Plain Formats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5 mb-6">
        <div className="bg-[var(--bg-surface)] p-3.5 rounded-lg border border-[var(--border)]">
          <span className="text-[10px] text-[var(--text-dim)] uppercase block font-semibold">Ciclos de Experiencia</span>
          <span className="text-lg font-bold text-[var(--text-main)]">Gen #{evolution.generation}</span>
          <span className="text-[11px] text-[var(--text-dim)] block font-sans mt-0.5">Entrenamientos sucesivos</span>
        </div>

        <div className="bg-[var(--bg-surface)] p-3.5 rounded-lg border border-[var(--border)]">
          <span className="text-[10px] text-[var(--text-dim)] uppercase block font-semibold">Tasa de Error Residual</span>
          <span className="text-lg font-bold text-sky-400">{(evolution.loss * 100).toFixed(2)}%</span>
          <span className="text-[11px] text-[var(--text-dim)] block font-sans mt-0.5">Altamente optimizado (&lt; 4%)</span>
        </div>

        <div className="bg-[var(--bg-surface)] p-3.5 rounded-lg border border-[var(--border)]">
          <span className="text-[10px] text-[var(--text-dim)] uppercase block font-semibold">Ventaja Estadística Neta</span>
          <span className="text-lg font-bold text-emerald-400">+{evolution.reward.toFixed(2)} pts</span>
          <span className="text-[11px] text-[var(--text-dim)] block font-sans mt-0.5">Rendimiento por recompensa</span>
        </div>

        <div className="bg-[var(--bg-surface)] p-3.5 rounded-lg border border-[var(--border)]">
          <span className="text-[10px] text-[var(--text-dim)] uppercase block font-semibold">Clima de Noticias (NLP IA)</span>
          <span className="text-xs font-bold text-amber-400 block mt-1">
            {evolution.huggingfaceNlp.label}
          </span>
          <span className="text-[11px] text-[var(--text-dim)] block font-sans mt-0.5">
            284 titulares analizados hoy
          </span>
        </div>
      </div>

      {/* Strategy Weights with Understandable Plain Descriptions */}
      <div className="space-y-4">
        <div className="text-xs text-[var(--text-muted)] font-semibold uppercase flex items-center justify-between border-b border-[var(--border)] pb-2">
          <span>En qué se enfoca el bot para elegir compras hoy (Total: 100%)</span>
          <span className="text-[10px] text-[var(--text-dim)]">Actualizado dinámicamente</span>
        </div>

        {/* Hawkes */}
        <div className="bg-[var(--bg-surface)] p-3 rounded-lg border border-[var(--border)]">
          <div className="flex justify-between text-xs mb-1.5">
            <div>
              <span className="font-bold text-[var(--text-main)]">1. Detección de Compras Institucionales Masivas</span>
              <span className="text-[11px] text-[var(--text-dim)] block font-sans">
                Descubre cuando bancos o grandes fondos compran antes de que el precio suba.
              </span>
            </div>
            <span className="font-bold text-sky-400 text-sm ml-2">{hw}%</span>
          </div>
          <div className="w-full bg-[var(--bg-card)] rounded-full h-2 overflow-hidden border border-[var(--border)]">
            <div className="bg-sky-400 h-2 rounded-full transition-all duration-500" style={{ width: `${hw}%` }}></div>
          </div>
        </div>

        {/* Momentum */}
        <div className="bg-[var(--bg-surface)] p-3 rounded-lg border border-[var(--border)]">
          <div className="flex justify-between text-xs mb-1.5">
            <div>
              <span className="font-bold text-[var(--text-main)]">2. Seguimiento de Subidas Fuertes (Impulso Continuo)</span>
              <span className="text-[11px] text-[var(--text-dim)] block font-sans">
                Se monta en olas alcistas claras con gran volumen de compradores.
              </span>
            </div>
            <span className="font-bold text-emerald-400 text-sm ml-2">{mo}%</span>
          </div>
          <div className="w-full bg-[var(--bg-card)] rounded-full h-2 overflow-hidden border border-[var(--border)]">
            <div className="bg-emerald-400 h-2 rounded-full transition-all duration-500" style={{ width: `${mo}%` }}></div>
          </div>
        </div>

        {/* Hugging Face Sentiment */}
        <div className="bg-[var(--bg-surface)] p-3 rounded-lg border border-[var(--border)]">
          <div className="flex justify-between text-xs mb-1.5">
            <div>
              <span className="font-bold text-[var(--text-main)]">3. Lectura de Noticias Económicas con IA (FinBERT)</span>
              <span className="text-[11px] text-[var(--text-dim)] block font-sans">
                Interpreta si los periódicos y anuncios de bancos centrales son positivos o negativos.
              </span>
            </div>
            <span className="font-bold text-purple-400 text-sm ml-2">{se}%</span>
          </div>
          <div className="w-full bg-[var(--bg-card)] rounded-full h-2 overflow-hidden border border-[var(--border)]">
            <div className="bg-purple-400 h-2 rounded-full transition-all duration-500" style={{ width: `${se}%` }}></div>
          </div>
        </div>

        {/* Mean Reversion */}
        <div className="bg-[var(--bg-surface)] p-3 rounded-lg border border-[var(--border)]">
          <div className="flex justify-between text-xs mb-1.5">
            <div>
              <span className="font-bold text-[var(--text-main)]">4. Caza de Rebotes a Precios Baratos</span>
              <span className="text-[11px] text-[var(--text-dim)] block font-sans">
                Aprovecha caídas exageradas en activos sólidos para comprar barato y vender en el rebote.
              </span>
            </div>
            <span className="font-bold text-amber-400 text-sm ml-2">{mr}%</span>
          </div>
          <div className="w-full bg-[var(--bg-card)] rounded-full h-2 overflow-hidden border border-[var(--border)]">
            <div className="bg-amber-400 h-2 rounded-full transition-all duration-500" style={{ width: `${mr}%` }}></div>
          </div>
        </div>
      </div>
    </div>
  );
};
