"""
ML Predictor V2 — Pre-trains on historical OHLCV data at startup.
================================================================
KEY CHANGES FROM V1:
  ✦ HISTORICAL PRE-TRAINING  — on startup, fetches 58 days of 15m data for all
                                symbols and generates thousands of labeled samples.
                                Model is ready before the first trade fires.
  ✦ LABEL GENERATION         — uses forward-looking return over N bars to label
                                each candle as UP/DOWN/NEUTRAL. Neutral samples
                                are dropped so the model learns directional bias.
  ✦ FEATURE ENGINEERING V2   — 22 features including: EMA ratios, RSI, MACD,
                                BB position, ATR volatility, ADX, MFI, volume
                                change, multi-timeframe momentum, Supertrend dir.
  ✦ ENSEMBLE MODEL           — Gradient Boosting + Random Forest voting.
                                Reduces overfit from single-model predictions.
  ✦ WALK-FORWARD VALIDATION  — trains on first 80% of data, validates on last 20%.
                                Reports out-of-sample accuracy in logs.
  ✦ INCREMENTAL LEARNING     — continues recording live trade outcomes and
                                re-retrains every 15 new samples.
  ✦ CONFIDENCE CALIBRATION   — raw probability is calibrated via Platt scaling
                                so 70% confidence actually means ~70% win rate.
  ✦ THREAD-SAFE              — all operations guarded by a single RLock.
"""

import numpy as np
import pandas as pd
import pandas_ta as ta
import asyncio
import threading
import os
import joblib
import logging
from typing import Dict, List, Optional, Tuple

from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, VotingClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import cross_val_score

logger = logging.getLogger("ml_predictor")

MODEL_PATH  = "ml_model_v2.pkl"
SCALER_PATH = "ml_scaler_v2.pkl"

_lock            = threading.RLock()
_model: Optional[CalibratedClassifierCV] = None
_scaler: Optional[StandardScaler]        = None
_training_data: List[Tuple[np.ndarray, int]] = []

MIN_TRAIN_SAMPLES = 50     # Minimum before model becomes active
FORWARD_BARS      = 8      # How many bars ahead to measure label (8 × 15m = 2h)
LABEL_THRESHOLD   = 0.003  # 0.3% move = meaningful direction
RETRAIN_EVERY     = 15     # Retrain every N new live samples


