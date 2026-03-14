import type { ScanResult } from '../api';
import { TrendingUp, TrendingDown, Minus, RefreshCw, Radar } from 'lucide-react';

function TrendBadge({ trend }: { trend: string }) {
  if (trend === 'BULLISH') return (
    <span className="flex items-center w-fit gap-1.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-1 rounded-md font-bold tracking-widest text-[9px] uppercase">
      <TrendingUp className="w-3 h-3" /> BULL
    </span>
  );
  if (trend === 'BEARISH') return (
    <span className="flex items-center w-fit gap-1.5 bg-red-500/10 text-red-400 border border-red-500/20 px-2 py-1 rounded-md font-bold tracking-widest text-[9px] uppercase">
      <TrendingDown className="w-3 h-3" /> BEAR
    </span>
  );
  return (
    <span className="flex items-center w-fit gap-1.5 bg-white/5 text-zinc-400 border border-white/10 px-2 py-1 rounded-md font-bold tracking-widest text-[9px] uppercase">
      <Minus className="w-3 h-3" /> NEUT
    </span>
  );
}

function ScoreBar({ score }: { score: number }) {
  const color = score >= 70
    ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]'
    : score <= 30
      ? 'bg-red-400 shadow-[0_0_10px_rgba(248,113,113,0.5)]'
      : 'bg-amber-400 shadow-[0_0_10px_rgba(245,158,11,0.5)]';

  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 h-1.5 bg-[#09090b] border border-white/5 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-1000 ease-out`} style={{ width: `${Math.max(0, Math.min(100, score))}%` }} />
      </div>
      <span className="text-[11px] font-mono font-bold text-zinc-200 w-8 text-right">{score.toFixed(0)}</span>
    </div>
  );
}

