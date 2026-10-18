import React, { useState } from 'react';
import { X, Check, Copy, Shield, ExternalLink, ArrowRight, HelpCircle, CheckCircle2 } from 'lucide-react';
import confetti from 'canvas-confetti';

interface DepositModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccessDeposit: (amount: number, tier: string, txid: string) => void;
}

export const DepositModal: React.FC<DepositModalProps> = ({ isOpen, onClose, onSuccessDeposit }) => {
  const [network, setNetwork] = useState<'TRC20' | 'ERC20' | 'POLYGON'>('TRC20');
  const [copied, setCopied] = useState(false);
  const [txid, setTxid] = useState('');
  const [amount, setAmount] = useState('5000');
  const [name, setName] = useState('Alejandro Dupont');
  const [tier, setTier] = useState('Syndicate Multi-Asset');
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const wallets = {
    TRC20: 'TLZ8vG3QJ5YF9r7wA1xN2kM4p6Bc7De9Fg',
    ERC20: '0x892a7C53f47eD1B69c1184a4608cDf0eC90b4D77',
    POLYGON: '0x892a7C53f47eD1B69c1184a4608cDf0eC90b4D77',
  };

  const handleCopy = () => {
    navigator.clipboard.writeText(wallets[network]);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!txid.trim()) {
      alert('Por favor ingrese el Hash de Transacción (TXID) o código de comprobante para vincular su dinero.');
      return;
    }

    setIsSubmitting(true);
    setTimeout(() => {
      setIsSubmitting(false);
      try {
        confetti({
          particleCount: 80,
          spread: 70,
          origin: { y: 0.6 },
        });
      } catch (err) {}
      onSuccessDeposit(Number(amount) || 5000, tier, txid);
      onClose();
    }, 1200);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded-2xl max-w-lg w-full p-6 sm:p-7 text-xs font-mono shadow-2xl relative max-h-[92vh] overflow-y-auto">
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-[var(--text-muted)] hover:text-[var(--text-main)] p-1 rounded hover:bg-[var(--bg-surface)]"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center gap-2.5 mb-2">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center font-bold text-base">
            ᚠ
          </div>
          <div>
            <h2 className="text-base font-extrabold text-[var(--text-main)] uppercase tracking-wider">
              Cómo Añadir Dinero a Tu Cuenta
            </h2>
            <p className="text-[11px] text-[var(--text-muted)] font-sans">
              Proceso simple en 3 pasos · Tu dinero siempre bajo tu propia titularidad
            </p>
          </div>
        </div>

        {/* Informative pill */}
        <div className="my-4 p-3 rounded-xl bg-emerald-500/5 border border-emerald-500/15 text-emerald-300 text-xs font-sans flex items-start gap-2">
          <Shield className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
          <span>
            <strong>Garantía de tranquilidad:</strong> Las operaciones son no-custodiales. Nadie puede bloquearte ni cobrar comisiones ocultas.
          </span>
        </div>

        {/* Network Selector */}
        <div className="mb-4">
          <label className="text-[11px] text-[var(--text-main)] font-bold block mb-1.5 font-sans">
            Paso 1: Elige la red donde tienes tus dólares digitales (USDT)
          </label>
          <div className="grid grid-cols-3 gap-2">
            {(['TRC20', 'ERC20', 'POLYGON'] as const).map((net) => (
              <button
                key={net}
                type="button"
                onClick={() => setNetwork(net)}
                className={`py-2 px-3 rounded-lg border text-center font-bold transition-all ${
                  network === net
                    ? 'border-emerald-500 bg-emerald-500/10 text-emerald-400'
                    : 'border-[var(--border)] bg-[var(--bg-surface)] text-[var(--text-muted)] hover:text-[var(--text-main)]'
                }`}
              >
                <div>{net}</div>
                <div className="text-[9px] font-normal font-sans opacity-80">
                  {net === 'TRC20' ? 'Comisión ~$1' : net === 'POLYGON' ? 'Comisión ~$0.05' : 'Red Ethereum'}
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Address Display & Copy */}
        <div className="mb-4">
          <label className="text-[11px] text-[var(--text-main)] font-bold block mb-1.5 font-sans">
            Paso 2: Copia esta dirección y envía el dinero desde tu app de Binance o Wallet
          </label>
          <div className="flex items-center gap-2 bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl p-3">
            <span className="truncate text-[var(--text-main)] font-semibold select-all text-xs font-mono">
              {wallets[network]}
            </span>
            <button
              type="button"
              onClick={handleCopy}
              className="px-3 py-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border)] hover:bg-[var(--bg-card-hover)] text-[var(--text-main)] shrink-0 transition-colors flex items-center gap-1.5 font-bold font-sans text-xs"
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4 text-emerald-400" />
                  <span className="text-emerald-400">¡Copiado!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  <span>Copiar</span>
                </>
              )}
            </button>
          </div>
        </div>

        {/* Verification Form */}
        <form onSubmit={handleSubmit} className="space-y-3.5">
          <label className="text-[11px] text-[var(--text-main)] font-bold block font-sans">
            Paso 3: Confirma tus datos para vincular el saldo a tu panel
          </label>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[10px] text-[var(--text-dim)] uppercase block mb-1">Tu Nombre Completo</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-2.5 text-[var(--text-main)] focus:outline-none focus:border-emerald-500"
                required
              />
            </div>
            <div>
              <label className="text-[10px] text-[var(--text-dim)] uppercase block mb-1">Monto Enviado (USDT)</label>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                className="w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-2.5 text-[var(--text-main)] focus:outline-none focus:border-emerald-500"
                required
              />
            </div>
          </div>

          <div>
            <label className="text-[10px] text-[var(--text-dim)] uppercase block mb-1">Tipo de Plan de Inversión</label>
            <select
              value={tier}
              onChange={(e) => setTier(e.target.value)}
              className="w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-2.5 text-[var(--text-main)] focus:outline-none focus:border-emerald-500"
            >
              <option value="Quant Alpha Core">Plan Inicial ($1,000 - $10,000)</option>
              <option value="Syndicate Multi-Asset">Plan Sindicato Multi-Activo ($10,000 - $100,000)</option>
              <option value="Institutional Prime High-Net-Worth">Plan Institucional (&gt; $100,000)</option>
            </select>
          </div>

          <div>
            <label className="text-[10px] text-[var(--text-dim)] uppercase block mb-1">
              Código de Comprobante o Hash (TXID) de tu Transferencia
            </label>
            <input
              type="text"
              placeholder="Ej: 0x9f83b... o el código que te da tu exchange"
              value={txid}
              onChange={(e) => setTxid(e.target.value)}
              className="w-full bg-[var(--bg-surface)] border border-[var(--border)] rounded-lg p-2.5 text-[var(--text-main)] focus:outline-none focus:border-emerald-500"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-4 py-3 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-black font-extrabold text-xs uppercase tracking-wider flex items-center justify-center gap-2 transition-all disabled:opacity-50 shadow-md"
          >
            {isSubmitting ? (
              <span>Verificando transferencia en la red...</span>
            ) : (
              <>
                <span>Confirmar y Empezar a Rendir</span>
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>
      </div>
    </div>
  );
};
