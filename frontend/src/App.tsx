import { useEffect, useRef, useState, useCallback } from 'react';
import { api, WS_URL } from './api';
import type { BotEvent, Trade, ScanResult, BinanceAccount, BotConfig } from './api';
import LiveLog from './components/LiveLog';
import ScannerPanel from './components/ScannerPanel';
import ActiveTrades from './components/ActiveTrades';
import PredictionsPanel from './components/PredictionsPanel';
import PerformancePanel from './components/PerformancePanel';
import StrategiesPanel from './components/StrategiesPanel';
import {
  Activity, Brain, BarChart2, Target, Radio, TrendingUp,
  Zap, Sun, Moon, Wallet, Settings, Menu, X, Trash2
} from 'lucide-react';
import { useTheme } from './components/ThemeProvider';
import StockDetailModal from './components/StockDetailModal';

type TabId = 'log' | 'scanner' | 'trades' | 'predictions' | 'performance' | 'strategies';

const TABS: { id: TabId; label: string; icon: any }[] = [
  { id: 'log', label: 'Mission Control', icon: Radio },
  { id: 'scanner', label: 'Market Scanner', icon: Zap },
  { id: 'trades', label: 'Trades', icon: TrendingUp },
  { id: 'predictions', label: 'AI Predictions', icon: Brain },
  { id: 'performance', label: 'Performance', icon: BarChart2 },
  { id: 'strategies', label: 'Strategies', icon: Target },
];

