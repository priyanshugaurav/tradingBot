"""
Advanced Multi-Strategy Bot Engine V2
Strategies: EMA Crossover | RSI Divergence | MACD | Bollinger Bands | Volume Surge
Includes: signal aggregation, ML fusion, pattern detection, learning weights, risk management
"""
import asyncio
import ccxt
import pandas as pd
import pandas_ta as ta
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
import database, models
import event_log as el
import pattern_detector as pd_
import ml_predictor as mlp
import market_scanner as ms

# ── Exchange ──────────────────────────────────────────────────────────────────
_exchange = ccxt.binance({
    'enableRateLimit': True,
    'timeout': 30000,
})

from binance_bot.client import BinanceFuturesClient
binance_testnet_client = BinanceFuturesClient()

# Bot state and configuration
bot_config = {
    "trading_enabled": False,
    "strategy": "FUSION",  # FUSION, ML, or INDIVIDUAL_NAME
    "timeframe": "15m",
    "min_signal_score": 60,
    "max_risk_per_trade_pct": 10,  # % of balance
    "max_open_positions": 10,
    "mode": "PAPER",           # PAPER, BINANCE_TESTNET, or SIMULATION
    "strategy_weights": {
        "ema_crossover": 1.0,
        "advanced_oscillators": 1.5,
        "macd": 1.0,
        "bollinger": 1.0,
        "volume_surge": 1.0,
        "ml_prediction": 1.5,
        "vwap": 1.0,
        "supertrend": 1.5,
        "ichimoku": 1.0,
    },
    "scan_enabled": True,
    "trailing_sl_enabled": True,
    "leverage": 20, 
    "symbols": ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT"],
}

CONFIG_FILE = "bot_config.json"

def save_config():
    try:
        # Don't save trading_enabled as True to avoid auto-start on crash/restart
        to_save = bot_config.copy()
        to_save["trading_enabled"] = False 
        with open(CONFIG_FILE, "w") as f:
            json.dump(to_save, f, indent=4)
    except Exception: pass

def load_config():
    global bot_config
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
                bot_config.update(saved)
        except Exception: pass

# Initial load
import json
import os
load_config()

# ── In-memory analytics ───────────────────────────────────────────────────────
strategy_stats: Dict[str, Dict] = {
    s: {"wins": 0, "losses": 0, "signals": 0}
    for s in ["ema_crossover", "advanced_oscillators", "macd", "bollinger", "volume_surge", "ml_prediction", "vwap", "supertrend", "ichimoku"]
}
predictions_cache: Dict[str, Dict] = {}
patterns_cache: Dict[str, List] = {}
ohlcv_cache: Dict[str, pd.DataFrame] = {}

# ── Simulation State ─────────────────────────────────────────────────────────
sim_context = {
    "active": False,
    "index": 0,
    "data": {},  # {symbol: df}
    "symbols": [],
    "total_steps": 0
}


# ══════════════════════════════════════════════════════════════════════════════
#  Data Fetcher
# ══════════════════════════════════════════════════════════════════════════════
def _sync_fetch_ohlcv(symbol: str, timeframe: str, limit: int):
    return _exchange.fetch_ohlcv(symbol, timeframe, limit=limit)

