import { Brain, TrendingUp, TrendingDown, Activity } from 'lucide-react';

function ConfidenceBar({ value, direction }: { value: number; direction: string }) {
  const isUp = direction === 'UP';
  const isDown = direction === 'DOWN';

  const trackColor = 'bg-[#09090b] border border-white/5';
  const fillColor = isUp
    ? 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]'
    : isDown
      ? 'bg-red-400 shadow-[0_0_10px_rgba(248,113,113,0.5)]'
      : 'bg-zinc-500';

  const pct = Math.round(value * 100);

  return (
    <div className="flex items-center gap-4">
      <div className={`flex-1 h-2 rounded-full overflow-hidden ${trackColor}`}>
        <div
          className={`h-full ${fillColor} rounded-full transition-all duration-1000 ease-out`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-[11px] font-mono font-bold text-zinc-200 w-8 text-right">{pct}%</span>
    </div>
  );
}

export default function PredictionsPanel({
  predictions,
  patterns,
  onSelectSymbol
}: {
  predictions: Record<string, any>;
  patterns: Record<string, any[]>;
  onSelectSymbol: (symbol: string) => void;
}) {
  const symbols = Object.keys(predictions);

  // ── EMPTY STATE ──
  if (symbols.length === 0) {
    return (
      <div className="border border-white/5 border-dashed rounded-2xl py-24 flex flex-col items-center justify-center bg-white/[0.01]">
        <div className="relative mb-5">
          <Brain className="w-10 h-10 text-purple-500/60 animate-pulse" />
          <div className="absolute inset-0 bg-purple-500/20 blur-xl rounded-full animate-pulse" />
        </div>
        <p className="text-zinc-400 font-mono tracking-widest text-[11px] uppercase font-bold">Awaiting ML Forecasts</p>
        <p className="text-zinc-600 text-[10px] mt-2 font-mono uppercase tracking-widest">Models are analyzing market data</p>
      </div>
    );
  }

  // ── PREDICTIONS GRID ──
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
      {symbols.map(sym => {
        const pred = predictions[sym];
        const pats = patterns[sym] || [];
        const isUp = pred.direction === 'UP';
        const isDown = pred.direction === 'DOWN';

        return (
          <div
            key={sym}
            className="bg-[#121214]/60 backdrop-blur-sm border border-white/5 rounded-2xl p-6 hover:border-white/10 hover:bg-[#121214]/80 transition-all duration-300 group shadow-xl relative overflow-hidden"
          >
            {/* Subtle Top Gradient Accent based on prediction direction */}
            <div className={`absolute top-0 left-0 w-full h-1 ${isUp ? 'bg-gradient-to-r from-emerald-500/0 via-emerald-500/30 to-emerald-500/0' : isDown ? 'bg-gradient-to-r from-red-500/0 via-red-500/30 to-red-500/0' : 'bg-transparent'}`} />

            {/* ── HEADER ── */}
            <div className="flex justify-between items-start mb-6 pb-4 border-b border-white/[0.05]">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 shadow-[0_0_15px_rgba(168,85,247,0.1)]">
                  <Brain className="w-4 h-4 text-purple-400" />
                </div>
                <h3 className="font-mono text-xl font-bold text-white tracking-widest flex items-center justify-between mb-2">
                  <button
                    onClick={() => onSelectSymbol(sym)}
                    className="hover:text-cyan-400 transition-colors"
                  >
                    {sym}
                  </button>
                </h3>
              </div>
              <div className={`flex items-center gap-1.5 text-[10px] font-bold tracking-widest uppercase border px-3 py-1.5 rounded-lg shadow-sm ${isUp
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                  : isDown
                    ? 'bg-red-500/10 border-red-500/20 text-red-400'
                    : 'bg-white/5 border-white/10 text-zinc-400'
                }`}>
                {isUp ? <TrendingUp className="w-3.5 h-3.5" /> : isDown ? <TrendingDown className="w-3.5 h-3.5" /> : null}
                {pred.direction}
              </div>
            </div>

            {/* ── CONFIDENCE BAR ── */}
            <div className="mb-6">
              <div className="flex justify-between text-[9px] font-mono tracking-widest uppercase text-zinc-500 mb-2.5">
                <span>Model Confidence</span>
                <span className="text-zinc-400">{pred.trained_on > 0 ? `TRAINED: ${pred.trained_on} SAMPLES` : 'HEURISTIC'}</span>
              </div>
              <ConfidenceBar value={pred.confidence} direction={pred.direction} />
            </div>

            {/* ── PROBABILITIES GRID ── */}
            <div className="grid grid-cols-3 gap-2 text-[10px] font-mono tracking-widest uppercase mb-2">
              <div className="text-center border-r border-white/5">
                <p className="text-zinc-600 mb-1.5">UP PROB</p>
                <p className="text-emerald-400 font-bold text-[11px] drop-shadow-[0_0_5px_rgba(52,211,153,0.3)]">
                  {((pred.up_prob ?? 0.5) * 100).toFixed(0)}%
                </p>
              </div>
              <div className="text-center border-r border-white/5">
                <p className="text-zinc-600 mb-1.5">DOWN PROB</p>
                <p className="text-red-400 font-bold text-[11px] drop-shadow-[0_0_5px_rgba(248,113,113,0.3)]">
                  {((pred.down_prob ?? 0.5) * 100).toFixed(0)}%
                </p>
              </div>
              <div className="text-center">
                <p className="text-zinc-600 mb-1.5">ALGO</p>
                <p className="text-purple-400 font-bold text-[11px]">
                  {pred.trained_on > 0 ? 'RF MODEL' : 'HEURISTIC'}
                </p>
              </div>
            </div>

            {/* ── DETECTED PATTERNS ── */}
            {pats.length > 0 && (
              <div className="border-t border-white/[0.05] pt-5 mt-5 space-y-2.5">
                <p className="text-[10px] font-mono tracking-widest uppercase text-zinc-500 mb-3 flex items-center gap-2">
                  <Activity className="w-3.5 h-3.5 text-cyan-400" /> Detected Patterns
                </p>
                {pats.map((p: any, i: number) => {
                  const isBullish = p.type === 'bullish';
                  return (
                    <div
                      key={i}
                      className={`flex justify-between items-center text-[10px] font-mono tracking-widest uppercase px-4 py-2.5 rounded-xl border ${isBullish
                          ? 'bg-emerald-500/[0.02] border-emerald-500/10'
                          : 'bg-red-500/[0.02] border-red-500/10'
                        }`}
                    >
                      <span className={isBullish ? 'text-emerald-400 font-bold' : 'text-red-400 font-bold'}>
                        {p.name}
                      </span>
                      <span className="text-zinc-400 font-bold bg-[#09090b] px-2 py-0.5 rounded-md border border-white/5">
                        {(p.confidence * 100).toFixed(0)}%
                      </span>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}