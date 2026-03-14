import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, Tooltip } from 'recharts';
import { Brain, TrendingUp, Target, Activity } from 'lucide-react';

function WinRateBar({ wins, losses }: { wins: number; losses: number }) {
  const total = wins + losses;
  const pct = total > 0 ? (wins / total) * 100 : 0;

  return (
    <div className="flex items-center gap-4">
      <div className="flex-1 h-1.5 bg-[#09090b] border border-white/5 rounded-full overflow-hidden flex">
        <div
          className="h-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.5)] transition-all duration-1000 ease-out"
          style={{ width: `${pct}%` }}
        />
        <div className="h-full bg-red-500/20 flex-1 transition-all duration-1000 ease-out" />
      </div>
      <span className="text-[11px] font-mono font-bold text-zinc-200 w-10 text-right">{pct.toFixed(0)}%</span>
    </div>
  );
}

const STRATEGY_LABELS: Record<string, string> = {
  ema_crossover: 'EMA Crossover',
  advanced_oscillators: 'Adv Oscillators',
  macd: 'MACD',
  bollinger: 'Bollinger Bands',
  volume_surge: 'Volume Surge',
  ml_prediction: 'ML Prediction',
};

// Custom tooltip for the Radar Chart
const CustomRadarTooltip = ({ active, payload }: any) => {
  if (active && payload && payload.length) {
    return (
      <div className="bg-[#09090b]/90 backdrop-blur-md border border-white/10 p-4 rounded-xl text-[10px] font-mono tracking-widest uppercase shadow-2xl">
        <p className="text-zinc-300 font-bold mb-3 border-b border-white/10 pb-2">{payload[0].payload.subject}</p>
        {payload.map((entry: any, index: number) => (
          <div key={index} className="flex items-center justify-between gap-4 mb-1.5 last:mb-0">
            <span style={{ color: entry.color }} className="opacity-80">{entry.name}</span>
            <span className="font-bold text-zinc-100">{entry.value.toFixed(1)}</span>
          </div>
        ))}
      </div>
    );
  }
  return null;
};

