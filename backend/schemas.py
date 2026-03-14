from typing import Optional, List, Dict
from pydantic import BaseModel
from datetime import datetime


class TradeCreate(BaseModel):
    symbol: str
    side: str
    quantity: float
    entry_price: float


class BotConfig(BaseModel):
    trading_enabled: bool
    strategy: str
    timeframe: str
    min_signal_score: float
    max_risk_per_trade_pct: float
    max_open_positions: int
    mode: str = "PAPER"
    strategy_weights: Dict[str, float]
    scan_enabled: bool = True
    trailing_sl_enabled: bool = True

class Trade(BaseModel):
    id: int
    symbol: str
    side: str
    type: str
    mode: str = "PAPER"
    quantity: float
    entry_price: float
    exit_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pnl: Optional[float] = None
    status: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    reason: Optional[str] = None
    ml_confidence: Optional[float] = None
    ml_direction: Optional[str] = None
    highest_price: Optional[float] = None
    is_trailing_active: Optional[bool] = None

    class Config:
        from_attributes = True


class Portfolio(BaseModel):
    id: int
    balance: float
    updated_at: datetime

    class Config:
        from_attributes = True


class PortfolioFund(BaseModel):
    amount: float


class TradeManualExecute(BaseModel):
    symbol: str
    side: str
    amount_usd: float


class BotConfigUpdate(BaseModel):
    # Core
    trading_enabled: Optional[bool] = None
    symbols: Optional[List[str]] = None
    timeframe: Optional[str] = None
    htf_timeframe: Optional[str] = None
    max_risk_per_trade_pct: Optional[float] = None
    max_open_positions: Optional[int] = None
    min_signal_score: Optional[float] = None
    daily_drawdown_limit_pct: Optional[float] = None
    scan_enabled: Optional[bool] = None
    trailing_sl_enabled: Optional[bool] = None
    mode: Optional[str] = None
    sim_speed: Optional[int] = None
    sim_start_date: Optional[int] = None
    active_strategies: Optional[List[str]] = None
    # V3 filter controls (exposed to UI)
    min_strategy_agreements: Optional[int] = None
    adx_trend_threshold: Optional[int] = None
    volume_surge_min_ratio: Optional[float] = None
    htf_confirmation_required: Optional[bool] = None
    candle_quality_filter: Optional[bool] = None
    session_filter: Optional[bool] = None
    partial_tp_enabled: Optional[bool] = None
    partial_tp_atr_mult: Optional[float] = None


class BacktestRequest(BaseModel):
    symbol: str
    timeframe: str = "15m"
    initial_balance: float = 10000.0