export default function App() {
  const [tab, setTab] = useState<TabId>('log');
  const [events, setEvents] = useState<BotEvent[]>([]);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [scanResults, setScanResults] = useState<ScanResult[]>([]);
  const [lastScan, setLastScan] = useState<string | null>(null);
  const [predictions, setPredictions] = useState<Record<string, any>>({});
  const [patterns, setPatterns] = useState<Record<string, any[]>>({});
  const [strategies, setStrategies] = useState<Record<string, any>>({});
  const [performance, setPerformance] = useState<any>(null);
  const [botConfig, setBotConfig] = useState<BotConfig | null>(null);
  const [binanceAccount, setBinanceAccount] = useState<BinanceAccount | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const { theme, setTheme } = useTheme();

  // ── WebSocket for live events ─────────────────────────────────────────────
  const connectWS = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => {
      setWsConnected(false);
      setTimeout(connectWS, 3000);
    };
    ws.onerror = () => { ws.close(); };
    ws.onmessage = (msg) => {
      try {
        const event: BotEvent = JSON.parse(msg.data);
        setEvents(prev => {
          const next = [event, ...prev];
          return next.slice(0, 500);
        });
      } catch { }
    };
  }, []);

  useEffect(() => {
    connectWS();
    return () => wsRef.current?.close();
  }, [connectWS]);

  // ── REST polling ──────────────────────────────────────────────────────────
  const fetchBinance = useCallback(async () => {
    try {
      const r = await api.getBinanceAccount();
      setBinanceAccount(r.data);
    } catch { }
  }, []);

  const fetchAll = useCallback(async () => {
    try {
      const [tradesR, cfgR, perfR, stratR, predsR, patsR] = await Promise.allSettled([
        api.getTrades(),
        api.getBotConfig(),
        api.getPerformance(),
        api.getStrategies(),
        api.getPredictions(),
        api.getPatterns(),
      ]);
      if (tradesR.status === 'fulfilled') setTrades(tradesR.value.data);
      if (cfgR.status === 'fulfilled') setBotConfig(cfgR.value.data);
      if (perfR.status === 'fulfilled') setPerformance(perfR.value.data);
      if (stratR.status === 'fulfilled') setStrategies(stratR.value.data);
      if (predsR.status === 'fulfilled') setPredictions(predsR.value.data);
      if (patsR.status === 'fulfilled') setPatterns(patsR.value.data);
      
      if (cfgR.status === 'fulfilled' && cfgR.value.data.mode === 'BINANCE_TESTNET') {
        fetchBinance();
      }
    } catch { }
  }, [fetchBinance]);

  const fetchScanner = useCallback(async () => {
    try {
      const r = await api.getScanner();
      setScanResults(r.data.results || []);
      setLastScan(r.data.last_scan);
    } catch { }
  }, []);

  useEffect(() => {
    fetchAll();
    fetchScanner();
    const fast = setInterval(fetchAll, 5000);
    const slow = setInterval(fetchScanner, 30000);
    return () => { clearInterval(fast); clearInterval(slow); };
  }, [fetchAll, fetchScanner]);

  // ── Actions ────────────────────────────────────────────────────────────
  const toggleBot = async () => {
    await api.toggleBot();
    fetchAll();
  };

  const triggerScan = async () => {
    setScanning(true);
    await api.triggerScan();
    setTimeout(() => { fetchScanner(); setScanning(false); }, 8000);
  };

  const handleFund = async () => {
    const amt = prompt('Enter amount of simulated USD to add:', '10000');
    if (!amt || isNaN(Number(amt))) return;
    try {
      await api.fundPortfolio(Number(amt));
      fetchAll();
    } catch { }
  };

  const updateConfig = async (data: Partial<BotConfig>) => {
    try {
      await api.updateConfig(data);
      fetchAll();
    } catch { }
  };

  const updateTimeframe = async (tf: string) => {
    await updateConfig({ timeframe: tf });
  };

  const toggleStrategy = async (key: string) => {
    const current = botConfig?.active_strategies || [];
    const next = current.includes(key) 
      ? current.filter((s: string) => s !== key)
      : [...current, key];
    
    try {
      await api.updateConfig({ active_strategies: next });
      fetchAll();
    } catch { }
  };

  const handleReset = async () => {
    if (!window.confirm("CRITICAL ACTION: This will permanently delete ALL trade history, logs, and reset your paper wallet to $10,000. Proceed?")) return;
    try {
      await api.resetDatabase();
      window.location.reload();
    } catch (err: any) {
      alert("Reset failed: " + (err.response?.data?.detail || err.message));
    }
  };

  // ── Derived stats ─────────────────────────────────────────────────────────
  const isRunning = botConfig?.trading_enabled ?? false;
  const totalPnl = performance?.total_pnl ?? 0;
  const balance = performance?.balance ?? 10000;
  const winRate = performance?.win_rate ?? 0;
  const openCount = trades.filter(t => t.status === 'OPEN').length;

  return (
    <div className="flex h-screen w-full bg-[#09090b] text-zinc-200 selection:bg-emerald-500/30 font-sans">

      {/* ── SIDEBAR NAVIGATION ─────────────────────────────────────────────── */}
      <aside className={`fixed inset-y-0 left-0 z-50 w-64 bg-[#121214] border-r border-white/5 flex flex-col transition-transform duration-300 md:relative md:translate-x-0 ${mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'}`}>

        {/* Logo Section */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-white/5 bg-[#09090b]/50 shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 flex items-center justify-center border border-emerald-500/20 shadow-[0_0_10px_rgba(16,185,129,0.1)]">
              <Activity className="w-4 h-4 text-emerald-400" />
            </div>
            <h1 className="text-lg font-bold tracking-tight text-white flex items-center gap-2">
            TradeBot
            </h1>
          </div>
          <button className="md:hidden text-zinc-400" onClick={() => setMobileMenuOpen(false)}>
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Navigation Links */}
        <div className="flex-1 overflow-y-auto py-6 px-4 space-y-1 custom-scrollbar">
          <div className="text-xs font-mono font-bold text-zinc-500 mb-4 px-2 tracking-widest uppercase">
            Menu
          </div>
          {TABS.map(t => {
            const Icon = t.icon;
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => { setTab(t.id); setMobileMenuOpen(false); }}
                className={`w-full flex items-center gap-3 px-3 py-3 rounded-xl text-[13px] font-medium transition-all duration-200 ${active
                    ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 shadow-sm'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-white/5 border border-transparent'
                  }`}
              >
                <Icon className={`w-4 h-4 ${active ? 'text-emerald-400' : 'text-zinc-500'}`} />
                {t.label}

                {/* Badges */}
                <div className="ml-auto flex gap-1">
                  {t.id === 'log' && events.length > 0 && (
                    <span className={`px-2 py-0.5 rounded-md text-[10px] font-mono font-bold ${active ? 'bg-emerald-500/20 text-emerald-400' : 'bg-white/10 text-zinc-400'}`}>
                      {events.length > 99 ? '99+' : events.length}
                    </span>
                  )}
                  {t.id === 'trades' && openCount > 0 && (
                    <span className="bg-amber-500/10 text-amber-400 px-2 py-0.5 rounded-md text-[10px] font-mono font-bold border border-amber-500/20">
                      {openCount}
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>

        {/* Sidebar Footer */}
        <div className="p-4 border-t border-white/5 shrink-0 bg-[#09090b]/20">
          <div className="flex items-center justify-center gap-2 text-xs font-mono text-zinc-500 bg-[#09090b] p-3 rounded-xl border border-white/5">
            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)]' : 'bg-red-500'}`} />
            {wsConnected ? 'SYSTEM ONLINE' : 'DISCONNECTED'}
          </div>
        </div>
      </aside>

      {/* ── MAIN CONTENT AREA ────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 bg-gradient-to-br from-[#09090b] to-[#121214] overflow-y-auto relative custom-scrollbar">

        {/* TOP HEADER */}
        <header className="sticky top-0 z-40 h-16 bg-[#09090b]/80 backdrop-blur-xl border-b border-white/5 flex items-center justify-between px-4 sm:px-6 shrink-0 shadow-sm">

          <div className="flex items-center gap-4">
            <button className="md:hidden text-zinc-400 hover:text-white" onClick={() => setMobileMenuOpen(true)}>
              <Menu className="w-5 h-5" />
            </button>
          </div>

          {/* Stats & Mode */}
          <div className="hidden lg:flex items-center gap-4 text-sm bg-white/[0.02] border border-white/5 rounded-full px-5 py-1.5">
            {/* Mode Switcher */}
            <div className="flex bg-[#09090b] p-1 rounded-xl border border-white/10 shadow-inner">
              <button
                onClick={() => updateConfig({ mode: 'PAPER' })}
                className={`px-4 py-1.5 rounded-lg text-[10px] font-bold tracking-widest transition-all duration-300 ${botConfig?.mode === 'PAPER' ? 'bg-emerald-500 text-zinc-950 shadow-lg shadow-emerald-500/20' : 'text-zinc-500 hover:text-zinc-300'}`}
              >
                PAPER
              </button>
              <button
                onClick={() => updateConfig({ mode: 'BINANCE_TESTNET' })}
                className={`px-3 py-1 rounded-md text-[10px] font-bold tracking-widest transition-all ${botConfig?.mode === 'BINANCE_TESTNET' ? 'bg-amber-500 text-black shadow-lg shadow-amber-500/20' : 'text-zinc-500 hover:text-zinc-300'}`}
              >
                BINANCE
              </button>
            </div>

            <div className="w-px h-4 bg-white/10" />

            <div className="flex items-center gap-2">
              <Wallet className={`w-4 h-4 ${botConfig?.mode === 'BINANCE_TESTNET' ? 'text-amber-400' : 'text-zinc-500'}`} />
              {botConfig?.mode === 'BINANCE_TESTNET' ? (
                <>
                  <span className="font-mono text-zinc-400">Net: <span className="text-amber-400 font-bold">${binanceAccount?.balance?.toFixed(2) || '0.00'}</span></span>
                  {binanceAccount?.error && (
                    <span className="text-[8px] text-red-500 ml-1 truncate max-w-[100px]" title={binanceAccount.error}>ERR: {binanceAccount.error}</span>
                  )}
                </>
              ) : (
                <span className="font-mono text-zinc-400">Bal: <span className="text-zinc-100 font-bold">${balance.toFixed(2)}</span></span>
              )}
              {botConfig?.mode === 'PAPER' && (
                <button onClick={handleFund} className="ml-2 text-[9px] font-bold tracking-widest bg-white/5 hover:bg-white/10 border border-white/10 text-zinc-300 px-2 py-1 rounded-md transition-all">
                  ADD
                </button>
              )}
            </div>
            
            <div className="w-px h-4 bg-white/10" />
            
            <div className="flex items-center gap-2">
              <span className="font-mono text-zinc-400">PNL:</span>
              <span className={`font-bold font-mono ${totalPnl >= 0 ? 'text-emerald-400 drop-shadow-[0_0_8px_rgba(52,211,153,0.3)]' : 'text-red-400'}`}>
                {totalPnl >= 0 ? '+' : ''}${totalPnl.toFixed(2)}
              </span>
            </div>

            <div className="w-px h-4 bg-white/10" />

            <div className="flex items-center gap-2">
              <span className="font-mono text-zinc-400">Win Rate: <span className="text-zinc-100 font-bold">{winRate}%</span></span>
            </div>
          </div>

          {/* Controls */}
          <div className="flex items-center gap-3 sm:gap-5 ml-auto">
            <button
              onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
              className="p-2 rounded-xl text-zinc-400 hover:text-white hover:bg-white/5 transition-all"
              title="Toggle Theme"
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            <button
              onClick={toggleBot}
              className={`flex items-center justify-center px-4 sm:px-6 py-2 text-[10px] sm:text-xs font-bold tracking-widest uppercase rounded-xl transition-all shadow-lg ${isRunning
                  ? 'bg-red-500/10 text-red-400 border border-red-500/30 hover:bg-red-500/20'
                  : 'bg-emerald-500 text-black hover:bg-emerald-400 border border-emerald-400 shadow-[0_0_15px_rgba(16,185,129,0.2)]'
                }`}
            >
              {isRunning ? 'STOP BOT' : 'START BOT'}
            </button>
          </div>
        </header>

        {/* BOT STATUS RIBBON */}
        {isRunning && (
          <div className="flex-shrink-0 bg-emerald-500/[0.03] border-b border-emerald-500/10 px-6 py-2.5 flex items-center gap-4 text-[10px] uppercase font-mono tracking-widest text-emerald-400">
            <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(52,211,153,0.8)] shrink-0" />
            <span className="shrink-0">Scanning <span className="font-bold text-emerald-300">{scanResults.length}</span> pairs</span>
            <span className="text-emerald-500/30 shrink-0">•</span>
            <span className="shrink-0"><span className="font-bold text-emerald-300">{botConfig?.timeframe}</span> TF</span>
            <span className="ml-auto opacity-50 truncate max-w-[200px] sm:max-w-md md:max-w-xl">
              {botConfig?.symbols?.join('  /  ')}
            </span>
          </div>
        )}

        {/* ── ACTUAL TAB CONTENT ── */}
        <div className="p-4 sm:p-6 lg:p-8 max-w-[1600px] mx-auto w-full">

          {tab === 'log' && (
            <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">

              {/* Console */}
              <div className="xl:col-span-2 bg-[#121214]/80 backdrop-blur-sm border border-white/5 rounded-2xl p-6 shadow-xl flex flex-col h-[calc(100vh-160px)] min-h-[600px]">
                <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/5 shrink-0">
                  <h2 className="font-bold text-white text-sm uppercase tracking-widest flex items-center gap-2">
                    <Radio className="w-4 h-4 text-cyan-400" /> Live Event Console
                  </h2>
                  <span className="text-[10px] font-mono text-zinc-500 bg-white/5 px-2 py-1 rounded-md">{events.length} EVENTS</span>
                </div>
                <div className="flex-1 overflow-hidden">
                  <LiveLog events={events} onSelectSymbol={setSelectedSymbol} />
                </div>
              </div>

              {/* Sidebar Settings */}
              <div className="space-y-6">

                {/* System Config */}
                <div className="bg-[#121214]/80 backdrop-blur-sm border border-white/5 rounded-2xl p-6 shadow-xl">
                  <h3 className="text-xs font-bold text-zinc-300 uppercase tracking-widest mb-6 flex items-center gap-2">
                    <Settings className="w-4 h-4 text-zinc-400" /> System Config
                  </h3>
                  <div className="space-y-1 text-[11px] font-mono tracking-wide">
                    <div className="flex justify-between items-center py-2.5 border-b border-white/[0.03]">
                      <span className="text-zinc-500">STRATEGY</span>
                      <span className="font-bold text-emerald-400">FUSION + ML</span>
                    </div>
                    <div className="flex justify-between items-center py-2 border-b border-white/[0.03]">
                      <span className="text-zinc-500">TIMEFRAME</span>
                      <select
                        className="bg-[#09090b] border border-white/10 rounded-lg px-3 py-1.5 text-zinc-200 outline-none cursor-pointer focus:border-emerald-500/50"
                        value={botConfig?.timeframe || '15m'}
                        onChange={(e) => updateTimeframe(e.target.value)}
                      >
                        {['1m', '3m', '5m', '15m', '1h', '4h', '1d'].map(tf => (
                          <option key={tf} value={tf}>{tf}</option>
                        ))}
                      </select>
                    </div>

                    {/* MIN SCORE */}
                    <div className="flex justify-between items-center py-2 border-b border-white/[0.03]">
                      <div>
                        <div className="text-zinc-500">MIN SCORE</div>
                        <div className="text-zinc-600 text-[9px]">Signal threshold (0-100)</div>
                      </div>
                      <input
                        type="number" min={0} max={100} step={5}
                        defaultValue={botConfig?.min_signal_score ?? 60}
                        key={botConfig?.min_signal_score}
                        className="w-20 bg-[#09090b] border border-white/10 rounded-lg px-2 py-1.5 text-zinc-100 outline-none text-right focus:border-emerald-500/50 transition-colors"
                        onBlur={async (e) => { try { await api.updateConfig({ min_signal_score: Number(e.target.value) }); fetchAll(); } catch {} }}
                        onKeyDown={async (e) => { if (e.key === 'Enter') { (e.target as HTMLInputElement).blur(); } }}
                      />
                    </div>

                    {/* MAX RISK */}
                    <div className="flex justify-between items-center py-2 border-b border-white/[0.03]">
                      <div>
                        <div className="text-zinc-500">MAX RISK / TRADE</div>
                        <div className="text-zinc-600 text-[9px]">% of balance per trade</div>
                      </div>
                      <div className="flex items-center gap-1">
                        <input
                          type="number" min={1} max={100} step={1}
                          defaultValue={botConfig?.max_risk_per_trade_pct ?? 10}
                          key={botConfig?.max_risk_per_trade_pct}
                          className="w-16 bg-[#09090b] border border-white/10 rounded-lg px-2 py-1.5 text-zinc-100 outline-none text-right focus:border-emerald-500/50 transition-colors"
                          onBlur={async (e) => { try { await api.updateConfig({ max_risk_per_trade_pct: Number(e.target.value) }); fetchAll(); } catch {} }}
                          onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
                        />
                        <span className="text-zinc-500">%</span>
                      </div>
                    </div>

                    {/* MAX POSITIONS */}
                    <div className="flex justify-between items-center py-2 border-b border-white/[0.03]">
                      <div>
                        <div className="text-zinc-500">MAX POSITIONS</div>
                        <div className="text-zinc-600 text-[9px]">Open trades at once</div>
                      </div>
                      <input
                        type="number" min={1} max={100} step={1}
                        defaultValue={botConfig?.max_open_positions ?? 20}
                        key={botConfig?.max_open_positions}
                        className="w-20 bg-[#09090b] border border-white/10 rounded-lg px-2 py-1.5 text-zinc-100 outline-none text-right focus:border-emerald-500/50 transition-colors"
                        onBlur={async (e) => { try { await api.updateConfig({ max_open_positions: Number(e.target.value) }); fetchAll(); } catch {} }}
                        onKeyDown={(e) => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur(); }}
                      />
                    </div>

                    {/* OPERATING MODE */}
                    <div className="flex justify-between items-center py-2 border-b border-white/[0.03]">
                      <div>
                        <div className="text-zinc-500 font-bold uppercase">MODE</div>
                        <div className="text-zinc-600 text-[9px]">Live vs Simulation</div>
                      </div>
                      <select
                        className={`bg-[#09090b] border rounded-lg px-2 py-1.5 text-zinc-200 outline-none cursor-pointer text-[10px] font-bold tracking-widest ${botConfig?.mode === 'SIMULATION' ? 'border-purple-500 text-purple-400' : 'border-white/10'}`}
                        value={botConfig?.mode || 'LIVE'}
                        onChange={async (e) => {
                          try { await api.updateConfig({ mode: e.target.value }); fetchAll(); } catch { }
                        }}
                      >
                        <option value="PAPER">PAPER TRADING (SIMULATED)</option>
                        <option value="BINANCE_TESTNET">BINANCE TESTNET (LIVE)</option>
                        <option value="SIMULATION">HISTORICAL SIMULATION</option>
                      </select>
                    </div>

                    {/* SIM SPEED */}
                    {botConfig?.mode === 'SIMULATION' && (
                      <div className="flex justify-between items-center py-2 border-b border-white/[0.03] animate-in slide-in-from-top duration-300">
                        <div>
                          <div className="text-purple-400 font-bold">SIM SPEED</div>
                          <div className="text-zinc-600 text-[9px]">Acceleration factor</div>
                        </div>
                        <select
                          className="bg-[#09090b] border border-purple-500/20 rounded-lg px-2 py-1.5 text-purple-300 outline-none cursor-pointer text-[10px] font-bold"
                          value={botConfig?.sim_speed || 1}
                          onChange={async (e) => {
                            try { await api.updateConfig({ sim_speed: Number(e.target.value) }); fetchAll(); } catch { }
                          }}
                        >
                          {[1, 2, 5, 10, 50, 100, 500].map(s => (
                            <option key={s} value={s}>{s}x Speed</option>
                          ))}
                        </select>
                      </div>
                    )}

                    {/* RESET DATABASE */}
                    <div className="pt-6 mt-4 border-t border-red-500/10">
                      <button
                        onClick={handleReset}
                        className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl text-[11px] font-bold tracking-widest uppercase bg-red-500/10 text-red-400 border border-red-500/20 hover:bg-red-500/20 transition-all group shadow-[0_0_15px_rgba(239,68,68,0.05)]"
                      >
                        <Trash2 className="w-3.5 h-3.5 group-hover:animate-bounce" />
                        Reset Database
                      </button>
                    </div>
                  </div>
                </div>

                {/* Recent Executions */}
                <div className="bg-[#121214]/80 backdrop-blur-sm border border-white/5 rounded-2xl p-6 shadow-xl">
                  <h3 className="text-xs font-bold text-zinc-300 uppercase tracking-widest mb-4 flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-zinc-400" /> Recent Executions
                  </h3>
                  <div className="space-y-1 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                    {trades.slice(0, 8).map(t => (
                      <div key={t.id} className="flex justify-between items-center py-3 border-b border-white/[0.03] last:border-0 group hover:bg-white/[0.02] rounded-xl px-3 -mx-3 transition-colors">
                        <div className="flex items-center gap-3">
                          <span className={`w-8 text-[9px] font-bold uppercase rounded flex items-center justify-center py-1 ${t.side === 'BUY' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-red-500/10 text-red-400 border border-red-500/20'}`}>
                            {t.side}
                          </span>
                          <button onClick={() => setSelectedSymbol(t.symbol)} className="text-zinc-200 font-mono text-[11px] font-bold tracking-wide hover:text-cyan-400">
                            {t.symbol}
                          </button>
                        </div>
                        <span className={`font-mono text-[11px] font-bold ${t.status === 'CLOSED' ? ((t.pnl ?? 0) >= 0 ? 'text-emerald-400' : 'text-red-400') : 'text-zinc-500'}`}>
                          {t.status === 'CLOSED' ? `${(t.pnl ?? 0) >= 0 ? '+' : ''}$${(t.pnl ?? 0).toFixed(3)}` : 'OPEN'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </div>
          )}

          {/* Render Panels */}
          {tab === 'scanner' && <ScannerPanel results={scanResults} lastScan={lastScan} onScan={triggerScan} scanning={scanning} onSelectSymbol={setSelectedSymbol} />}
          {tab === 'trades' && <ActiveTrades trades={trades} onSelectSymbol={setSelectedSymbol} onExecuteTrade={async (sym, side, amt) => {
            try { await api.executeTrade(sym, side, amt); fetchAll(); } catch (err: any) { alert(err.response?.data?.detail || "Trade failed"); }
          }} />}
          {tab === 'predictions' && <PredictionsPanel predictions={predictions} patterns={patterns} onSelectSymbol={setSelectedSymbol} />}
          {tab === 'performance' && <PerformancePanel perf={performance} />}
          {tab === 'strategies' && <StrategiesPanel 
            strategies={strategies} 
            activeStrategies={botConfig?.active_strategies} 
            onToggle={toggleStrategy}
          />}

        </div>
      </div>

      {/* ── MODALS ── */}
      {selectedSymbol && (
        <StockDetailModal symbol={selectedSymbol} onClose={() => setSelectedSymbol(null)} />
      )}
    </div>
  );
}
