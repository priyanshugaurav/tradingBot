import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis, ReferenceLine, Cell } from 'recharts';
import { TrendingUp, Award, Target, Zap, BarChart2, Shield } from 'lucide-react';

interface Perf {
  balance: number;
  total_pnl: number;
  total_trades: number;
  open_trades: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_win: number;
  avg_loss: number;
  profit_factor: number;
  equity_curve: Array<{ time: string; balance: number; pnl: number; symbol: string }>;
  ml_trained_on: number;
}

function KpiCard({ icon, label, value, sub, valueColor = 'text-zinc-200' }: any) {
  return (
    <div className="bg-white/[0.02] border border-white/[0.05] rounded-2xl p-5 hover:bg-white/[0.04] hover:border-white/10 transition-all duration-300 group">
      <div className="flex items-center gap-2 mb-4 text-zinc-500 group-hover:text-zinc-400 transition-colors">
        <div className="p-1.5 rounded-lg bg-white/5 border border-white/5">
          {icon}
        </div>
        <span className="text-[10px] uppercase font-mono tracking-widest">{label}</span>
      </div>
      <p className={`text-2xl font-mono font-bold tracking-tight ${valueColor}`}>{value}</p>
      {sub && <p className="text-[10px] font-mono uppercase tracking-widest text-zinc-600 mt-2">{sub}</p>}
    </div>
  );
}

const CustomTooltip = ({ active, payload }: any) => {
  if (active && payload?.length) {
    const d = payload[0].payload;
    return (
      <div className="bg-[#09090b]/90 backdrop-blur-md border border-white/10 p-4 rounded-xl text-[10px] font-mono tracking-widest uppercase shadow-2xl">
        <p className="text-zinc-400 mb-2">{d.symbol || 'PORTFOLIO'}</p>
        {d.balance !== undefined && (
          <p className="text-zinc-100 font-bold text-sm mb-1">${d.balance?.toFixed(2)}</p>
        )}
        {d.pnl !== undefined && (
          <p className={`font-bold ${d.pnl >= 0 ? 'text-emerald-400 drop-shadow-[0_0_5px_rgba(52,211,153,0.4)]' : 'text-red-400'}`}>
            {d.pnl >= 0 ? '+' : ''}${d.pnl?.toFixed(4)} PNL
          </p>
        )}
      </div>
    );
  }
  return null;
};