export default function StrategiesPanel({ 
  strategies, 
  activeStrategies = [], 
  onToggle 
}: { 
  strategies: Record<string, any>;
  activeStrategies?: string[];
  onToggle?: (key: string) => void;
}) {
  const radarData = Object.entries(strategies).map(([key, val]) => ({
    subject: STRATEGY_LABELS[key] ?? key,
    winRate: val.win_rate || 0,
    weight: (val.weight || 0) * 30, // Scaled for visual comparison against win rate (0-100 scale)
    signals: val.signals || 0,
    active: activeStrategies.includes(key)
  }));

  // Empty State Protection
  if (Object.keys(strategies).length === 0) {
    return (
      <div className="border border-white/5 border-dashed rounded-2xl py-24 flex flex-col items-center justify-center bg-white/[0.01]">
        <div className="relative mb-4">
          <Target className="w-8 h-8 text-rose-500/50 animate-pulse" />
          <div className="absolute inset-0 bg-rose-500/10 blur-xl rounded-full animate-pulse" />
        </div>
        <p className="text-zinc-500 font-mono tracking-widest text-[11px] uppercase">Awaiting Strategy Data</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">

      {/* ── TOP ROW: RADAR CHART & LEARNING NOTE ── */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

        {/* Radar Chart Card */}
        <div className="xl:col-span-2 bg-white/[0.02] border border-white/[0.05] rounded-2xl p-6 relative overflow-hidden group hover:border-white/10 transition-colors">
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-1/2 h-32 bg-purple-500/5 blur-[100px] rounded-full pointer-events-none" />

          <div className="flex items-center justify-between mb-2 pb-4 border-b border-white/[0.05]">
            <h3 className="text-[11px] font-bold text-zinc-300 uppercase tracking-widest flex items-center gap-2">
              <Activity className="w-4 h-4 text-purple-400" /> Strategy Radar Analysis
            </h3>
            <div className="flex gap-4 text-[9px] font-mono tracking-widest uppercase font-bold">
              <span className="text-purple-400 flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-purple-400 shadow-[0_0_5px_rgba(192,132,252,0.5)]" /> Win Rate</span>
              <span className="text-emerald-400 flex items-center gap-1.5"><div className="w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_5px_rgba(52,211,153,0.5)]" /> Weight</span>
            </div>
          </div>

          <div className="h-72 w-full mt-4">
            <ResponsiveContainer width="100%" height="100%">
              <RadarChart cx="50%" cy="50%" outerRadius="75%" data={radarData}>
                <PolarGrid stroke="rgba(255,255,255,0.05)" />
                <PolarAngleAxis
                  dataKey="subject"
                  tick={{ fill: '#a1a1aa', fontSize: 10, fontFamily: 'monospace' }}
                />
                <Radar
                  name="Win Rate %"
                  dataKey="winRate"
                  stroke="#c084fc"
                  strokeWidth={2}
                  fill="#c084fc"
                  fillOpacity={0.1}
                  activeDot={{ r: 4, fill: '#c084fc', stroke: '#121214', strokeWidth: 2 }}
                />
                <Radar
                  name="Relative Weight"
                  dataKey="weight"
                  stroke="#34d399"
                  strokeWidth={2}
                  fill="#34d399"
                  fillOpacity={0.1}
                  activeDot={{ r: 4, fill: '#34d399', stroke: '#121214', strokeWidth: 2 }}
                />
                <Tooltip content={<CustomRadarTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Self-Learning Module Note */}
        <div className="xl:col-span-1 border border-purple-500/20 bg-gradient-to-b from-purple-500/[0.05] to-transparent rounded-2xl p-6 relative overflow-hidden flex flex-col justify-center">
          <div className="absolute top-0 right-0 w-32 h-32 bg-purple-500/10 blur-[50px] rounded-full pointer-events-none" />

          <div className="flex items-center gap-3 mb-6">
            <div className="p-2 rounded-xl bg-purple-500/10 border border-purple-500/20 shadow-[0_0_15px_rgba(168,85,247,0.1)] relative">
              <Brain className="w-5 h-5 text-purple-400" />
              <div className="absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full bg-emerald-400 border-2 border-[#121214] animate-pulse" />
            </div>
            <div>
              <p className="font-bold text-purple-400 text-xs font-mono tracking-widest uppercase">Self-Learning</p>
              <p className="text-[10px] font-mono tracking-widest text-emerald-400 uppercase">System Active</p>
            </div>
          </div>

          <div className="space-y-4 font-mono tracking-widest text-[10px] uppercase text-zinc-400 leading-relaxed border-l-2 border-purple-500/30 pl-4">
            <p>
              After each trade closes, the bot analyzes which strategies agreed with the final trade direction.
            </p>
            <p className="text-zinc-300">
              <span className="text-emerald-400 font-bold">Winning Strategies</span> gain +0.05 weight.<br />
              <span className="text-red-400 font-bold">Losing Strategies</span> lose -0.015 weight.
            </p>
            <p>
              ML Models are retrained locally every 10 closed trades. Weights update in real-time below.
            </p>
          </div>
        </div>

      </div>

      {/* ── BOTTOM ROW: STRATEGY BREAKDOWN TABLE ── */}
      <div className="bg-white/[0.02] border border-white/[0.05] rounded-2xl p-6 hover:border-white/10 transition-colors">
        <div className="flex items-center gap-3 mb-6 pb-4 border-b border-white/[0.05]">
          <TrendingUp className="w-4 h-4 text-emerald-400" />
          <h3 className="text-[11px] uppercase font-bold tracking-widest text-zinc-300">Per-Strategy Breakdown</h3>
        </div>

        <div className="space-y-2">
          {/* Table Header Row */}
          <div className="grid grid-cols-[0.5fr_1.5fr_1fr_1fr_1fr_2fr] gap-4 px-4 pb-2 text-[9px] font-mono tracking-widest uppercase text-zinc-500">
            <div className="text-center">Status</div>
            <div>Strategy Engine</div>
            <div className="text-center">Wins</div>
            <div className="text-center">Losses</div>
            <div className="text-center">Weight Multiplier</div>
            <div>Win Rate Tracker</div>
          </div>

          {/* Table Data Rows */}
          {Object.entries(strategies).map(([key, val]) => {
            const isActive = activeStrategies.includes(key);
            
            return (
              <div
                key={key}
                className={`grid grid-cols-[0.5fr_1.5fr_1fr_1fr_1fr_2fr] items-center gap-4 text-[10px] font-mono tracking-widest uppercase p-4 bg-white/[0.01] hover:bg-white/[0.03] border rounded-xl transition-all duration-300 ${
                  isActive ? 'border-white/[0.05]' : 'border-red-500/10 opacity-60 grayscale'
                }`}
              >
                <div className="flex justify-center">
                  <button
                    onClick={() => onToggle?.(key)}
                    className={`w-6 h-6 rounded-md border flex items-center justify-center transition-all ${
                      isActive 
                        ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.1)]' 
                        : 'bg-white/5 border-white/10 text-zinc-600'
                    }`}
                  >
                    <div className={`w-2 h-2 rounded-full ${isActive ? 'bg-emerald-400 animate-pulse' : 'bg-transparent border border-white/20'}`} />
                  </button>
                </div>

                <div>
                  <p className="font-bold text-zinc-200 text-[11px] mb-1">{STRATEGY_LABELS[key] || key}</p>
                  <p className="text-zinc-600 text-[9px]">{val.signals} Lifetime Signals</p>
                </div>

                <div className="text-center flex flex-col items-center justify-center">
                  <span className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-md font-bold text-[11px]">
                    {val.wins}
                  </span>
                </div>

                <div className="text-center flex flex-col items-center justify-center">
                  <span className="bg-red-500/10 text-red-400 border border-red-500/20 px-3 py-1 rounded-md font-bold text-[11px]">
                    {val.losses}
                  </span>
                </div>

                <div className="text-center flex flex-col items-center justify-center">
                  <span className={`px-3 py-1 rounded-md font-bold text-[11px] border ${val.weight >= 1
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20 shadow-[0_0_8px_rgba(245,158,11,0.2)]'
                      : 'bg-white/5 text-zinc-400 border-white/10'
                    }`}>
                  {val.weight.toFixed(2)}×
                </span>
              </div>

              <div className="pl-4">
                <WinRateBar wins={val.wins} losses={val.losses} />
              </div>
            </div>
            );
          })}
        </div>
      </div>

    </div>
  );
}