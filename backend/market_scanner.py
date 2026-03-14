"""
Market Scanner — Scans top 100+ USDT pairs on Binance.
Ranks them by opportunity score and returns best picks for trading.
"""
import ccxt
import pandas as pd
import pandas_ta as ta
import asyncio
import threading
from typing import List, Dict, Optional
from datetime import datetime
import event_log as el


exchange = ccxt.binance({
    'enableRateLimit': True,
    'options': {'defaultType': 'future'}
})

_scan_results: List[Dict] = []
_last_scan: Optional[str] = None
_lock = threading.Lock()


async def get_top_symbols(limit: int = 120) -> List[str]:
    """Fetch top USDT pairs by 24h volume. Offloaded to thread."""
    try:
        tickers = await asyncio.to_thread(exchange.fetch_tickers)
        # Filters for USDT pairs that are active
        usdt_pairs = []
        for sym, data in tickers.items():
            if sym.endswith("/USDT") or sym.endswith(":USDT"):
                quote_vol = data.get("quoteVolume")
                if quote_vol is not None:
                    vol = float(quote_vol)
                else:
                    base_vol = data.get("baseVolume") or 0
                    last_price = data.get("last") or 0
                    vol = float(base_vol) * float(last_price)
                
                if vol > 0:
                    usdt_pairs.append((sym, vol))
                    
        usdt_pairs.sort(key=lambda x: x[1], reverse=True)
        # Exclude stablecoins and weird test symbols
        stables = {"BUSD/USDT", "USDC/USDT", "TUSD/USDT", "DAI/USDT", "FDUSD/USDT"}
        return [sym for sym, _ in usdt_pairs if sym not in stables][:limit]
    except Exception as e:
        el.log(f"Scanner error fetching symbols: {e}", el.EventType.ERROR, el.EventSeverity.DANGER)
        return ["BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT"]


def score_symbol(symbol: str, timeframe: str = "15m") -> Optional[Dict]:
    """
    Score a symbol 0-100 based on trend strength, momentum, volatility.
    """
    try:
        data = exchange.fetch_ohlcv(symbol, timeframe, limit=60)
        if not data or len(data) < 40:
            return None

        df = pd.DataFrame(data, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)

        df.ta.ema(length=9,  append=True)
        df.ta.ema(length=21, append=True)
        df.ta.rsi(length=14, append=True)
        df.ta.macd(append=True)
        df.ta.atr(length=14, append=True)
        df.ta.adx(length=14, append=True)
        df.ta.mfi(length=14, append=True)
        df.ta.stochrsi(length=14, rsi_length=14, append=True)
        df.ta.willr(length=14, append=True)

        latest   = df.iloc[-1]
        close    = latest["close"]
        ema9     = latest.get("EMA_9", close)
        ema21    = latest.get("EMA_21", close)
        rsi      = latest.get("RSI_14", 50)
        macd_h   = latest.get("MACDh_12_26_9", 0)
        adx      = latest.get("ADX_14", 0)
        atr      = latest.get("ATRr_14", 0)
        mfi      = latest.get("MFI_14", 50)
        stochrsi = latest.get("STOCHRSIk_14_14_3_3", 50) * 100
        willr    = latest.get("WILLR_14", -50)

        # Price change metrics
        change_1h  = (close - df["close"].iloc[-5])  / df["close"].iloc[-5]  * 100
        change_4h  = (close - df["close"].iloc[-16]) / df["close"].iloc[-16] * 100
        change_24h = (close - df["close"].iloc[-max(len(df)-1,0)]) / df["close"].iloc[-max(len(df)-1,0)] * 100

        vol_avg = df["volume"].iloc[-20:-1].mean()
        vol_now = latest["volume"]
        vol_ratio = vol_now / (vol_avg + 1e-8)

        # --- Score calculation (0-100) ---
        score = 50  # Neutral base

        # Trend score (EMA alignment)
        if ema9 > ema21: score += 10
        else: score -= 10

        # RSI (favor non-extreme readings)
        if 40 < rsi < 65: score += 10
        elif rsi < 30: score += 15   # Oversold bounce potential
        elif rsi > 75: score -= 15

        # Money Flow Index (Volume-weighted RSI)
        if mfi < 20: score += 15
        elif mfi > 80: score -= 15

        # Stochastic RSI
        if stochrsi < 20: score += 10
        elif stochrsi > 80: score -= 10

        # Williams %R
        if willr < -80: score += 10
        elif willr > -20: score -= 10

        # Momentum (MACD histogram direction)
        prev_macd_h = df["MACDh_12_26_9"].iloc[-2] if "MACDh_12_26_9" in df else 0
        if macd_h > 0 and macd_h > prev_macd_h: score += 10
        elif macd_h < 0 and macd_h < prev_macd_h: score -= 10

        # Trend strength (ADX)
        if adx > 25: score += 10
        elif adx < 15: score -= 5

        # Volatility bonus (need movement to make money)
        atr_pct = atr / close * 100
        if 0.5 < atr_pct < 3: score += 5
        elif atr_pct > 5: score -= 5

        # Volume surge is good
        if vol_ratio > 1.5: score += 10
        elif vol_ratio < 0.5: score -= 5

        score = max(0, min(100, score))

        # Determine overall trend
        if ema9 > ema21 and rsi > 50:
            trend = "BULLISH"
        elif ema9 < ema21 and rsi < 50:
            trend = "BEARISH"
        else:
            trend = "NEUTRAL"

        return {
            "symbol": symbol,
            "trend": trend,
            "score": round(score, 1),
            "price": close,
            "change_1h": round(change_1h, 2),
            "change_24h": round(change_24h, 2),
            "rsi": round(rsi, 1),
            "adx": round(adx, 1),
            "mfi": round(mfi, 1),
            "stochrsi": round(stochrsi, 1),
            "willr": round(willr, 1),
            "volume_ratio": round(vol_ratio, 2),
            "atr_pct": round(atr_pct, 2),
            "scanned_at": datetime.utcnow().isoformat() + "Z"
        }
    except Exception:
        return None


async def run_scan(top_n: int = 100):
    """Parallel scan of all top symbols using worker threads for sync I/O."""
    global _scan_results, _last_scan
    el.log(f"Market scanner starting — scanning top {top_n} coins...", el.EventType.SCANNER, el.EventSeverity.INFO)
    
    symbols = await get_top_symbols(top_n)
    
    # Use a semaphore to avoid overloading the exchange/system with too many threads/requests at once
    sem = asyncio.Semaphore(15) 

    async def _scan_one(sym):
        async with sem:
            # score_symbol is synchronous (ccxt fetch_ohlcv is sync)
            return await asyncio.to_thread(score_symbol, sym)

    tasks = [_scan_one(sym) for sym in symbols]
    raw_results = await asyncio.gather(*tasks)
    
    results = [r for r in raw_results if r is not None]
    results.sort(key=lambda x: x["score"], reverse=True)

    with _lock:
        _scan_results = results
        _last_scan = datetime.utcnow().isoformat() + "Z"

    el.log(
        f"Scan complete — {len(results)} pairs analyzed. Top pick: {results[0]['symbol'] if results else 'N/A'} (score {results[0]['score'] if results else 0})",
        el.EventType.SCANNER, el.EventSeverity.SUCCESS
    )
    return results


def get_results() -> List[Dict]:
    with _lock:
        return list(_scan_results)


def get_top_picks(n: int = 10) -> List[Dict]:
    with _lock:
        return _scan_results[:n]
