import { Currency, CURRENCY_MAP } from '../types';

export interface FormattedMoney {
  formatted: string;
  symbol: string;
  amount: number;
  currency: Currency;
  plainText: string;
}

/**
 * Formato de dinero claro y legible para cualquier persona
 */
export function formatMoney(amount: number, currency: Currency = 'USD'): string {
  const config = CURRENCY_MAP[currency];
  const converted = amount * config.rate;
  const decimals = currency === 'BTC' ? 4 : 2;
  
  const formattedNumber = converted.toLocaleString('es-ES', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  return `${config.symbol} ${formattedNumber} ${currency}`;
}

export function formatCompactNumber(num: number): string {
  if (num >= 1000000) {
    return `${(num / 1000000).toFixed(1)} Millones`;
  }
  if (num >= 1000) {
    return `${(num / 1000).toFixed(1)} Mil`;
  }
  return num.toString();
}

export interface MetricExplanation {
  title: string;
  humanName: string;
  humanExplanation: string;
  statusLevel: 'excelente' | 'bueno' | 'protegido';
  everydayAnalogy: string;
}

export const METRIC_EXPLANATIONS: Record<string, MetricExplanation> = {
  sharpe: {
    title: 'Ratio de Sharpe (2.42)',
    humanName: 'Calidad del Rendimiento vs Riesgo',
    humanExplanation: 'Mide cuánta ganancia obtienes por cada gota de riesgo. Una puntuación mayor a 2.0 se considera de grado élite mundial.',
    statusLevel: 'excelente',
    everydayAnalogy: 'Como conducir un auto a 120 km/h pero con frenos de Fórmula 1 y cinturones de máxima seguridad.',
  },
  drawdown: {
    title: 'Límite de Drawdown (-6.4%)',
    humanName: 'Freno de Protección de Capital',
    humanExplanation: 'Es lo máximo que puede llegar a retroceder temporalmente tu cuenta. Si el mercado entra en pánico, el bot apaga las compras para proteger tu dinero.',
    statusLevel: 'protegido',
    everydayAnalogy: 'Un cortacircuitos en tu casa: si hay una sobrecarga eléctrica, salta la llave antes de que se quemen los electrodomésticos.',
  },
  winRate: {
    title: 'Tasa de Acierto (78.5%)',
    humanName: 'Efectividad de Operaciones',
    humanExplanation: 'De cada 10 operaciones que realiza el sistema, casi 8 terminan con ganancias cerradas en tu bolsillo.',
    statusLevel: 'excelente',
    everydayAnalogy: 'Un goleador que anota 8 de cada 10 penales que patea.',
  },
  profitFactor: {
    title: 'Factor de Beneficio (2.65 R)',
    humanName: 'Relación Ganancia / Pérdida',
    humanExplanation: 'Por cada $1 dólar que se ha cedido en pequeñas pérdidas controladas, el sistema ha generado $2.65 dólares de beneficio limpio.',
    statusLevel: 'excelente',
    everydayAnalogy: 'Metes $1 en una máquina y te devuelve $2.65 de promedio de forma consistente.',
  },
  custodia: {
    title: 'Custodia No Custodial',
    humanName: 'Tu Dinero Siempre en Tu Poder',
    humanExplanation: 'Nadie más tiene acceso a retirar tu dinero. Los fondos están en tu propia cuenta bancaria o de Binance/IBKR con tus claves personales.',
    statusLevel: 'protegido',
    everydayAnalogy: 'Le das las llaves del auto al chofer para que lo maneje, pero los papeles de propiedad y la cuenta del banco son 100% tuyos.',
  },
};