export default function ScannerPanel({
  results, lastScan, onScan, scanning, onSelectSymbol
}: {
  results: ScanResult[]; lastScan: string | null; onScan: () => void; scanning: boolean; onSelectSymbol: (symbol: string) => void;
}) {
  return (
    <div className="space-y-6">

      {/* ── HEADER & CONTROLS ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-white/[0.02] border border-white/[0.05] rounded-2xl p-5">
        <div className="flex items-center gap-4">
          <div className="flex flex-col gap-1 text-[10px] font-mono tracking-widest uppercase">
            <span className="text-zinc-500">Pairs Analyzed</span>
            <span className="text-zinc-200 font-bold text-sm">{results.length}</span>
          </div>
          <div className="w-px h-8 bg-white/10" />
          <div className="flex flex-col gap-1 text-[10px] font-mono tracking-widest uppercase">
            <span className="text-zinc-500">Last Scan</span>
            <span className="text-zinc-300">
              {lastScan ? new Date(lastScan).toLocaleTimeString() : 'AWAITING INIT'}
            </span>
          </div>
        </div>

        <button
          onClick={onScan}
          disabled={scanning}
          className={`flex items-center gap-2 px-6 py-2.5 rounded-xl font-bold tracking-widest text-[10px] uppercase transition-all duration-300 shadow-lg border ${scanning
              ? 'bg-zinc-800 text-zinc-400 border-zinc-700 cursor-not-allowed opacity-80'
              : 'bg-emerald-500 hover:bg-emerald-400 text-black border-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.2)] hover:shadow-[0_0_20px_rgba(16,185,129,0.4)]'
            }`}
        >
          <RefreshCw className={`w-4 h-4 ${scanning ? 'animate-spin' : ''}`} />
          {scanning ? 'Scanning Market...' : 'Force Scan Now'}
        </button>
      </div>

      {/* ── SCAN RESULTS TABLE ── */}
      <div className="overflow-x-auto border border-white/5 rounded-2xl bg-[#121214]/60 shadow-xl custom-scrollbar">
        <table className="w-full text-left font-mono tracking-widest text-[10px] uppercase whitespace-nowrap">
          <thead>
            <tr className="text-zinc-500 border-b border-white/[0.05] bg-white/[0.02]">
              <th className="pb-4 pt-4 pl-6 pr-4 font-medium tracking-wider">#</th>
              <th className="pb-4 pt-4 pr-4 font-medium tracking-wider">Symbol</th>
              <th className="pb-4 pt-4 pr-4 font-medium tracking-wider">Trend</th>
              <th className="pb-4 pt-4 pr-6 font-medium tracking-wider">Score</th>
              <th className="pb-4 pt-4 pr-4 font-medium tracking-wider text-right">Price</th>
              <th className="pb-4 pt-4 pr-4 font-medium tracking-wider text-right">1h %</th>
              <th className="pb-4 pt-4 pr-4 font-medium tracking-wider text-right">24h %</th>
              <th className="pb-4 pt-4 pr-4 font-medium tracking-wider text-right">RSI</th>
              <th className="pb-4 pt-4 pr-4 font-medium tracking-wider text-right">MFI</th>
              <th className="pb-4 pt-4 pr-4 font-medium tracking-wider text-right">Stoch</th>
              <th className="pb-4 pt-4 pr-4 font-medium tracking-wider text-right">W%R</th>
              <th className="pb-4 pt-4 pr-4 font-medium tracking-wider text-right">ADX</th>
              <th className="pb-4 pt-4 pr-6 font-medium tracking-wider text-right">Vol×</th>
            </tr>
          </thead>
          <tbody>
            {results.slice(0, 60).map((r, i) => (
              <tr
                key={r.symbol}
                className={`border-b border-white/[0.03] transition-colors ${i < 5 ? 'bg-emerald-500/[0.02] hover:bg-emerald-500/[0.04]' : 'hover:bg-white/[0.03]'
                  } ${i === results.length - 1 ? 'border-none' : ''}`}
              >
                <td className="py-4 pl-6 pr-4 text-zinc-600 text-[10px]">{i + 1}</td>
                <td className="py-4 pr-4">
                  <button
                    onClick={() => onSelectSymbol(r.symbol)}
                    className="font-bold text-zinc-100 text-[11px] hover:text-cyan-400 transition-colors"
                    title="View Chart"
                  >
                    {r.symbol.replace('/USDT', '')}
                  </button>
                  <span className="text-zinc-600 text-[9px] ml-0.5">/USDT</span>
                </td>
                <td className="py-4 pr-4"><TrendBadge trend={r.trend} /></td>
                <td className="py-4 pr-6 w-36"><ScoreBar score={r.score} /></td>
                <td className="py-4 pr-4 text-right text-zinc-300 text-[11px] font-medium">
                  ${r.price < 1 ? r.price.toFixed(6) : r.price.toFixed(2)}
                </td>
                <td className={`py-4 pr-4 text-right text-[11px] font-bold ${r.change_1h >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {r.change_1h >= 0 ? '+' : ''}{r.change_1h.toFixed(2)}%
                </td>
                <td className={`py-4 pr-4 text-right text-[11px] font-bold ${r.change_24h >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {r.change_24h >= 0 ? '+' : ''}{r.change_24h.toFixed(2)}%
                </td>
                <td className={`py-4 pr-4 text-right text-[11px] ${r.rsi < 30 ? 'text-emerald-400 font-bold' : r.rsi > 70 ? 'text-red-400 font-bold' : 'text-zinc-500'}`}>
                  {r.rsi.toFixed(1)}
                </td>
                <td className={`py-4 pr-4 text-right text-[11px] ${r.mfi < 20 ? 'text-emerald-400 font-bold' : r.mfi > 80 ? 'text-red-400 font-bold' : 'text-zinc-500'}`}>
                  {r.mfi.toFixed(1)}
                </td>
                <td className={`py-4 pr-4 text-right text-[11px] ${r.stochrsi < 20 ? 'text-emerald-400 font-bold' : r.stochrsi > 80 ? 'text-red-400 font-bold' : 'text-zinc-500'}`}>
                  {r.stochrsi.toFixed(1)}
                </td>
                <td className={`py-4 pr-4 text-right text-[11px] ${r.willr < -80 ? 'text-emerald-400 font-bold' : r.willr > -20 ? 'text-red-400 font-bold' : 'text-zinc-500'}`}>
                  {r.willr.toFixed(1)}
                </td>
                <td className="py-4 pr-4 text-right text-[11px] text-zinc-500">{r.adx.toFixed(1)}</td>
                <td className={`py-4 text-right text-[11px] pr-6 ${r.volume_ratio > 2 ? 'text-amber-400 font-bold drop-shadow-[0_0_5px_rgba(245,158,11,0.5)]' : 'text-zinc-500'}`}>
                  {r.volume_ratio.toFixed(1)}×
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {/* ── EMPTY STATE ── */}
        {results.length === 0 && !scanning && (
          <div className="flex flex-col items-center justify-center py-20 bg-white/[0.01]">
            <div className="relative mb-5">
              <Radar className="w-10 h-10 text-emerald-500/60 animate-[spin_3s_linear_infinite]" />
              <div className="absolute inset-0 bg-emerald-500/10 blur-xl rounded-full animate-pulse" />
            </div>
            <p className="text-zinc-400 font-mono tracking-widest text-[11px] uppercase font-bold">No Scan Data Active</p>
            <p className="text-zinc-600 text-[10px] mt-2 font-mono uppercase tracking-widest">Initialize system or run manual scan</p>
          </div>
        )}
      </div>
    </div>
  );
}