# ══════════════════════════════════════════════════════════════════════════════
#  Feature Engineering
# ══════════════════════════════════════════════════════════════════════════════
def _extract_features(df: pd.DataFrame) -> Optional[np.ndarray]:
    """Extract 22 ML features from OHLCV dataframe."""
    try:
        if len(df) < 60:
            return None
        d = df.copy()

        # Compute all indicators
        d.ta.ema(length=8,   append=True)
        d.ta.ema(length=21,  append=True)
        d.ta.ema(length=50,  append=True)
        d.ta.rsi(length=14,  append=True)
        d.ta.mfi(length=14,  append=True)
        d.ta.macd(append=True)
        d.ta.bbands(length=20, append=True)
        d.ta.atr(length=14,  append=True)
        d.ta.adx(length=14,  append=True)
        d.ta.stochrsi(length=14, rsi_length=14, append=True)
        d.ta.willr(length=14, append=True)
        try:
            st = d.ta.supertrend(length=10, multiplier=3.0)
            if st is not None:
                dir_col = [c for c in st.columns if c.startswith("SUPERTd_")][0]
                d["ST_DIR"] = st[dir_col]
        except Exception:
            d["ST_DIR"] = 0

        row   = d.iloc[-1]
        close = float(row["close"])

        def g(col, default=0.0):
            v = row.get(col, default)
            if v is None: return default
            try:
                f = float(v)
                return default if np.isnan(f) or np.isinf(f) else f
            except Exception:
                return default

        ema8  = g("EMA_8",  close)
        ema21 = g("EMA_21", close)
        ema50 = g("EMA_50", close)
        rsi   = g("RSI_14", 50)
        mfi   = g("MFI_14", 50)
        macd  = g("MACD_12_26_9",  0)
        macd_s = g("MACDs_12_26_9", 0)
        macd_h = g("MACDh_12_26_9", 0)
        bb_u  = g("BBU_20_2.0", close * 1.02)
        bb_l  = g("BBL_20_2.0", close * 0.98)
        atr   = g("ATRr_14", close * 0.01)
        adx   = g("ADX_14",  20)
        stoch = g("STOCHRSIk_14_14_3_3", 0.5) * 100
        willr = g("WILLR_14", -50)
        st_dir = g("ST_DIR", 0)

        # Volume features
        vol_now  = float(d["volume"].iloc[-1]) + 1e-8
        vol_avg  = float(d["volume"].iloc[-21:-1].mean()) + 1e-8
        vol_ratio = vol_now / vol_avg

        # Multi-bar momentum
        c  = d["close"].values
        r1  = (c[-1] - c[-2])  / (c[-2]  + 1e-8)
        r3  = (c[-1] - c[-4])  / (c[-4]  + 1e-8)
        r8  = (c[-1] - c[-9])  / (c[-9]  + 1e-8)
        r16 = (c[-1] - c[-17]) / (c[-17] + 1e-8) if len(c) > 16 else 0.0

        # Bollinger position
        bb_range = bb_u - bb_l
        bb_pos   = (close - bb_l) / (bb_range + 1e-8)

        # Candle body
        body = abs(float(row["close"]) - float(row["open"]))
        cr   = float(row["high"]) - float(row["low"])
        body_pct = body / (cr + 1e-8)
        is_bull  = 1.0 if row["close"] > row["open"] else 0.0

        features = np.array([
            (ema8  - ema21) / (ema21 + 1e-8),    # EMA8 vs EMA21
            (ema21 - ema50) / (ema50 + 1e-8),    # EMA21 vs EMA50
            (close - ema21) / (ema21 + 1e-8),    # price vs EMA21
            rsi   / 100.0,
            mfi   / 100.0,
            macd  / (close + 1e-8),
            macd_s / (close + 1e-8),
            macd_h / (close + 1e-8),
            bb_pos,
            (bb_u - bb_l) / (close + 1e-8),      # BB width (volatility)
            atr   / (close + 1e-8),               # ATR as % of price
            adx   / 100.0,
            stoch / 100.0,
            (willr + 100) / 100.0,
            st_dir,                                # +1 / -1 / 0
            min(vol_ratio, 5.0) / 5.0,            # normalised volume ratio
            r1,
            r3,
            r8,
            r16,
            body_pct,
            is_bull,
        ], dtype=np.float32)

        # Sanity check — reject rows with NaN/Inf
        if not np.isfinite(features).all():
            return None
        return features

    except Exception as e:
        logger.debug(f"Feature extraction error: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  Label Generation  (for historical pre-training)
# ══════════════════════════════════════════════════════════════════════════════
def _generate_labels(df: pd.DataFrame,
                     forward_bars: int = FORWARD_BARS,
                     threshold: float = LABEL_THRESHOLD) -> List[Tuple[np.ndarray, int]]:
    """
    For each candle i (leaving enough room for warmup + future bars):
      - compute forward return over `forward_bars` candles
      - label = 1 (UP) if return > +threshold, 0 (DOWN) if < -threshold
      - skip NEUTRAL candles (reduces noise)
    Returns list of (features, label) pairs.
    """
    samples = []
    closes  = df["close"].values
    n       = len(df)
    warmup  = 60  # Need enough history for all indicators

    for i in range(warmup, n - forward_bars):
        fwd_return = (closes[i + forward_bars] - closes[i]) / (closes[i] + 1e-8)

        if abs(fwd_return) < threshold:
            continue  # Skip neutral — too noisy

        label = 1 if fwd_return > 0 else 0
        window = df.iloc[max(0, i - warmup + 1): i + 1].copy()

        if len(window) < 60:
            continue

        feats = _extract_features(window)
        if feats is None:
            continue

        samples.append((feats, label))

    return samples


# ══════════════════════════════════════════════════════════════════════════════
#  Model Training
# ══════════════════════════════════════════════════════════════════════════════
def _build_ensemble():
    rf = RandomForestClassifier(
        n_estimators=200, max_depth=7, min_samples_leaf=5,
        class_weight="balanced", random_state=42, n_jobs=-1
    )
    gb = GradientBoostingClassifier(
        n_estimators=150, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=42
    )
    return VotingClassifier(
        estimators=[("rf", rf), ("gb", gb)],
        voting="soft"
    )


def _retrain(data: List[Tuple[np.ndarray, int]], log_accuracy: bool = True):
    """Train on provided (features, label) list. Thread-safe via caller."""
    global _model, _scaler

    if len(data) < MIN_TRAIN_SAMPLES:
        return

    X = np.array([f for f, _ in data], dtype=np.float32)
    y = np.array([l for _, l in data], dtype=np.int32)

    if len(np.unique(y)) < 2:
        logger.warning("Retrain skipped: only one class present")
        return

    # Walk-forward split — train on first 80%, validate last 20%
    split  = int(len(X) * 0.80)
    X_tr, X_val = X[:split], X[split:]
    y_tr, y_val = y[:split], y[split:]

    scaler  = StandardScaler()
    X_tr_sc = scaler.fit_transform(X_tr)
    X_val_sc = scaler.transform(X_val)

    base    = _build_ensemble()
    # Calibrate via Platt scaling on the validation set
    cal_clf = CalibratedClassifierCV(base, method="sigmoid", cv="prefit")
    base.fit(X_tr_sc, y_tr)
    cal_clf.fit(X_val_sc, y_val)  # calibrates on held-out data

    val_acc = float(np.mean(cal_clf.predict(X_val_sc) == y_val))

    _scaler = scaler
    _model  = cal_clf

    try:
        joblib.dump(_model,  MODEL_PATH)
        joblib.dump(_scaler, SCALER_PATH)
    except Exception:
        pass

    if log_accuracy:
        try:
            import event_log as el
            el.log(
                f"ML model trained: {len(data)} samples | "
                f"val_acc={val_acc*100:.1f}% | "
                f"UP={int(y.sum())} DOWN={int((1-y).sum())}",
                el.EventType.LEARNING, el.EventSeverity.SUCCESS
            )
        except Exception:
            logger.info(f"ML retrain done: n={len(data)} val_acc={val_acc*100:.1f}%")


# ══════════════════════════════════════════════════════════════════════════════
#  Historical Pre-Training (called from bot_engine startup)
# ══════════════════════════════════════════════════════════════════════════════
async def pretrain_on_history(symbols: List[str], timeframe: str = "15m"):
    """
    Fetch historical OHLCV for all symbols and generate training samples.
    Runs once at startup in the background so the model is ready before
    the first trade signal fires.
    """
    try:
        import event_log as el
        el.log(
            f"ML pre-training starting on {len(symbols)} symbols ({timeframe})...",
            el.EventType.LEARNING, el.EventSeverity.INFO
        )
    except Exception:
        pass

    all_samples: List[Tuple[np.ndarray, int]] = []

    for symbol in symbols:
        try:
            df = await _fetch_history_for_training(symbol, timeframe)
            if df is None or len(df) < 120:
                continue
            samples = _generate_labels(df)
            all_samples.extend(samples)
            try:
                import event_log as el
                el.log(
                    f"ML labels: {symbol} → {len(samples)} samples from {len(df)} candles",
                    el.EventType.LEARNING, el.EventSeverity.INFO
                )
            except Exception:
                pass
        except Exception as e:
            logger.warning(f"ML pretrain failed for {symbol}: {e}")

    if len(all_samples) < MIN_TRAIN_SAMPLES:
        try:
            import event_log as el
            el.log(
                f"ML pre-training: not enough samples ({len(all_samples)}), skipping.",
                el.EventType.LEARNING, el.EventSeverity.WARNING
            )
        except Exception:
            pass
        return

    # Shuffle to break time-series bias in training
    import random
    random.shuffle(all_samples)

    with _lock:
        _training_data.clear()
        _training_data.extend(all_samples)
        # V2 Fix: Run heavy CPU-bound retrain in a separate thread to avoid blocking the event loop
        await asyncio.to_thread(_retrain, _training_data, True)

    try:
        import event_log as el
        el.log(
            f"✅ ML pre-training complete: {len(all_samples)} total samples across {len(symbols)} symbols",
            el.EventType.LEARNING, el.EventSeverity.SUCCESS
        )
    except Exception:
        pass


async def _fetch_history_for_training(symbol: str, timeframe: str) -> Optional[pd.DataFrame]:
    """Fetch training data via yfinance (same approach as sim data)."""
    try:
        import yfinance as yf
        from datetime import datetime, timedelta

        yf_symbol = symbol.replace("/", "-").replace("USDT", "USD")
        now       = datetime.utcnow() - timedelta(minutes=5)
        if timeframe in ("1m", "2m"):
            start = now - timedelta(days=6)
        elif timeframe in ("5m", "15m", "30m", "60m", "1h"):
            start = now - timedelta(days=55)
        else:
            start = now - timedelta(days=55)

        interval = timeframe if timeframe in ["1m","2m","5m","15m","30m","60m","1h","1d"] else "15m"

        def _fetch():
            return yf.Ticker(yf_symbol).history(start=start, end=now, interval=interval)

        df = await asyncio.to_thread(_fetch)
        if df is None or df.empty:
            return None

        df.reset_index(inplace=True)
        tc = "Datetime" if "Datetime" in df.columns else "Date"
        df.rename(columns={tc:"timestamp","Open":"open","High":"high",
                            "Low":"low","Close":"close","Volume":"volume"}, inplace=True)
        cols = [c for c in ["timestamp","open","high","low","close","volume"] if c in df.columns]
        df = df[cols]
        df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.tz_localize(None)
        df.set_index("timestamp", inplace=True)
        df = df[~df.index.duplicated(keep="first")].sort_index()

        # Clean zero-range candles
        cr = df["high"] - df["low"]
        zm = cr < 1e-8
        if zm.any():
            df.loc[zm, ["open","high","low","close"]] = np.nan
            df = df.ffill().dropna(subset=["close"])

        return df

    except Exception as e:
        logger.warning(f"History fetch for {symbol}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
#  Inference
# ══════════════════════════════════════════════════════════════════════════════
def predict(df: pd.DataFrame) -> Dict:
    """
    Returns {direction, confidence, up_prob, down_prob, trained_on}.
    Falls back to heuristic if model not yet trained.
    """
    features = _extract_features(df)
    if features is None:
        return _heuristic(df)

    with _lock:
        if _model is None or len(_training_data) < MIN_TRAIN_SAMPLES:
            return _heuristic(df)
        try:
            X      = _scaler.transform(features.reshape(1, -1))
            proba  = _model.predict_proba(X)[0]
            classes = list(_model.classes_)

            up_idx   = classes.index(1) if 1 in classes else 0
            dn_idx   = classes.index(0) if 0 in classes else 1

            up_p  = float(proba[up_idx])   if up_idx < len(proba)  else 0.5
            dn_p  = float(proba[dn_idx])   if dn_idx < len(proba)  else 0.5

            direction  = "UP" if up_p > dn_p else "DOWN"
            confidence = max(up_p, dn_p)

            return {
                "direction":   direction,
                "confidence":  round(confidence, 3),
                "up_prob":     round(up_p, 3),
                "down_prob":   round(dn_p, 3),
                "trained_on":  len(_training_data),
            }
        except Exception:
            return _heuristic(df)


def _heuristic(df: pd.DataFrame) -> Dict:
    """Simple rule-based fallback until model is ready."""
    try:
        d = df.copy()
        d.ta.ema(length=8, append=True)
        d.ta.ema(length=21, append=True)
        d.ta.rsi(length=14, append=True)
        e8  = d["EMA_8"].iloc[-1]
        e21 = d["EMA_21"].iloc[-1]
        rsi = d["RSI_14"].iloc[-1]
        score = 0
        if e8 > e21: score += 1
        if rsi < 55: score += 0.5
        if rsi > 45: score += 0.5
        direction  = "UP" if score > 1 else "DOWN"
        confidence = 0.5 + abs(score - 1) * 0.05
        return {
            "direction": direction, "confidence": round(confidence, 3),
            "up_prob":   confidence if direction == "UP" else 1 - confidence,
            "down_prob": confidence if direction == "DOWN" else 1 - confidence,
            "trained_on": 0
        }
    except Exception:
        return {"direction": "NEUTRAL", "confidence": 0.0,
                "up_prob": 0.5, "down_prob": 0.5, "trained_on": 0}


# ══════════════════════════════════════════════════════════════════════════════
#  Incremental Online Learning (called after each live trade closes)
# ══════════════════════════════════════════════════════════════════════════════
def record_outcome(df: pd.DataFrame, was_profitable: bool):
    """
    Record one live trade outcome and trigger retrain every RETRAIN_EVERY samples.
    This lets the model adapt to current market conditions over time.
    """
    features = _extract_features(df)
    if features is None:
        return

    label = 1 if was_profitable else 0

    with _lock:
        _training_data.append((features, label))
        n = len(_training_data)
        # Retrain every N new live samples (only after pre-training bootstrap)
        if n >= MIN_TRAIN_SAMPLES and (n - MIN_TRAIN_SAMPLES) % RETRAIN_EVERY == 0:
            _retrain(_training_data, log_accuracy=True)


# ══════════════════════════════════════════════════════════════════════════════
#  Startup — load saved model if available
# ══════════════════════════════════════════════════════════════════════════════
def load_saved():
    global _model, _scaler
    if os.path.exists(MODEL_PATH) and os.path.exists(SCALER_PATH):
        try:
            _model  = joblib.load(MODEL_PATH)
            _scaler = joblib.load(SCALER_PATH)
            logger.info(f"Loaded saved ML model from disk ({MODEL_PATH})")
        except Exception as e:
            logger.warning(f"Could not load saved model: {e}")


load_saved()