async def fetch_ohlcv(symbol: str, timeframe: str, limit: int = 150) -> Optional[pd.DataFrame]:
    try:
        data = await asyncio.to_thread(_sync_fetch_ohlcv, symbol, timeframe, limit)
        df = pd.DataFrame(data, columns=["timestamp","open","high","low","close","volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        ohlcv_cache[symbol] = df
        return df
    except Exception as e:
        el.log(f"OHLCV fetch failed for {symbol}: {e}", el.EventType.ERROR, el.EventSeverity.WARNING, symbol)
        return None

import yfinance as yf

def _sync_yf_history(ticker, start, end, interval):
    return ticker.history(start=start, end=end, interval=interval)

async def fetch_historical_ohlcv(symbol: str, timeframe: str, since_ms: int, limit: int = 1000) -> Optional[pd.DataFrame]:
    # Use yfinance for backtesting as CCXT/Binance history has brutal rate limits/bans
    try:
        # Convert symbol BTC/USDT -> BTC-USD for Yahoo Finance
        yf_symbol = symbol.replace("/", "-").replace("USDT", "USD")
        
        # Convert since_ms to datetime
        start_dt = datetime.utcfromtimestamp(since_ms / 1000.0)
        # Fetch a bit more than limit to ensure we have enough after dropping NaNs
        end_dt = start_dt + timedelta(days=6)
        
        # yfinance timeframes: 1m, 2m, 5m, 15m, 30m, 60m, 90m, 1h, 1d, 5d, 1wk, 1mo, 3mo
        yf_interval = timeframe
        if timeframe not in ["1m", "5m", "15m", "30m", "60m", "1d"]:
            yf_interval = "15m" # Default generic fallback
            
        el.log(f"Fetching yfinance {yf_symbol} interval={yf_interval} from {start_dt.date()} to {end_dt.date()}", el.EventType.SYSTEM, el.EventSeverity.INFO)
            
        ticker = yf.Ticker(yf_symbol)
        df = await asyncio.to_thread(_sync_yf_history, ticker, start_dt, end_dt, yf_interval)
        
        if df.empty:
            el.log(f"yfinance returned empty dataframe for {yf_symbol}", el.EventType.ERROR, el.EventSeverity.WARNING)
            return None
            
        # Standardize columns to match our CCXT format
        df.reset_index(inplace=True)
        # yfinance index is 'Datetime'
        time_col = 'Datetime' if 'Datetime' in df.columns else 'Date'
        df.rename(columns={
            time_col: "timestamp",
            "Open": "open",
            "High": "high",
            "Low": "low",
            "Close": "close",
            "Volume": "volume"
        }, inplace=True)
        
        # Select only needed columns
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        # Remove timezone info for compatibility with our internal signals
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
        df.set_index("timestamp", inplace=True)
        
        return df.head(limit)
    except Exception as e:
        el.log(f"Historical OHLCV fetch failed for {symbol}: {e}", el.EventType.ERROR, el.EventSeverity.WARNING, symbol)
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  Individual Strategy Signals  (each returns a score: -100 to +100)
# ══════════════════════════════════════════════════════════════════════════════
def _ema_crossover_signal(df: pd.DataFrame) -> Tuple[float, str]:
    df = df.copy()
    df.ta.ema(length=9,  append=True)
    df.ta.ema(length=21, append=True)
    df.ta.ema(length=50, append=True)

    cur  = df.iloc[-1]
    prev = df.iloc[-2]

    ema9_c, ema21_c, ema50_c = cur.get("EMA_9",cur["close"]),  cur.get("EMA_21",cur["close"]),  cur.get("EMA_50",cur["close"])
    ema9_p, ema21_p          = prev.get("EMA_9",prev["close"]), prev.get("EMA_21",prev["close"])

    score = 0
    # Golden cross (9 crosses above 21)
    if ema9_c > ema21_c and ema9_p <= ema21_p: score = 80
    # Death cross
    elif ema9_c < ema21_c and ema9_p >= ema21_p: score = -80
    # Trend alignment (partial)
    elif ema9_c > ema21_c > ema50_c: score = 40
    elif ema9_c < ema21_c < ema50_c: score = -40

    detail = f"EMA9={ema9_c:.4f} EMA21={ema21_c:.4f} EMA50={ema50_c:.4f}"
    return score, detail


def _advanced_oscillators_signal(df: pd.DataFrame) -> Tuple[float, str]:
    df = df.copy()
    df.ta.rsi(length=14, append=True)
    df.ta.mfi(length=14, append=True)
    df.ta.stochrsi(length=14, rsi_length=14, append=True)
    df.ta.willr(length=14, append=True)
    
    rsi   = df.get("RSI_14", pd.Series([50])).iloc[-1]
    mfi   = df.get("MFI_14", pd.Series([50])).iloc[-1]
    stoch = df.get("STOCHRSIk_14_14_3_3", pd.Series([0.5])).iloc[-1] * 100
    willr = df.get("WILLR_14", pd.Series([-50])).iloc[-1]

    score = 0
    # Overbought checks (Sell signals)
    if rsi > 70 and stoch > 80 and mfi > 80: score = -80
    elif stoch > 80 and willr > -20: score = -60
    elif rsi > 70: score = -30

    # Oversold checks (Buy signals)
    elif rsi < 30 and stoch < 20 and mfi < 20: score = 80
    elif stoch < 20 and willr < -80: score = 60
    elif rsi < 30: score = 30

    return score, f"RSI={rsi:.0f} MFI={mfi:.0f} Stoch={stoch:.0f} W%R={willr:.0f}"


def _macd_signal(df: pd.DataFrame) -> Tuple[float, str]:
    df = df.copy()
    df.ta.macd(append=True)
    hist_col = "MACDh_12_26_9"
    sig_col  = "MACDs_12_26_9"
    macd_col = "MACD_12_26_9"

    if hist_col not in df.columns: return 0, "MACD N/A"

    cur_h  = df[hist_col].iloc[-1]
    prev_h = df[hist_col].iloc[-2]
    cur_s  = df[sig_col].iloc[-1]
    cur_m  = df[macd_col].iloc[-1]

    score = 0
    # MACD crosses signal line
    if cur_m > cur_s and df[macd_col].iloc[-2] <= df[sig_col].iloc[-2]: score = 80
    elif cur_m < cur_s and df[macd_col].iloc[-2] >= df[sig_col].iloc[-2]: score = -80
    # Histogram expanding
    elif cur_h > 0 and cur_h > prev_h: score = 40
    elif cur_h < 0 and cur_h < prev_h: score = -40

    return score, f"MACD={cur_m:.6f} Signal={cur_s:.6f} Hist={cur_h:.6f}"


def _bollinger_signal(df: pd.DataFrame) -> Tuple[float, str]:
    df = df.copy()
    df.ta.bbands(length=20, append=True)
    close = df["close"].iloc[-1]
    upr   = df.get("BBU_20_2.0", pd.Series([close])).iloc[-1]
    lwr   = df.get("BBL_20_2.0", pd.Series([close])).iloc[-1]
    mid   = df.get("BBM_20_2.0", pd.Series([close])).iloc[-1]

    if "BBU_20_2.0" not in df.columns: return 0, "BB N/A"

    upr = df["BBU_20_2.0"].iloc[-1]
    lwr = df["BBL_20_2.0"].iloc[-1]
    mid = df["BBM_20_2.0"].iloc[-1]

    bb_pct = (close - lwr) / (upr - lwr + 1e-8)

    score = 0
    if close < lwr:          score = 70    # Price below lower band → oversold bounce
    elif close > upr:        score = -70   # Price above upper band → overbought
    elif bb_pct < 0.2:       score = 40
    elif bb_pct > 0.8:       score = -40

    return score, f"BB%={bb_pct:.2f} Upper={upr:.4f} Lower={lwr:.4f}"


def _volume_surge_signal(df: pd.DataFrame) -> Tuple[float, str]:
    vol     = df["volume"]
    cur_vol = vol.iloc[-1]
    avg_vol = vol.iloc[-20:-1].mean()
    ratio   = cur_vol / (avg_vol + 1e-8)
    close_change = (df["close"].iloc[-1] - df["close"].iloc[-2]) / df["close"].iloc[-2]

    score = 0
    if ratio > 2.0:
        score = 60 * np.sign(close_change) * min(ratio / 2, 1.5)

    return score, f"VolRatio={ratio:.2f} PriceChg={close_change*100:.2f}%"

def _vwap_signal(df: pd.DataFrame) -> Tuple[float, str]:
    df = df.copy()
    # vwap requires a DatetimeIndex usually, which we have (timestamp)
    try:
        df.ta.vwap(append=True)
        vwap_val = df["VWAP_D"].iloc[-1]
        close = df["close"].iloc[-1]
        
        score = 0
        dist = (close - vwap_val) / vwap_val
        
        # Pullback to VWAP in an uptrend (buying opportunity)
        if 0 < dist < 0.005: score = 50
        elif close > vwap_val: score = 20
        elif -0.005 < dist < 0: score = -50
        elif close < vwap_val: score = -20
        
        return score, f"VWAP={vwap_val:.2f} Dist={dist*100:.2f}%"
    except Exception:
        return 0, "VWAP Error"


def _supertrend_signal(df: pd.DataFrame) -> Tuple[float, str]:
    df = df.copy()
    try:
        # returns df with columns like SUPERT_7_3.0, SUPERTd_7_3.0 (direction), SUPERTl_7_3.0 (long), SUPERTs_7_3.0 (short)
        sti = df.ta.supertrend(length=10, multiplier=3.0)
        # Combine column names since they depend on inputs
        dir_col = [c for c in sti.columns if c.startswith("SUPERTd_")][0]
        val_col = [c for c in sti.columns if c.startswith("SUPERT_")][0]
        
        cur_dir = sti[dir_col].iloc[-1]
        prev_dir = sti[dir_col].iloc[-2]
        
        score = 0
        if cur_dir == 1 and prev_dir == -1: score = 80 # Flipped to bullish
        elif cur_dir == -1 and prev_dir == 1: score = -80 # Flipped to bearish
        elif cur_dir == 1: score = 40 # Trending up
        elif cur_dir == -1: score = -40 # Trending down
        
        return score, f"ST_Dir={cur_dir} Val={sti[val_col].iloc[-1]:.2f}"
    except Exception:
        return 0, "Supertrend Error"


def _ichimoku_signal(df: pd.DataFrame) -> Tuple[float, str]:
    df = df.copy()
    try:
        # returns 2 dfs, first one has the lines
        ichi, _ = df.ta.ichimoku()
        
        tenkan = ichi[ichi.columns[0]].iloc[-1] # ISA_9
        kijun = ichi[ichi.columns[1]].iloc[-1]  # ISB_26
        senkou_a = ichi[ichi.columns[2]].iloc[-1] # ITS_9
        senkou_b = ichi[ichi.columns[3]].iloc[-1] # IKS_26
        close = df["close"].iloc[-1]
        
        score = 0
        # Check cloud (Kumo)
        if close > senkou_a and close > senkou_b:
            score += 40 # Bullish territory
            if tenkan > kijun: score += 40 # TK Cross
        elif close < senkou_a and close < senkou_b:
            score -= 40 # Bearish territory
            if tenkan < kijun: score -= 40 # TK Cross
            
        return score, f"Cloud A={senkou_a:.2f} B={senkou_b:.2f} TK={tenkan:.2f}/{kijun:.2f}"
    except Exception:
        return 0, "Ichimoku Error"


# ══════════════════════════════════════════════════════════════════════════════
#  Signal Aggregator (fuses all strategies into composite score)
# ══════════════════════════════════════════════════════════════════════════════
def compute_composite_signal(symbol: str, df: pd.DataFrame) -> Dict:
    weights = bot_config["strategy_weights"]
    signals = {}

    score_ema,  det_ema  = _ema_crossover_signal(df)
    score_osc,  det_osc  = _advanced_oscillators_signal(df)
    score_macd, det_macd = _macd_signal(df)
    score_bb,   det_bb   = _bollinger_signal(df)
    score_vol,  det_vol  = _volume_surge_signal(df)
    score_vwap, det_vwap = _vwap_signal(df)
    score_st,   det_st   = _supertrend_signal(df)
    score_ichi, det_ichi = _ichimoku_signal(df)

    signals["ema_crossover"]         = {"score": score_ema,  "detail": det_ema}
    signals["advanced_oscillators"]  = {"score": score_osc,  "detail": det_osc}
    signals["macd"]           = {"score": score_macd, "detail": det_macd}
    signals["bollinger"]      = {"score": score_bb,   "detail": det_bb}
    signals["volume_surge"]   = {"score": score_vol,  "detail": det_vol}
    signals["vwap"]           = {"score": score_vwap, "detail": det_vwap}
    signals["supertrend"]     = {"score": score_st,   "detail": det_st}
    signals["ichimoku"]       = {"score": score_ichi, "detail": det_ichi}

    # ML prediction
    prediction  = mlp.predict(df)
    predictions_cache[symbol] = prediction
    ml_raw = (prediction["confidence"] - 0.5) * 200  # map [0.5,1] → [0,100]
    if prediction["direction"] == "DOWN": ml_raw = -ml_raw
    signals["ml_prediction"] = {"score": ml_raw, "detail": f"ML: {prediction['direction']} @ {prediction['confidence']*100:.1f}%"}

    # Filter out inactive strategies before calculating composite
    active_strats = bot_config.get("active_strategies", list(signals.keys()))
    
    # Calculate Weighted composite for only ACTIVE strategies
    active_weight_sum = sum(weights[s] for s in signals if s in active_strats)
    
    if active_weight_sum > 0:
        composite = sum(signals[s]["score"] * weights[s] for s in signals if s in active_strats) / active_weight_sum
    else:
        composite = 0 # Default to neutral if nothing active

    # Normalize to 0-100 for display (50 = neutral, >70 = BUY, <30 = SELL)
    normalized = (composite + 100) / 2

    # Detect patterns
    patterns = pd_.detect_patterns(df)
    patterns_cache[symbol] = patterns

    dominant = pd_.get_dominant_pattern(patterns)
    # Pattern conviction modifier
    if dominant:
        if dominant["type"] == "bullish": normalized = min(100, normalized + dominant["confidence"] * 10)
        else:                             normalized = max(0,   normalized - dominant["confidence"] * 10)

    action = "BUY" if normalized >= bot_config["min_signal_score"] else ("SELL" if normalized <= (100 - bot_config["min_signal_score"]) else "HOLD")

    return {
        "symbol":       symbol,
        "action":       action,
        "score":        round(normalized, 1),
        "raw_composite": round(composite, 1),
        "signals":      signals,
        "prediction":   prediction,
        "patterns":     patterns,
        "dominant_pattern": dominant,
        "price":        df["close"].iloc[-1],
        "timestamp":    datetime.utcnow().isoformat() + "Z",
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Risk Manager
# ══════════════════════════════════════════════════════════════════════════════
def compute_position_size(balance: float, price: float, atr: float) -> float:
    """Use ATR for position sizing. Risk 1% of balance per trade at 1.5× ATR stop."""
    risk_per_trade = balance * (bot_config["max_risk_per_trade_pct"] / 100)
    stop_distance  = max(atr * 1.5, price * 0.005)   # min 0.5% stop
    quantity       = risk_per_trade / stop_distance
    max_quantity   = (balance * 0.2) / price          # cap at 20% of portfolio per trade
    return min(quantity, max_quantity)


def compute_sl_tp(entry: float, side: str, df: pd.DataFrame):
    df = df.copy()
    df.ta.atr(length=14, append=True)
    atr = df["ATRr_14"].iloc[-1]
    if side == "BUY":
        sl = entry - atr * 2.0
        tp = entry + atr * 3.5
    else:
        sl = entry + atr * 2.0
        tp = entry - atr * 3.5
    return round(sl, 6), round(tp, 6)


# ══════════════════════════════════════════════════════════════════════════════
#  Paper Trading Execution
# ══════════════════════════════════════════════════════════════════════════════
def _get_atr(df: pd.DataFrame) -> float:
    df = df.copy()
    df.ta.atr(length=14, append=True)
    return df["ATRr_14"].iloc[-1]


async def execute_trade(symbol: str, action: str, signal: Dict, df: pd.DataFrame, db: Session, timestamp: Optional[datetime] = None):
    portfolio = db.query(models.Portfolio).first()
    if not portfolio:
        return

    price  = signal["price"]
    atr    = _get_atr(df)
    qty    = compute_position_size(portfolio.balance, price, atr)
    sl, tp = compute_sl_tp(price, action, df)

    cost = price * qty
    if cost > portfolio.balance:
        el.log(f"Insufficient balance for {symbol}", el.EventType.RISK, el.EventSeverity.WARNING, symbol)
        return

    # Determine mode
    mode = bot_config.get("mode", "PAPER")

    # Execution (Real vs Paper)
    if mode == "BINANCE_TESTNET":
        try:
            await binance_testnet_client.place_order(
                symbol=symbol,
                side=action,
                order_type="MARKET",
                quantity=qty
            )
        except Exception as e:
            el.log(f"Binance {action} failed: {e}", el.EventType.ERROR, el.EventSeverity.DANGER, symbol)
            return None

    trade = models.Trade(
        symbol        = symbol,
        side          = action,
        type          = "MARKET",
        mode          = mode,
        entry_price   = price,
        quantity      = qty,
        stop_loss     = sl,
        take_profit   = tp,
        reason        = f"Score={signal['score']} | {signal.get('dominant_pattern',{}).get('name','') if signal.get('dominant_pattern') else ''}",
        signals_json  = str(signal["signals"]),
        ml_confidence = signal["prediction"]["confidence"],
        ml_direction  = signal["prediction"]["direction"],
        entry_time    = timestamp if timestamp else datetime.now()
    )
    
    # Only deduct from Paper Portfolio if in PAPER/SIMULATION mode
    if mode in ["PAPER", "SIMULATION"]:
        portfolio.balance -= cost
        
    db.add(trade)
    db.commit()
    db.refresh(trade)

    prefix = "PAPER" if mode != "BINANCE_TESTNET" else "BINANCE"
    el.log(
        f"{prefix} {action}: {symbol} @ ${price:.4f}  Qty={qty:.4f}  SL=${sl:.4f}  TP=${tp:.4f}",
        el.EventType.TRADE, el.EventSeverity.SUCCESS, symbol,
        detail=f"Score={signal['score']} | Pattern={signal.get('dominant_pattern',{}).get('name','None') if signal.get('dominant_pattern') else 'None'} | ML={signal['prediction']['direction']} {signal['prediction']['confidence']*100:.1f}%"
    )
    return trade


def _calculate_sl_tp(symbol: str, side: str, price: float):
    """Synchronous wrapper for computing SL/TP for manual trades."""
    # We use a dummy DF since compute_sl_tp needs it for ATR, 
    # but for manual trades we can fallback to a fixed % or fetch minimal ATR.
    # For now, let's use the standard ATR-based compute_sl_tp but handle the DF.
    try:
        # Try to get from cache first
        df = ohlcv_cache.get(symbol)
        if df is not None and not df.empty:
            return compute_sl_tp(price, side, df)
    except:
        pass
        
    # Fallback to fixed percentages if no DF available (e.g., 2% SL, 4% TP)
    if side == "BUY":
        return round(price * 0.98, 6), round(price * 1.04, 6)
    else:
        return round(price * 1.02, 6), round(price * 0.96, 6)


async def execute_manual_trade(symbol: str, side: str, amount_usd: float, db: Session):
    portfolio = db.query(models.Portfolio).first()
    if not portfolio or portfolio.balance < amount_usd:
        return None

    # Determine trading mode
    mode = bot_config.get("mode", "PAPER")
    
    if mode == "BINANCE_TESTNET":
        if not binance_testnet_client.is_valid_symbol(symbol):
            el.log(f"Manual {side} failed: Symbol {symbol} not supported on Binance Testnet.", el.EventType.ERROR, el.EventSeverity.DANGER, symbol)
            return None

    # Fetch latest price
    df = await fetch_ohlcv(symbol, bot_config["timeframe"], limit=50)
    if df is None or df.empty:
        return None

    price = df["close"].iloc[-1]
    leverage = bot_config.get("leverage", 1)
    qty = (amount_usd * leverage) / price
    
    # Determine trading mode
    mode = bot_config.get("mode", "PAPER")
    
    # Check if we should actually execute on Binance
    binance_response = None
    if mode == "BINANCE_TESTNET":
        try:
            # Place order on Binance Testnet
            binance_response = await binance_testnet_client.place_order(
                symbol=symbol,
                side=side,
                order_type="MARKET",
                quantity=qty
            )
            # Use actual fill price if available, otherwise fallback to current close
            price = float(binance_response.get('price', price)) if binance_response.get('price') and float(binance_response.get('price')) > 0 else price
        except Exception as e:
            el.log(f"Binance {side} failed: {str(e)}", el.EventType.ERROR, el.EventSeverity.DANGER, symbol)
            return None

    # Calculate SL/TP
    sl, tp = _calculate_sl_tp(symbol, side, price)
    
    # Create DB record
    trade = models.Trade(
        symbol      = symbol,
        side        = side,
        type        = "MARKET",
        mode        = mode,
        entry_price = price,
        quantity    = qty,
        stop_loss   = sl,
        take_profit = tp,
        reason      = "MANUAL_USER_TRADE",
        signals_json = "{}",
        ml_confidence = None,
        ml_direction  = None,
    )
    
    portfolio.balance -= amount_usd
    db.add(trade)
    db.commit()
    db.refresh(trade)

    el.log(
        f"USER MANUAL {side}: {symbol} @ ${price:.4f}  Qty={qty:.4f}",
        el.EventType.TRADE, el.EventSeverity.SUCCESS, symbol, detail="Manual Trade Execution"
    )
    return trade


async def check_sl_tp(db: Session, current_prices: Dict[str, float]):
    """Check all open trades for stop-loss, take-profit, or trailing stop hits."""
    open_trades = db.query(models.Trade).filter(models.Trade.status == "OPEN").all()
    portfolio   = db.query(models.Portfolio).first()
    mode = bot_config.get("mode", "PAPER")

    for trade in open_trades:
        price = current_prices.get(trade.symbol)
        if price is None:
            continue

        # ── Trailing Stop-Loss Logic ──────────────────────────────────────────
        # If profit exceeds 1.5% or 1 ATR, activate trailing stop
        pnl_pct = (price - trade.entry_price) / trade.entry_price if trade.side == "BUY" else (trade.entry_price - price) / trade.entry_price
        
        # Track highest (or lowest) price reached
        if trade.highest_price is None:
            trade.highest_price = price
        
        if trade.side == "BUY":
            if price > trade.highest_price:
                trade.highest_price = price
                # If trailing is active or we hit threshold, pull SL up
                if pnl_pct > 0.015 or trade.is_trailing_active:
                    trade.is_trailing_active = True
                    # Trail by 1.5% from peak
                    new_sl = trade.highest_price * 0.985
                    if new_sl > trade.stop_loss:
                        trade.stop_loss = new_sl
        else: # SELL
            if price < trade.highest_price: # For sells, "highest" price is the lowest valley
                trade.highest_price = price
                if pnl_pct > 0.015 or trade.is_trailing_active:
                    trade.is_trailing_active = True
                    # Trail by 1.5% from valley
                    new_sl = trade.highest_price * 1.015
                    if new_sl < trade.stop_loss:
                        trade.stop_loss = new_sl

        # ── Exit Condition Checks ─────────────────────────────────────────────
        hit_sl = (trade.side == "BUY"  and price <= trade.stop_loss)  or \
                 (trade.side == "SELL" and price >= trade.stop_loss)
        hit_tp = (trade.side == "BUY"  and price >= trade.take_profit) or \
                 (trade.side == "SELL" and price <= trade.take_profit)

        if hit_sl or hit_tp:
            is_tsl = hit_sl and trade.is_trailing_active
            reason_suffix = "TP HIT ✅" if hit_tp else ("TSL HIT 🛡️" if is_tsl else "SL HIT ❌")
            
            await _close_trade_logic(trade, price, reason_suffix, db)


async def _close_trade_logic(trade: models.Trade, price: float, reason_suffix: str, db: Session):
    """Internal helper to handle the actual mechanics of closing a trade."""
    pnl = (price - trade.entry_price) * trade.quantity if trade.side == "BUY" \
          else (trade.entry_price - price) * trade.quantity

    trade.exit_price = price
    trade.pnl        = pnl
    trade.status     = "CLOSED"
    trade.exit_time  = datetime.utcnow()
    trade.reason    += f" | {reason_suffix}"

    # Only close on Binance if the trade record itself was a Binance trade
    if trade.mode == "BINANCE_TESTNET":
        try:
            await binance_testnet_client.place_order(
                symbol=trade.symbol,
                side="SELL" if trade.side == "BUY" else "BUY",
                order_type="MARKET",
                quantity=trade.quantity,
                reduce_only=True
            )
        except Exception as e:
            el.log(f"Failed to close Binance position for {trade.symbol}: {e}", el.EventType.ERROR, el.EventSeverity.DANGER, trade.symbol)
            # We still mark CLOSED in DB so the bot doesn't loop forever on a dead trade, 
            # but the error log will alert the user to manually check Binance.
    
    portfolio = db.query(models.Portfolio).first()
    if portfolio:
        portfolio.balance += price * trade.quantity
        
    db.commit()

    severity = el.EventSeverity.SUCCESS if pnl > 0 else el.EventSeverity.DANGER
    peak_str = f"${trade.highest_price:.4f}" if trade.highest_price else "N/A"
    el.log(
        f"{reason_suffix} {trade.symbol}: PNL ${pnl:+.4f}",
        el.EventType.TRADE, severity, trade.symbol,
        detail=f"Entry=${trade.entry_price:.4f} Exit=${price:.4f} Peak={peak_str}"
    )

    # ML learning feedback
    try:
        hist_df = ohlcv_cache.get(trade.symbol)
        if hist_df is not None:
            mlp.record_outcome(hist_df, pnl > 0)
            if pnl > 0:
                el.log(f"ML model updated — profitable trade learned for {trade.symbol}", el.EventType.LEARNING, el.EventSeverity.INFO, trade.symbol)
    except Exception:
        pass

    # Update strategy weights (reinforcement learning)
    _update_strategy_weights(trade, pnl > 0)


async def close_manual_trade(trade_id: int, db: Session):
    """Manually close a specific trade by ID."""
    trade = db.query(models.Trade).filter(models.Trade.id == trade_id, models.Trade.status == "OPEN").first()
    if not trade:
        return False
        
    # Fetch current price
    df = await fetch_ohlcv(trade.symbol, bot_config["timeframe"], limit=5)
    if df is None or df.empty:
        return False
        
    price = df["close"].iloc[-1]
    await _close_trade_logic(trade, price, "MANUAL CLOSE ✋", db)
    return True



def _update_strategy_weights(trade: models.Trade, won: bool):
    """Update strategy weights based on trade outcome."""
    weights = bot_config["strategy_weights"]
    delta = 0.05 if won else -0.03

    # Parse signal contributions from the trade's stored signals JSON
    try:
        import ast
        sigs = ast.literal_eval(trade.signals_json)
        for strat, sig in sigs.items():
            score = sig.get("score", 0)
            if score * (1 if trade.side == "BUY" else -1) > 0:
                # Strategy agreed with the trade direction
                weights[strat] = round(max(0.1, min(3.0, weights[strat] + delta)), 3)
                strategy_stats[strat]["wins" if won else "losses"] += 1
            else:
                weights[strat] = round(max(0.1, min(3.0, weights[strat] - delta * 0.5)), 3)

        el.log(
            f"Strategy weights updated after {'WIN' if won else 'LOSS'}",
            el.EventType.LEARNING, el.EventSeverity.INFO,
            detail=str({k: round(v,3) for k, v in weights.items()})
        )
    except Exception:
        pass


# ══════════════════════════════════════════════════════════════════════════════
#  Main Trade Loop
# ══════════════════════════════════════════════════════════════════════════════
async def _init_simulation(db: Session):
    el.log("Initializing Simulation Mode...", el.EventType.SYSTEM, el.EventSeverity.INFO)
    sim_context["active"] = True
    sim_context["index"] = 100 # Start with some history (100 candles) for indicators
    sim_context["data"] = {}
    
    start_ms = bot_config.get("sim_start_date")
    if not start_ms:
        start_ms = int((datetime.now() - timedelta(days=15)).timestamp() * 1000)
        
    for symbol in bot_config["symbols"]:
        # Fetch a large chunk for simulation (yfinance fallback is handled inside)
        df = await fetch_historical_ohlcv(symbol, bot_config["timeframe"], start_ms)
        if df is not None:
            sim_context["data"][symbol] = df
            
    lengths = [len(df) for df in sim_context["data"].values()]
    if lengths:
        sim_context["total_steps"] = min(lengths)
        el.log(f"Simulation ready: {sim_context['total_steps']} steps", el.EventType.SYSTEM, el.EventSeverity.SUCCESS)
    else:
        sim_context["active"] = False
        bot_config["mode"] = "LIVE"
        el.log("Simulation failed: No data found. Returning to LIVE.", el.EventType.ERROR, el.EventSeverity.DANGER)

async def trade_loop():
    scan_counter = 0
    pause_log_counter = 0
    el.log("Bot engine V2 initialized", el.EventType.SYSTEM, el.EventSeverity.INFO)

    # Move initialization here (within event loop)
    try:
        await binance_testnet_client.initialize()
    except Exception as e:
        el.log(f"Binance Client Init Failed: {e}", el.EventType.ERROR, el.EventSeverity.DANGER)

    while True:
        try:
            if bot_config["trading_enabled"]:
                db = database.SessionLocal()
                mode = bot_config.get("mode", "LIVE")

                if mode == "SIMULATION":
                    if not sim_context["active"]:
                        await _init_simulation(db)
                    
                    if sim_context["index"] >= sim_context["total_steps"]:
                        el.log("Simulation finished. Pausing bot.", el.EventType.SYSTEM, el.EventSeverity.INFO)
                        bot_config["trading_enabled"] = False
                        sim_context["active"] = False
                        db.close()
                        await asyncio.sleep(5)
                        continue
                    
                    # SIMULATION Logic
                    sim_idx = sim_context["index"]
                    current_prices = {}
                    
                    # Current "Simulated Time" - based on first symbol's index
                    first_symbol = list(sim_context["data"].keys())[0]
                    sim_time = sim_context["data"][first_symbol].index[sim_idx]

                    for symbol, df_full in sim_context["data"].items():
                        # Slice data up to current simulated index
                        df = df_full.iloc[:sim_idx+1]
                        current_prices[symbol] = df["close"].iloc[-1]

                        signal = compute_composite_signal(symbol, df)
                        
                        # Only show/execute if it's a new "event" (simplified log logic)
                        if sim_idx % 2 == 0: # Reduce log spam in sim
                            el.log(
                                f"[SIM][{symbol}] Score={signal['score']} Action={signal['action']}",
                                el.EventType.SIGNAL, el.EventSeverity.INFO, symbol
                            )

                        if signal["action"] == "BUY":
                            open_count = db.query(models.Trade).filter(models.Trade.status == "OPEN").count()
                            if open_count < bot_config["max_open_positions"]:
                                existing = db.query(models.Trade).filter(
                                    models.Trade.symbol == symbol, models.Trade.status == "OPEN"
                                ).first()
                                if not existing:
                                    await execute_trade(symbol, "BUY", signal, df, db, timestamp=sim_time)

                    # Update step
                    sim_context["index"] += 1
                    
                    # Check SL/TP using simulated prices
                    await check_sl_tp(db, current_prices)
                    db.close()
                    
                    # Variable sleep based on sim_speed
                    # Normal: 30s. If 100x: 0.3s
                    speed = bot_config.get("sim_speed", 1)
                    await asyncio.sleep(max(0.05, 30.0 / speed))
                    continue

                else:
                    # LIVE Logic
                    sim_context["active"] = False
                    # Run scanner every 5 iterations (~2.5 min on 30s cycle)
                    if scan_counter % 5 == 0 and bot_config.get("scan_enabled"):
                        asyncio.create_task(ms.run_scan(60))

                    scan_counter += 1
                    
                    # Fetch symbols that have OPEN trades in DB to ensure persistence
                    open_db_symbols = [t.symbol for t in db.query(models.Trade.symbol).filter(models.Trade.status == "OPEN").distinct().all()]
                    
                    # Merge symbols from config + top picks + open trades
                    symbols = set(bot_config["symbols"])
                    symbols.update(open_db_symbols)

                    # Add top scanner picks dynamically
                    top_picks = [r["symbol"] for r in ms.get_top_picks(5)]
                    symbols.update(top_picks)

                    current_prices = {}

                    for symbol in list(symbols):
                        # Filter for Binance mode
                        if bot_config["mode"] == "BINANCE_TESTNET":
                            if not binance_testnet_client.is_valid_symbol(symbol):
                                continue # Skip untradable symbols for this env

                        df = await fetch_ohlcv(symbol, bot_config["timeframe"])
                        if df is None:
                            continue

                        current_prices[symbol] = df["close"].iloc[-1]

                        # Analyze signal
                        signal = compute_composite_signal(symbol, df)
                        
                        el.log(
                            f"[{symbol}] Score={signal['score']} Action={signal['action']}",
                            el.EventType.SIGNAL, 
                            el.EventSeverity.SUCCESS if signal["action"] == "BUY" else el.EventSeverity.INFO,
                            symbol
                        )

                        is_new_target = (symbol in bot_config["symbols"] or symbol in top_picks)
                        if is_new_target and signal["action"] == "BUY":
                            open_count = db.query(models.Trade).filter(models.Trade.status == "OPEN").count()
                            if open_count < bot_config["max_open_positions"]:
                                existing = db.query(models.Trade).filter(
                                    models.Trade.symbol == symbol, models.Trade.status == "OPEN"
                                ).first()
                                if not existing:
                                    await execute_trade(symbol, "BUY", signal, df, db)

                    # Check SL/TP
                    await check_sl_tp(db, current_prices)
                    db.close()
                    
                    # Heartbeat log to show it's actually finishing a cycle
                    el.log(f"Trading Cycle Complete — {len(symbols)} symbols processed", el.EventType.SYSTEM, el.EventSeverity.INFO)
                    await asyncio.sleep(30)

            else:
                if pause_log_counter % 20 == 0:
                    el.log("Bot is paused. Trading engine idling...", el.EventType.SYSTEM, el.EventSeverity.INFO)
                pause_log_counter += 1
                await asyncio.sleep(10)

        except Exception as e:
            el.log(f"Bot loop error: {e}", el.EventType.ERROR, el.EventSeverity.DANGER)
            await asyncio.sleep(10)


# ══════════════════════════════════════════════════════════════════════════════
#  Backtesting Engine
# ══════════════════════════════════════════════════════════════════════════════
async def run_backtest(symbol: str, timeframe: str, start_time_ms: int, initial_balance: float = 10000.0) -> Dict:
    el.log(f"Starting rapid backtest for {symbol} from timestamp {start_time_ms}...", el.EventType.SYSTEM, el.EventSeverity.INFO)
    df_full = await fetch_historical_ohlcv(symbol, timeframe, since_ms=start_time_ms, limit=1000)
    
    if df_full is None or df_full.empty:
        return {"error": "Failed to fetch backtest data or no data available for timeframe"}
        
    warmup = 50
    if len(df_full) <= warmup:
        return {"error": "Not enough data fetched for warmup"}
        
    balance = initial_balance
    trades = []
    open_trade = None
    equity_curve = []
    
    for i in range(warmup, len(df_full)):
        current_idx = df_full.index[i]
        window_df = df_full.iloc[:i+1].copy()
        current_price = window_df["close"].iloc[-1]
        
        # Check Open Trade
        if open_trade:
            # Simplified SL/TP check on Close price
            hit_sl = (open_trade["side"] == "BUY" and current_price <= open_trade["sl"]) or \
                     (open_trade["side"] == "SELL" and current_price >= open_trade["sl"])
            hit_tp = (open_trade["side"] == "BUY" and current_price >= open_trade["tp"]) or \
                     (open_trade["side"] == "SELL" and current_price <= open_trade["tp"])
                     
            if hit_sl or hit_tp:
                pnl = (current_price - open_trade["entry"]) * open_trade["qty"] if open_trade["side"] == "BUY" else (open_trade["entry"] - current_price) * open_trade["qty"]
                balance += (open_trade["entry"] * open_trade["qty"]) + pnl # Return initial cost + pnl
                
                open_trade["exit"] = current_price
                open_trade["pnl"] = pnl
                open_trade["exit_time"] = str(current_idx)
                open_trade["reason"] = "TP" if hit_tp else "SL"
                trades.append(open_trade)
                equity_curve.append({"time": str(current_idx), "balance": balance, "pnl": pnl})
                open_trade = None
                continue
                
        # Generate Signal on historical window
        signal = compute_composite_signal(symbol, window_df)
        action = signal["action"]
        
        if action == "BUY" and not open_trade:
            # We only do LONG in this simulation simplicity for now
            atr = _get_atr(window_df)
            qty = compute_position_size(balance, current_price, atr)
            sl, tp = compute_sl_tp(current_price, "BUY", window_df)
            
            cost = current_price * qty
            if cost <= balance and cost > 0:
                balance -= cost
                open_trade = {
                    "side": "BUY",
                    "entry": current_price,
                    "qty": qty,
                    "sl": sl,
                    "tp": tp,
                    "entry_time": str(current_idx)
                }

    # Close any remaining trade at the end of the simulation
    if open_trade:
        current_price = df_full["close"].iloc[-1]
        pnl = (current_price - open_trade["entry"]) * open_trade["qty"]
        balance += current_price * open_trade["qty"]
        open_trade["exit"] = current_price
        open_trade["pnl"] = pnl
        open_trade["exit_time"] = str(df_full.index[-1])
        open_trade["reason"] = "END_OF_TEST"
        trades.append(open_trade)
        equity_curve.append({"time": str(df_full.index[-1]), "balance": balance, "pnl": pnl})

    wins = [t for t in trades if t["pnl"] > 0]
    total_pnl = sum(t["pnl"] for t in trades)
    win_rate = (len(wins) / len(trades) * 100) if trades else 0
    profit_factor = sum(t["pnl"] for t in wins) / max(abs(sum(t["pnl"] for t in trades if t["pnl"] <= 0)), 1e-8)
    
    el.log(f"Backtest complete for {symbol}. Trades: {len(trades)}, WR: {win_rate:.1f}%, PnL: ${total_pnl:.2f}", el.EventType.SYSTEM, el.EventSeverity.SUCCESS)
    
    return {
        "symbol": symbol,
        "start_time": str(df_full.index[0]),
        "end_time": str(df_full.index[-1]),
        "initial_balance": initial_balance,
        "final_balance": round(balance, 2),
        "total_pnl": round(total_pnl, 2),
        "total_trades": len(trades),
        "win_rate": round(win_rate, 1),
        "profit_factor": round(profit_factor, 2),
        "trades": trades,
        "equity_curve": equity_curve
    }
