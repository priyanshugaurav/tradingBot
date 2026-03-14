import type { Trade } from '../api';
import { TrendingUp, TrendingDown, Brain, Shield, Crosshair, XCircle, Loader2 } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { useState } from 'react';
import { api } from '../api';

function TradeCard({ trade, onClose }: { trade: Trade; onClose?: (id: number) => Promise<void> }) {
  const [closing, setClosing] = useState(false);
  const isOpen = trade.status === 'OPEN';
  const isBuy = trade.side === 'BUY';
  const pnlColor = (trade.pnl ?? 0) >= 0 ? 'text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.3)]' : 'text-red-400';

  const handleClose = async () => {
    if (!onClose) return;
    setClosing(true);
    try {
      await onClose(trade.id);
    } finally {
      setClosing(false);
    }
  };

  return (
    <div className={`relative p-5 rounded-2xl border transition-all duration-300 group hover:shadow-xl ${isOpen
      ? 'border-emerald-500/20 bg-gradient-to-br from-emerald-500/[0.03] to-[#121214]/80 shadow-[0_0_15px_rgba(16,185,129,0.05)]'
      : 'border-white/5 bg-[#121214]/60 hover:border-white/10 hover:bg-[#121214]/80'
      }`}>

      {/* ── CARD HEADER ── */}
      <div className="flex justify-between items-start mb-5 pb-3 border-b border-white/[0.05]">
        <div className="flex items-center gap-3">
          <div className={`p-1.5 rounded-lg ${isBuy ? 'bg-emerald-500/10' : 'bg-red-500/10'}`}>
            {isBuy ? <TrendingUp className="w-4 h-4 text-emerald-400" /> : <TrendingDown className="w-4 h-4 text-red-400" />}
          </div>
          <span className="font-bold text-white text-sm uppercase tracking-widest">{trade.symbol}</span>
          <span className={`text-[10px] px-2 py-0.5 rounded-md border font-bold tracking-widest uppercase ${isBuy
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
            : 'bg-red-500/10 text-red-400 border-red-500/20'
            }`}>
            {trade.side}
          </span>
          {trade.is_trailing_active && (
            <span className="text-[10px] px-2 py-0.5 rounded-md border border-amber-500/30 bg-amber-500/10 text-amber-400 font-bold tracking-widest uppercase flex items-center gap-1 shadow-[0_0_10px_rgba(245,158,11,0.1)]">
              <Shield className="w-3 h-3" /> TSL
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isOpen && onClose && (
            <button
              onClick={handleClose}
              disabled={closing}
              className={`text-[9px] font-bold tracking-widest uppercase px-3 py-1 rounded-md border transition-all flex items-center gap-1.5 
                ${closing ? 'bg-zinc-800 text-zinc-500 border-zinc-700' : 'bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20 hover:border-red-500/40'}`}
              title="Close position manually"
            >
              {closing ? <Loader2 className="w-3 h-3 animate-spin" /> : <XCircle className="w-3 h-3" />}
              {closing ? 'CLOSING...' : 'CLOSE'}
            </button>
          )}
          <span className={`text-[9px] font-bold tracking-widest uppercase px-2 py-1 rounded-md border ${isOpen
            ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
            : 'bg-white/5 text-zinc-500 border-white/5'
            }`}>
            {trade.status}
          </span>
        </div>
      </div>

      {/* ── DATA GRID ── */}
      <div className="grid grid-cols-3 gap-y-5 gap-x-4 text-[10px] font-mono tracking-widest uppercase mb-2">
        <div>
          <p className="text-zinc-500 mb-1 text-[9px]">ENTRY</p>
          <p className="font-medium text-zinc-200">${trade.entry_price.toFixed(4)}</p>
        </div>
        {trade.exit_price && (
          <div>
            <p className="text-zinc-500 mb-1 text-[9px]">EXIT</p>
            <p className="font-medium text-zinc-200">${trade.exit_price.toFixed(4)}</p>
          </div>
        )}
        <div>
          <p className="text-zinc-500 mb-1 text-[9px]">QTY</p>
          <p className="font-medium text-zinc-200">{trade.quantity.toFixed(4)}</p>
        </div>

        {trade.stop_loss && (
          <div>
            <p className="text-zinc-500 mb-1 text-[9px] flex items-center gap-1">
              {trade.is_trailing_active ? 'TRAIL SL' : 'STOP LOSS'}
            </p>
            <p className="font-medium text-red-400">${trade.stop_loss.toFixed(4)}</p>
          </div>
        )}
        {trade.take_profit && (
          <div>
            <p className="text-zinc-500 mb-1 text-[9px]">TAKE PROFIT</p>
            <p className="font-medium text-emerald-400">${trade.take_profit.toFixed(4)}</p>
          </div>
        )}
        {trade.highest_price && trade.is_trailing_active && (
          <div>
            <p className="text-zinc-500 mb-1 text-[9px]">PEAK PRICE</p>
            <p className="font-medium text-amber-400">${trade.highest_price.toFixed(4)}</p>
          </div>
        )}
        {trade.pnl !== undefined && trade.pnl !== null && (
          <div>
            <p className="text-zinc-500 mb-1 text-[9px]">PNL</p>
            <p className={`font-bold text-[11px] ${pnlColor}`}>
              {trade.pnl >= 0 ? '+' : ''}${trade.pnl.toFixed(4)}
            </p>
          </div>
        )}
      </div>

      {/* ── ML INFO ── */}
      {trade.ml_direction && (
        <div className="flex items-center gap-2 mt-4 pt-4 border-t border-white/[0.05]">
          <Brain className="w-3.5 h-3.5 text-purple-400" />
          <span className="text-[9px] font-mono tracking-widest text-zinc-500">ML:</span>
          <span className={`text-[9px] font-mono tracking-widest font-bold bg-white/5 px-2 py-0.5 rounded ${trade.ml_direction === 'UP' ? 'text-emerald-400' : 'text-red-400'}`}>
            {trade.ml_direction}
          </span>
          {trade.ml_confidence && (
            <span className="text-[9px] font-mono tracking-widest text-zinc-500 ml-auto">
              {(trade.ml_confidence * 100).toFixed(0)}% CONF
            </span>
          )}
        </div>
      )}

      {/* ── FOOTER ── */}
      <div className="flex justify-between items-center text-[9px] font-mono tracking-widest uppercase text-zinc-500 mt-4 pt-4 border-t border-white/[0.05]">
        <span>{formatDistanceToNow(new Date(trade.entry_time), { addSuffix: true })}</span>
        {trade.reason && <span className="truncate ml-4 max-w-[120px] opacity-60 text-right">{trade.reason.split('|')[0]}</span>}
      </div>
    </div>
  );
}

export default function ActiveTrades({
  trades,
  onExecuteTrade,
  onSelectSymbol
}: {
  trades: Trade[];
  onExecuteTrade: (symbol: string, side: string, amount: number) => void;
  onSelectSymbol: (symbol: string) => void;
}) {
  const [exeSymbol, setExeSymbol] = useState('BTC');
  const [exeSide, setExeSide] = useState('BUY');
  const [exeAmount, setExeAmount] = useState('100');

  const openTrades = trades.filter(t => t.status === 'OPEN');
  const closedTrades = trades.filter(t => t.status === 'CLOSED');

  const handleManualTrade = (e: React.FormEvent) => {
    e.preventDefault();
    onExecuteTrade(exeSymbol.toUpperCase() + '/USDT', exeSide, Number(exeAmount));
  };

  const handleCloseTrade = async (id: number) => {
    try {
      await api.closeTrade(id);
    } catch (err) {
      console.error('Failed to close trade:', err);
    }
  };

  return (
    <div className="space-y-10">

      {/* ── MANUAL EXECUTION FORM ── */}
      <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-6 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500/0 via-emerald-500/20 to-cyan-500/0" />

        <h3 className="text-[11px] font-bold text-zinc-300 mb-5 uppercase tracking-widest flex items-center gap-2">
          <Crosshair className="w-4 h-4 text-emerald-400" /> Manual Trade Execution
        </h3>

        <form onSubmit={handleManualTrade} className="flex flex-wrap items-end gap-5 text-[10px] font-mono tracking-widest uppercase text-zinc-400">
          <div className="flex flex-col gap-2">
            <label className="text-zinc-500 ml-1">Coin Symbol</label>
            <input
              value={exeSymbol}
              onChange={e => setExeSymbol(e.target.value)}
              placeholder="BTC"
              required
              className="bg-[#09090b] border border-white/10 rounded-xl px-4 py-2.5 w-32 text-zinc-100 focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 outline-none transition-all duration-200 placeholder:text-zinc-700"
            />
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-zinc-500 ml-1">Side</label>
            <select
              value={exeSide}
              onChange={e => setExeSide(e.target.value)}
              className="bg-[#09090b] border border-white/10 rounded-xl px-4 py-2.5 w-32 text-zinc-100 focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 outline-none transition-all duration-200 cursor-pointer"
            >
              <option value="BUY">BUY</option>
              <option value="SELL">SELL</option>
            </select>
          </div>
          <div className="flex flex-col gap-2">
            <label className="text-zinc-500 ml-1">Amount (USD)</label>
            <input
              value={exeAmount}
              onChange={e => setExeAmount(e.target.value)}
              type="number"
              step="0.01"
              min="10"
              placeholder="100"
              required
              className="bg-[#09090b] border border-white/10 rounded-xl px-4 py-2.5 w-40 text-zinc-100 focus:border-emerald-500/50 focus:ring-1 focus:ring-emerald-500/20 outline-none transition-all duration-200 placeholder:text-zinc-700"
            />
          </div>
          <button
            type="submit"
            className="bg-emerald-500 hover:bg-emerald-400 text-black font-bold py-2.5 px-8 rounded-xl transition-all duration-300 shadow-[0_0_15px_rgba(16,185,129,0.2)] hover:shadow-[0_0_20px_rgba(16,185,129,0.4)] ml-auto sm:ml-0"
          >
            Execute
          </button>
        </form>
      </div>

      {/* ── OPEN POSITIONS ── */}
      <div>
        <div className="flex items-center gap-3 mb-5">
          <h3 className="text-[11px] font-bold text-zinc-400 uppercase tracking-widest">
            Open Positions
          </h3>
          <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full text-[10px] font-mono">
            {openTrades.length}
          </span>
          <div className="flex-1 h-px bg-white/[0.05] ml-4" />
        </div>

        {openTrades.length === 0 ? (
          <div className="border border-white/5 border-dashed rounded-2xl py-12 flex flex-col items-center justify-center bg-white/[0.01]">
            <Shield className="w-8 h-8 text-zinc-700 mb-3" />
            <p className="text-zinc-500 text-[11px] font-mono uppercase tracking-widest">No active positions</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {openTrades.map(t => <TradeCard key={t.id} trade={t} onClose={handleCloseTrade} />)}
          </div>
        )}
      </div>

      {/* ── TRADE HISTORY ── */}
      <div>
        <div className="flex items-center gap-3 mb-5">
          <h3 className="text-[11px] font-bold text-zinc-400 uppercase tracking-widest">
            Trade History
          </h3>
          <span className="bg-white/5 text-zinc-400 border border-white/10 px-2 py-0.5 rounded-full text-[10px] font-mono">
            {closedTrades.length}
          </span>
          <div className="flex-1 h-px bg-white/[0.05] ml-4" />
        </div>

        <div className="overflow-x-auto border border-white/5 rounded-2xl bg-[#121214]/60 shadow-xl custom-scrollbar">
          <table className="w-full text-left font-mono tracking-widest text-[10px] uppercase whitespace-nowrap">
            <thead>
              <tr className="text-zinc-500 border-b border-white/[0.05] bg-white/[0.02]">
                <th className="pb-4 pt-4 pl-6 pr-4 font-medium tracking-wider">Symbol</th>
                <th className="pb-4 pt-4 pr-4 font-medium tracking-wider">Side</th>
                <th className="pb-4 pt-4 pr-4 font-medium tracking-wider">Entry</th>
                <th className="pb-4 pt-4 pr-4 font-medium tracking-wider">Exit</th>
                <th className="pb-4 pt-4 pr-4 font-medium tracking-wider text-right">PNL</th>
                <th className="pb-4 pt-4 pr-4 font-medium tracking-wider text-center">ML</th>
                <th className="pb-4 pt-4 pr-6 font-medium tracking-wider text-right">When</th>
              </tr>
            </thead>
            <tbody>
              {closedTrades.map((t, idx) => (
                <tr key={t.id} className={`border-b border-white/[0.03] hover:bg-white/[0.03] transition-colors ${idx === closedTrades.length - 1 ? 'border-none' : ''}`}>
                  <td className="py-4 pl-6 pr-4 font-bold text-zinc-200 text-[11px] flex flex-col items-start gap-0.5">
                    <button
                      onClick={() => onSelectSymbol(t.symbol)}
                      className="font-bold text-white font-mono text-[11px] mb-0.5 hover:text-cyan-400 transition-colors text-left"
                    >
                      {t.symbol}
                    </button>
                  </td>
                  <td className="py-4 pr-4">
                    <span className={`px-2 py-0.5 border rounded-md font-bold text-[9px] ${t.side === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                      {t.side}
                    </span>
                  </td>
                  <td className="py-4 pr-4 text-zinc-300 text-[11px]">${t.entry_price.toFixed(4)}</td>
                  <td className="py-4 pr-4 text-zinc-300 text-[11px]">${t.exit_price?.toFixed(4) ?? '—'}</td>
                  <td className={`py-4 pr-4 text-right font-bold text-[11px] ${(t.pnl ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                    {(t.pnl ?? 0) >= 0 ? '+' : ''}${(t.pnl ?? 0).toFixed(4)}
                  </td>
                  <td className="py-4 pr-4 text-center text-[10px]">
                    {t.ml_direction ? (
                      <span className={`px-2 py-1 rounded bg-white/5 ${t.ml_direction === 'UP' ? 'text-emerald-400' : 'text-red-400'}`}>
                        {t.ml_direction} {t.ml_confidence ? `${(t.ml_confidence * 100).toFixed(0)}%` : ''}
                      </span>
                    ) : <span className="text-zinc-600">—</span>}
                  </td>
                  <td className="py-4 pr-6 text-zinc-500 text-[10px] text-right">{formatDistanceToNow(new Date(t.entry_time), { addSuffix: true })}</td>
                </tr>
              ))}
              {closedTrades.length === 0 && (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-zinc-600 text-[11px]">No trade history available</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}