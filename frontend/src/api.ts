import axios from 'axios';

export const API_URL = 'http://localhost:8000/api';
export const WS_URL  = 'ws://localhost:8000/ws/events';

export const api = {
  getPortfolio:   () => axios.get(`${API_URL}/portfolio`),
  fundPortfolio:  (amount: number) => axios.post(`${API_URL}/portfolio/fund`, { amount }),
  getTrades:      (status?: string) => axios.get(`${API_URL}/trades`, { params: { status, limit: 200 } }),
  executeTrade:   (symbol: string, side: string, amount_usd: number) => axios.post(`${API_URL}/trades/execute`, { symbol, side, amount_usd }),
  getLogs:        (limit = 200) => axios.get(`${API_URL}/logs`, { params: { limit } }),
  getBotConfig:   () => axios.get(`${API_URL}/bot/config`),
  toggleBot:      () => axios.post(`${API_URL}/bot/toggle`),
  updateConfig:   (data: any) => axios.post(`${API_URL}/bot/config`, data),
  getScanner:     () => axios.get(`${API_URL}/scanner`),
  triggerScan:    () => axios.post(`${API_URL}/scanner/run`),
  getPredictions: () => axios.get(`${API_URL}/predictions`),
  getPatterns:    () => axios.get(`${API_URL}/patterns`),
  getStrategies:  () => axios.get(`${API_URL}/strategies`),
  getPerformance: () => axios.get(`${API_URL}/performance`),
  getChart:       (symbol: string, timeframe = '15m') => axios.get(`${API_URL}/chart`, { params: { symbol, timeframe } }),
  resetDatabase:  () => axios.post(`${API_URL}/admin/reset-db`),
};

export type EventSeverity = 'INFO' | 'SUCCESS' | 'WARNING' | 'DANGER';
export type EventType = 'SYSTEM' | 'SCANNER' | 'SIGNAL' | 'PATTERN' | 'PREDICTION' | 'TRADE' | 'RISK' | 'LEARNING' | 'ERROR';

export interface BotEvent {
  id: number | null;
  timestamp: string;
  event_type: EventType;
  severity: EventSeverity;
  symbol: string | null;
  title: string;
  detail: string | null;
}

export interface Trade {
  id: number;
  symbol: string;
  side: string;
  quantity: number;
  entry_price: number;
  exit_price?: number;
  stop_loss?: number;
  take_profit?: number;
  pnl?: number;
  status: string;
  entry_time: string;
  exit_time?: string;
  reason?: string;
  ml_confidence?: number;
  ml_direction?: string;
  highest_price?: number;
  is_trailing_active?: boolean;
}

export interface ScanResult {
  symbol: string;
  trend: string;
  score: number;
  price: number;
  change_1h: number;
  change_24h: number;
  rsi: number;
  adx: number;
  mfi: number;
  stochrsi: number;
  willr: number;
  volume_ratio: number;
  atr_pct: number;
  scanned_at: string;
}