export default function PerformancePanel({ perf }: { perf: Perf | null }) {
  if (!perf) return (
    <div className="border border-white/5 border-dashed rounded-2xl py-24 flex flex-col items-center justify-center bg-white/[0.01]">
      <div className="relative mb-4">
        <BarChart2 className="w-8 h-8 text-cyan-500/50 animate-pulse" />
        <div className="absolute inset-0 bg-cyan-500/10 blur-xl rounded-full animate-pulse" />
      </div>
      <p className="text-zinc-500 font-mono tracking-widest text-[11px] uppercase">Awaiting Performance Metrics</p>
      <p className="text-zinc-600 text-[10px] mt-2">Data will populate after initial trades</p>
    </div>
  );

  return (
    <div className="space-y-6">

      {/* ── KPI METRICS GRID ── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <KpiCard
          icon={<TrendingUp className="w-4 h-4 text-emerald-400" />}
          label="Total PNL"
          value={`${perf.total_pnl >= 0 ? '+' : ''}$${perf.total_pnl.toFixed(2)}`}
          valueColor={perf.total_pnl >= 0 ? 'text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.3)]' : 'text-red-400'}
        />
        <KpiCard
          icon={<Target className="w-4 h-4 text-cyan-400" />}
          label="Win Rate"
          value={`${perf.win_rate}%`}
          sub={`${perf.wins}W / ${perf.losses}L`}
        />
        <KpiCard
          icon={<Award className="w-4 h-4 text-amber-400" />}
          label="Profit Factor"
          value={perf.profit_factor.toFixed(2)}
          valueColor={perf.profit_factor >= 1 ? 'text-emerald-400' : 'text-red-400'}
        />
        <KpiCard
          icon={<Zap className="w-4 h-4 text-emerald-400" />}
          label="Avg Win"
          value={`$${perf.avg_win.toFixed(2)}`}
          valueColor="text-emerald-400"
        />
        <KpiCard
          icon={<Zap className="w-4 h-4 text-red-400" />}
          label="Avg Loss"
          value={`$${perf.avg_loss.toFixed(2)}`}
          valueColor="text-red-400"
        />
        <KpiCard
          icon={<BarChart2 className="w-4 h-4 text-purple-400" />}
          label="Total Trades"
          value={perf.total_trades}
          sub={`${perf.open_trades} CURRENTLY OPEN`}
        />
        <KpiCard
          icon={<TrendingUp className="w-4 h-4 text-blue-400" />}
          label="Balance"
          value={`$${perf.balance.toFixed(2)}`}
        />
        <KpiCard
          icon={<Shield className="w-4 h-4 text-rose-400" />}
          label="ML Samples"
          value={perf.ml_trained_on}
          sub="DATA POINTS LEARNED"
        />
      </div>

      {/* ── EQUITY CURVE ── */}
      <div className="bg-white/[0.02] border border-white/[0.05] rounded-2xl p-6 relative overflow-hidden group hover:border-white/10 transition-colors">
        {/* Subtle background glow */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-24 bg-emerald-500/5 blur-[80px] rounded-full pointer-events-none" />

        <h3 className="text-[11px] font-bold text-zinc-300 mb-8 uppercase tracking-widest flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-emerald-400" /> Equity Curve
        </h3>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={perf.equity_curve}>
              <defs>
                <linearGradient id="equityGlow" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#34d399" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#34d399" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis dataKey="time" hide />
              <YAxis
                stroke="#71717a"
                tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'monospace' }}
                tickFormatter={v => `$${v}`}
                tickLine={false}
                axisLine={false}
                width={60}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ stroke: 'rgba(255,255,255,0.1)', strokeWidth: 1, strokeDasharray: '4 4' }} />
              <Area
                dataKey="balance"
                stroke="#34d399"
                fill="url(#equityGlow)"
                strokeWidth={2}
                dot={false}
                type="stepAfter"
                activeDot={{ r: 4, fill: '#34d399', stroke: '#121214', strokeWidth: 2 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* ── PNL PER TRADE BAR CHART ── */}
      <div className="bg-white/[0.02] border border-white/[0.05] rounded-2xl p-6 hover:border-white/10 transition-colors">
        <h3 className="text-[11px] font-bold text-zinc-300 mb-8 uppercase tracking-widest flex items-center gap-2">
          <BarChart2 className="w-4 h-4 text-cyan-400" /> PNL Per Execution
        </h3>

        <div className="h-52 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={perf.equity_curve}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
              <XAxis
                dataKey="symbol"
                tick={{ fill: '#71717a', fontSize: 9, fontFamily: 'monospace' }}
                tickLine={false}
                axisLine={false}
                height={20}
              />
              <YAxis
                stroke="#71717a"
                tick={{ fill: '#71717a', fontSize: 10, fontFamily: 'monospace' }}
                tickFormatter={v => `$${v}`}
                tickLine={false}
                axisLine={false}
                width={60}
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255,255,255,0.02)' }} />
              <ReferenceLine y={0} stroke="rgba(255,255,255,0.1)" strokeWidth={1} />

              <Bar
                dataKey="pnl"
                radius={[4, 4, 4, 4]}
                isAnimationActive={false}
                maxBarSize={40}
              >
                {perf.equity_curve.map((entry, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={entry.pnl >= 0 ? '#34d399' : '#f87171'}
                    fillOpacity={0.8}
                  />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

    </div>
  );
}