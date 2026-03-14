"""
Pattern Detector — Identifies classic chart patterns from OHLCV data.
Returns a list of detected patterns with confidence scores.
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Optional


def _local_highs(series: pd.Series, order: int = 3) -> np.ndarray:
    from scipy.signal import argrelextrema
    return argrelextrema(series.values, np.greater_equal, order=order)[0]


def _local_lows(series: pd.Series, order: int = 3) -> np.ndarray:
    from scipy.signal import argrelextrema
    return argrelextrema(series.values, np.less_equal, order=order)[0]


def detect_patterns(df: pd.DataFrame) -> List[Dict]:
    """
    Detects chart patterns from OHLCV DataFrame.
    Returns list of: {name, type, confidence, description}
    """
    patterns = []
    if df is None or len(df) < 30:
        return patterns

    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    vol   = df["volume"]

    highs_idx = _local_highs(high, order=3)
    lows_idx  = _local_lows(low, order=3)

    # 1. Bull Flag — sharp rise then sideways/slight consolidation
    try:
        last_20 = close.iloc[-20:]
        pole_rise = (close.iloc[-14] - close.iloc[-20]) / close.iloc[-20]
        flag_range = last_20.iloc[-6:].max() - last_20.iloc[-6:].min()
        flag_range_pct = flag_range / close.iloc[-20]
        if pole_rise > 0.025 and flag_range_pct < 0.012:
            conf = min(0.9, 0.5 + pole_rise * 5)
            patterns.append({
                "name": "Bull Flag",
                "type": "bullish",
                "confidence": round(conf, 2),
                "description": f"Sharp {round(pole_rise*100,1)}% pole rise with tight consolidation"
            })
    except Exception:
        pass

    # 2. Bear Flag
    try:
        pole_drop = (close.iloc[-20] - close.iloc[-14]) / close.iloc[-20]
        flag_range_pct = (close.iloc[-6:].max() - close.iloc[-6:].min()) / close.iloc[-14]
        if pole_drop > 0.025 and flag_range_pct < 0.012:
            conf = min(0.9, 0.5 + pole_drop * 5)
            patterns.append({
                "name": "Bear Flag",
                "type": "bearish",
                "confidence": round(conf, 2),
                "description": f"Sharp {round(pole_drop*100,1)}% drop with tight consolidation"
            })
    except Exception:
        pass

    # 3. Double Top
    try:
        if len(highs_idx) >= 2:
            h1 = high.iloc[highs_idx[-2]]
            h2 = high.iloc[highs_idx[-1]]
            if abs(h1 - h2) / h1 < 0.015 and h1 > close.iloc[-1]:
                patterns.append({
                    "name": "Double Top",
                    "type": "bearish",
                    "confidence": round(0.72, 2),
                    "description": f"Two peaks near ${h1:.2f}, potential reversal"
                })
    except Exception:
        pass

    # 4. Double Bottom
    try:
        if len(lows_idx) >= 2:
            l1 = low.iloc[lows_idx[-2]]
            l2 = low.iloc[lows_idx[-1]]
            if abs(l1 - l2) / l1 < 0.015 and l1 < close.iloc[-1]:
                patterns.append({
                    "name": "Double Bottom",
                    "type": "bullish",
                    "confidence": round(0.74, 2),
                    "description": f"Two bottoms near ${l1:.2f}, potential reversal up"
                })
    except Exception:
        pass

    # 5. Ascending Triangle
    try:
        if len(highs_idx) >= 3 and len(lows_idx) >= 3:
            top_prices = high.iloc[highs_idx[-3:]]
            bot_prices = low.iloc[lows_idx[-3:]]
            resistance_flat = top_prices.std() / top_prices.mean() < 0.008
            support_rising  = bot_prices.is_monotonic_increasing
            if resistance_flat and support_rising:
                patterns.append({
                    "name": "Ascending Triangle",
                    "type": "bullish",
                    "confidence": 0.78,
                    "description": "Flat resistance + rising support, bullish breakout expected"
                })
    except Exception:
        pass

    # 6. Descending Triangle
    try:
        if len(highs_idx) >= 3 and len(lows_idx) >= 3:
            top_prices = high.iloc[highs_idx[-3:]]
            bot_prices = low.iloc[lows_idx[-3:]]
            support_flat     = bot_prices.std() / bot_prices.mean() < 0.008
            resistance_falling = top_prices.is_monotonic_decreasing
            if support_flat and resistance_falling:
                patterns.append({
                    "name": "Descending Triangle",
                    "type": "bearish",
                    "confidence": 0.76,
                    "description": "Flat support + falling resistance, bearish breakout expected"
                })
    except Exception:
        pass

    # 7. Volume surge — unusual activity
    try:
        avg_vol = vol.iloc[-20:-1].mean()
        cur_vol = vol.iloc[-1]
        if cur_vol > avg_vol * 2.5:
            direction = "bullish" if close.iloc[-1] > close.iloc[-2] else "bearish"
            patterns.append({
                "name": "Volume Surge",
                "type": direction,
                "confidence": min(0.85, round((cur_vol / avg_vol) * 0.2, 2)),
                "description": f"Volume {round(cur_vol/avg_vol, 1)}x above average — strong momentum"
            })
    except Exception:
        pass

    # 8. Oversold Bounce
    try:
        import pandas_ta as ta
        rsi_v = df.ta.rsi(length=14).iloc[-1]
        if rsi_v < 30:
            patterns.append({
                "name": "Oversold",
                "type": "bullish",
                "confidence": round(0.5 + (30 - rsi_v) * 0.015, 2),
                "description": f"RSI at {rsi_v:.1f} — potential bounce incoming"
            })
        elif rsi_v > 70:
            patterns.append({
                "name": "Overbought",
                "type": "bearish",
                "confidence": round(0.5 + (rsi_v - 70) * 0.015, 2),
                "description": f"RSI at {rsi_v:.1f} — potential pullback incoming"
            })
    except Exception:
        pass

    return patterns


def get_dominant_pattern(patterns: List[Dict]) -> Optional[Dict]:
    if not patterns:
        return None
    return max(patterns, key=lambda p: p["confidence"])
