# ARCAFID QUANTITATIVE ASSET MANAGEMENT · React Quantitative Syndicate & Alpha Engine

[![React 18](https://img.shields.io/badge/React-18.3-blue.svg)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue.svg)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-6.0-purple.svg)](https://vitejs.dev/)
[![Tailwind CSS](https://img.shields.io/badge/TailwindCSS-4.0-38bdf8.svg)](https://tailwindcss.com/)
[![License: Institutional](https://img.shields.io/badge/license-Institutional-navy.svg)](#licencia)

Plataforma de gestión de activos cuantitativos de grado institucional y sindicato algorítmico autónomo **ArcaFid Quantitative**, reescrita integralmente como aplicación **React (Vite + TypeScript + Tailwind CSS)**. Diseñada para la ejecución sistemática de estrategias multiactivo híbridas (Criptoactivos líderes en Binance y Acciones en Interactive Brokers), supervisión fiduciaria con cerrojo de drawdown de -6.4%, optimización auto-evolutiva RL, y un portal web con conmutador dual Terminal Oscuro / Institucional Claro.

---

## Características Principales

1. **Portal Inversor Institucional**:
   - Curva de Equity interactiva con canvas de alta precisión y comparación frente al benchmark SPY.
   - Histograma de Drawdown con línea de advertencia fiduciaria de -6.4%.
   - Conmutador multi-divisa (USD $, EUR €, GBP £, BTC ₿) con recálculo dinámico en tiempo real.
   - Simulador cuantitativo de ROI con interés compuesto vs distribución mensual de dividendos.
   - Conciliación de depósitos fiduciarios no-custodiales (USDT TRC20, ERC20, Polygon) con verificación on-chain (TXID).
   - Exportación de informes de auditoría en formatos PDF/Certificado, CSV (Libro Mayor) y JSON.

2. **Centro de Mando & Control Operativo (Workstation)**:
   - Panel de control del motor algorítmico con botón de parada de emergencia / trading en vivo.
   - Escáner multidimensional de señales con indicadores técnicos en tiempo real (RSI, ATR, Volumen Z-score).
   - Inmunidad de Auto-Tuning con umbrales acotados (Clamped $\le 0.55$) para prevenir sobreoptimización.
   - Registro de telemetría y auditoría en lenguaje natural fiduciario (sin jerga críptica).

3. **Motor Auto-Evolutivo RL & Hugging Face FinBERT**:
   - Ajuste dinámico de pesos de estrategias (Alpha Hawkes, Momentum Trend, Hugging Face Sentiment, Mean Reversion).
   - Muestreo de Thompson y gradiente estocástico ejecutable interactivamente en vivo.
   - Puntuación de sentimiento de noticias y titulares financieros.

4. **Panel Unificado Multi-Broker**:
   - Consolidación de Binance Trading Spot + Binance Earn & Staking + Interactive Brokers (IBKR TWS API).
   - Resumen de posiciones abiertas (#NVDA, #MSFT, #AAPL, SOL/USDT, BTC/USDT, ETH/USDT).

5. **Tesis Fehu (Pitch Deck Institucional)**:
   - Presentación interactiva de los 4 pilares: Seguridad Fiduciaria (Lo que Hacemos vs Lo que NUNCA Hacemos), Ventaja Estadística, Honorarios 100% a Éxito (0% Gestión) e Infografía Oficial Fehu (ᚠ).

---

## Ejecución Local

```bash
# Instalar dependencias
npm install

# Iniciar servidor de desarrollo en puerto 3000
npm run dev

# Compilar para producción
npm run build
```
