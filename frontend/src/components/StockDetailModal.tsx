import { useEffect, useRef, useState } from 'react';
import { createChart, ColorType, CrosshairMode, CandlestickSeries, HistogramSeries } from 'lightweight-charts';
import type { IChartApi, ISeriesApi } from 'lightweight-charts';
import { X, Activity, AlertCircle, BarChart2 } from 'lucide-react';
import { api } from '../api';

export default function StockDetailModal({ 
  symbol, 
  onClose 
}: { 
  symbol: string; 
  onClose: () => void;
}) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [chartData, setChartData] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeframe, setTimeframe] = useState('15m');

  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);

  useEffect(() => {
    let isMounted = true;
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api.getChart(symbol, timeframe);
        if (isMounted) {
          const formattedData = res.data.map((d: any) => ({
            ...d,
            // Provide correctly formatted colors for the volume series
            color: d.close >= d.open ? '#34d399' : '#f87171',
          }));
          setChartData(formattedData);
        }
      } catch (err: any) {
        if (isMounted) setError(err.response?.data?.detail || "Failed to load chart data");
      } finally {
        if (isMounted) setLoading(false);
      }
    };
    fetchData();
    return () => { isMounted = false; };
  }, [symbol, timeframe]);

  useEffect(() => {
    if (!chartContainerRef.current || chartData.length === 0) return;

    // Dispose old chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const el = chartContainerRef.current;

    const chart = createChart(el, {
      layout: {
        background: { type: ColorType.Solid, color: '#09090b' },
        textColor: '#71717a',
        fontFamily: 'ui-monospace, SFMono-Regular, monospace',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.04)' },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: {
          color: 'rgba(255,255,255,0.2)',
          labelBackgroundColor: '#27272a',
        },
        horzLine: {
          color: 'rgba(255,255,255,0.2)',
          labelBackgroundColor: '#27272a',
        },
      },
      rightPriceScale: {
        borderColor: 'rgba(255,255,255,0.06)',
        scaleMargins: { top: 0.08, bottom: 0.28 },  // Leave bottom 28% for volume
      },
      leftPriceScale: {
        visible: false,
      },
      timeScale: {
        borderColor: 'rgba(255,255,255,0.06)',
        timeVisible: true,
        secondsVisible: false,
        barSpacing: 8,
      },
      handleScroll: { vertTouchDrag: false },
      autoSize: true,
    });

    // ── CANDLESTICK (price) series ──
    const candleSeries = chart.addSeries(CandlestickSeries, {
      upColor:      '#34d399',
      downColor:    '#f87171',
      borderVisible: false,
      wickUpColor:   '#34d399',
      wickDownColor: '#f87171',
    });

    // ── VOLUME histogram series — separate overlay with its own scale margins ──
    const volumeSeries = chart.addSeries(HistogramSeries, {
      priceFormat: { type: 'volume' },
      priceScaleId: 'vol',
    });

    // Position volume in the bottom 25% of the chart
    chart.priceScale('vol').applyOptions({
      scaleMargins: { top: 0.76, bottom: 0 },
    });

    // Feed data
    const cData = chartData.map(d => ({ time: d.time, open: d.open, high: d.high, low: d.low, close: d.close }));
    const vData = chartData.map(d => ({
      time:  d.time,
      value: d.value,
      color: d.close >= d.open ? 'rgba(52,211,153,0.35)' : 'rgba(248,113,113,0.35)',
    }));

    candleSeries.setData(cData);
    volumeSeries.setData(vData);

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    chart.timeScale().fitContent();

    const handleResize = () => {
      if (el && chartRef.current) {
        chartRef.current.applyOptions({
          width: el.clientWidth,
          height: el.clientHeight,
        });
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
      }
    };
  }, [chartData]); // Re-create chart only when data changes

  // Escape key handler
  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, [onClose]);

  const currentPrice = chartData.length > 0 ? chartData[chartData.length - 1].close : 0;
  const previousPrice = chartData.length > 1 ? chartData[0].open : 0;
  const priceChange = currentPrice - previousPrice;
  const priceChangePct = previousPrice !== 0 ? (priceChange / previousPrice) * 100 : 0;
  const isPositive = priceChange >= 0;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 bg-black/80 backdrop-blur-sm">
      <div 
        className="w-full max-w-5xl max-h-[90vh] bg-[#121214] border border-white/10 rounded-2xl shadow-2xl flex flex-col overflow-hidden relative"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Subtle top glow */}
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-emerald-500/0 via-cyan-500/30 to-purple-500/0" />

        {/* ── HEADER ── */}
        <div className="flex items-center justify-between p-5 border-b border-white/[0.05] bg-white/[0.02]">
          <div className="flex items-center gap-4">
            <div className="p-2 rounded-xl bg-cyan-500/10 border border-cyan-500/20 shadow-[0_0_15px_rgba(34,211,238,0.1)]">
              <Activity className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white tracking-widest uppercase flex items-center gap-2">
                {symbol}
              </h2>
              {chartData.length > 0 && (
                <div className="flex items-center gap-3 text-sm mt-1">
                  <span className="font-mono text-zinc-100 font-bold">${currentPrice.toFixed(4)}</span>
                  <span className={`font-mono text-xs font-bold flex items-center gap-1 ${isPositive ? 'text-emerald-400' : 'text-red-400'}`}>
                    {isPositive ? '+' : ''}{priceChange.toFixed(4)} ({priceChangePct.toFixed(2)}%)
                  </span>
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center gap-4">
            {/* Timeframe selector */}
            <div className="hidden sm:flex bg-black/50 border border-white/10 rounded-lg p-1">
              {['1m', '5m', '15m', '1h', '4h', '1d'].map(tf => (
                <button
                  key={tf}
                  onClick={() => setTimeframe(tf)}
                  className={`px-3 py-1 text-[10px] font-mono font-bold uppercase rounded-md transition-all ${
                    timeframe === tf
                      ? 'bg-white/10 text-white shadow-sm'
                      : 'text-zinc-500 hover:text-zinc-300'
                  }`}
                >
                  {tf}
                </button>
              ))}
            </div>

            <button 
              onClick={onClose}
              className="p-2 bg-white/5 border border-white/10 rounded-xl text-zinc-400 hover:text-white hover:bg-white/10 transition-colors group"
            >
              <X className="w-5 h-5 group-hover:rotate-90 transition-transform duration-300" />
            </button>
          </div>
        </div>

        {/* ── CHART BODY ── */}
        <div className="relative h-[450px] sm:h-[500px] bg-[#09090b] px-1 pb-1 sm:px-5 sm:pb-5">
          {loading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#09090b]/80 backdrop-blur-sm">
              <BarChart2 className="w-8 h-8 text-cyan-500/50 animate-pulse mb-4" />
              <p className="text-zinc-400 font-mono text-xs uppercase tracking-widest animate-pulse">Loading Chart Data...</p>
            </div>
          )}
          
          {error && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center bg-[#09090b]/90 backdrop-blur-sm">
              <AlertCircle className="w-10 h-10 text-red-500/50 mb-4" />
              <p className="text-red-400 font-mono text-xs uppercase tracking-widest">{error}</p>
              <button 
                onClick={() => { setLoading(true); setTimeframe(timeframe); }}
                className="mt-4 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-mono text-zinc-300 transition-colors"
              >
                RETRY
              </button>
            </div>
          )}

          <div 
            ref={chartContainerRef} 
            className={`w-full h-full transition-opacity duration-500 ${loading || error ? 'opacity-0' : 'opacity-100'}`} 
          />
        </div>
      </div>
    </div>
  );
}
