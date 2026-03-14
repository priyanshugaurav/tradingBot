import type { BotEvent, EventSeverity } from '../api';
import { Activity, AlertTriangle, CheckCircle, Info, Zap, TrendingUp, Brain, Radio, Shield } from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';

// Refined palette matching the new premium dark mode aesthetic
const severityConfig: Record<EventSeverity, { bg: string; text: string; border: string; glow: string }> = {
  INFO: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/20', glow: 'bg-cyan-400 shadow-[0_0_10px_rgba(34,211,238,0.5)]' },
  SUCCESS: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/20', glow: 'bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,0.5)]' },
  WARNING: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/20', glow: 'bg-amber-400 shadow-[0_0_10px_rgba(245,158,11,0.5)]' },
  DANGER: { bg: 'bg-red-500/10', text: 'text-red-400', border: 'border-red-500/20', glow: 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]' },
};

const eventTypeIcon: Record<string, any> = {
  SYSTEM: Activity,
  SCANNER: Radio,
  SIGNAL: Zap,
  PATTERN: TrendingUp,
  PREDICTION: Brain,
  TRADE: CheckCircle,
  RISK: Shield,
  LEARNING: Brain,
  ERROR: AlertTriangle,
};

export default function LiveLog({ 
  events,
  onSelectSymbol
}: { 
  events: BotEvent[];
  onSelectSymbol: (symbol: string) => void;
}) {
  return (
    // Replaced standard scrollbar with a custom scrollbar class (ensure you add scrollbar hiding/styling in your global CSS)
    <div className="flex flex-col gap-2.5 h-full max-h-[calc(100vh-220px)] overflow-y-auto pr-2 custom-scrollbar font-mono">

      {/* ── EMPTY STATE ── */}
      {events.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 border border-white/5 border-dashed rounded-xl bg-white/[0.01] h-full">
          <div className="relative mb-4">
            <Radio className="w-8 h-8 text-zinc-600 animate-pulse" />
            <div className="absolute inset-0 bg-zinc-500/20 blur-xl rounded-full animate-pulse" />
          </div>
          <p className="text-xs uppercase tracking-widest text-zinc-500 mb-1">Awaiting Telemetry</p>
          <p className="text-[10px] text-zinc-600">Start the bot to initialize data stream</p>
        </div>
      )}

      {/* ── EVENT LIST ── */}
      {events.map((ev, i) => {
        const cfg = severityConfig[ev.severity] || severityConfig.INFO;
        const Icon = eventTypeIcon[ev.event_type] || Info;
        const age = formatDistanceToNow(new Date(ev.timestamp), { addSuffix: true });

        return (
          <div
            key={ev.id ?? i}
            className="relative flex gap-3.5 p-3.5 rounded-xl border border-white/[0.03] bg-white/[0.01] hover:bg-white/[0.03] transition-all duration-300 animate-fade-in group"
          >
            {/* Edge Accent Indicator */}
            <div className={`absolute left-0 top-3 bottom-3 w-[2px] rounded-r-full opacity-50 transition-opacity group-hover:opacity-100 ${cfg.glow}`} />

            {/* Icon Container */}
            <div className={`flex items-center justify-center w-8 h-8 rounded-lg flex-shrink-0 ${cfg.bg} border ${cfg.border}`}>
              <Icon className={`w-4 h-4 ${cfg.text}`} />
            </div>

            {/* Event Data */}
            <div className="flex-1 min-w-0 flex flex-col justify-center">
              <div className="flex items-start justify-between gap-3 mb-1">
                <span className="text-[11px] font-semibold text-zinc-200 truncate uppercase tracking-wide leading-tight">
                  {ev.title}
                </span>

                {/* Right side metadata pill cluster */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  {ev.symbol && (
                    <button 
                      onClick={() => onSelectSymbol(ev.symbol!)}
                      className="text-[9px] px-2 py-0.5 rounded-md bg-[#09090b] border border-white/10 text-zinc-300 tracking-widest font-bold hover:text-white transition-colors"
                    >
                      {ev.symbol}
                    </button>
                  )}
                  <span className={`text-[9px] px-2 py-0.5 rounded-md font-bold tracking-widest uppercase border ${cfg.bg} ${cfg.text} ${cfg.border}`}>
                    {ev.event_type}
                  </span>
                </div>
              </div>

              <div className="flex items-end justify-between gap-4 mt-0.5">
                <p className="text-[10px] text-zinc-500 truncate group-hover:text-zinc-400 transition-colors">
                  {ev.detail || "System nominal"}
                </p>
                <span className="text-[9px] text-zinc-600 flex-shrink-0 tracking-widest">
                  {age}
                </span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}