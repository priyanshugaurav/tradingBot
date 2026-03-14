# TradeBot: Advanced Multi-Strategy AI Trading Bot

TradeBot is a sophisticated trading platform that combines traditional technical analysis with modern machine learning to automate cryptocurrency trading. It features a high-performance Python backend and a real-time React dashboard.

![TradeBot Dashboard](https://github.com/priyanshugaurav/tradingBot/raw/main/screenshots/dashboard_main.png)

## Key Features

- **Multi-Strategy Fusion**: Combines 8+ technical indicators into a single composite signal.
- **AI-Powered Predictions**: Uses a Gradient Boosting + Random Forest ensemble for directional bias.
- **Market Scanner**: Automatically scans top 100+ USDT pairs on Binance to find high-probability setups.
- **Risk Management**: ATR-based position sizing, automated SL/TP, and intelligent Trailing Stop-Loss.
- **Paper Trading & Simulation**: Test strategies in real-time or via accelerated historical simulations.
- **Real-Time Dashboard**: Beautiful glassmorphic UI with WebSocket-driven live updates.

---

## Backend Engine & Strategies

The backend is built with **FastAPI** and **SQLAlchemy**, featuring a modular bot engine (`bot_engine.py`) that handles signal generation and trade execution.

### Technical Strategies
The bot calculates composite scores (-100 to +100) using weighted inputs from:
- **EMA Crossover**: 9/21/50 EMA alignment and golden/death crosses.
- **Advanced Oscillators**: Combined RSI, MFI, Stochastic RSI, and Williams %R.
- **MACD**: Trend momentum and histogram direction.
- **Bollinger Bands**: Volatility-adjusted price positioning.
- **Ichimoku Cloud**: Trend confirmation using Kumo cloud and TK crosses.
- **Supertrend**: Volatility-based trend following.
- **VWAP**: Volume-weighted average price pullbacks.
- **Volume Surge**: Detection of institutional activity via relative volume analysis.

### Signal Fusion
Signals are normalized and combined with **Pattern Detection** (Head & Shoulders, Double Tops/Bottoms, etc.) to produce a final "Action" (BUY/SELL/HOLD).

---

## Machine Learning (ML)

The `ml_predictor.py` module implements a sophisticated learning pipeline:

- **Ensemble Model**: Combines **Random Forest** and **Gradient Boosting** classifiers with soft voting.
- **Historical Pre-training**: On startup, the model fetches 50+ days of historical data via `yfinance` to bootstrap its intelligence.
- **Feature Engineering**: Extracts 22 features per candle, including oscillator ratios, multi-timeframe momentum, and volatility metrics.
- **Incremental Learning**: The model continuously learns from every closed trade, adapting its weights based on real market outcomes.
- **Confidence Calibration**: Probabilities are calibrated via Platt scaling to ensure reliability.

---

## Market Scanner

The `market_scanner.py` performs high-speed parallel analysis:
- **Scope**: Monitors the top 100-120 high-volume USDT pairs on Binance.
- **Ranking**: Each pair is assigned an "Opportunity Score" based on trend strength (ADX), momentum, and oversold/overbought conditions.
- **Dynamic Selection**: The bot automatically adds top-ranking coins to its active watchlist.

---

## Frontend Architecture

A premium, responsive dashboard built with **React**, **Vite**, and **Tailwind CSS**.

- **Mission Control**: Live event console with real-time WebSocket reporting.
- **AI Predictions**: Visual breakdown of ML confidence and detected chart patterns.
- **Scanner Panel**: Real-time ranking and filtering of market opportunities.
- **Trade Management**: Manual and automated trade tracking with PNL visualization.
- **Strategy Control**: Real-time adjustment of strategy weights and bot parameters.

---

## Setup & Installation

### Backend
1. Navigate to `/backend`:
   ```bash
   pip install -r requirements.txt
   python main.py
   ```
2. The API will run on `http://localhost:8000`.

### Frontend
1. Navigate to `/frontend`:
   ```bash
   npm install
   npm run dev
   ```
2. Open `http://localhost:5173` in your browser.

---

## Disclaimer
This software is for educational purposes only. Do not trade with real money unless you fully understand the risks involved. The authors are not responsible for any financial losses.
