# TradeBot: Binance Futures Testnet Trading Bot

TradeBot is a Python-based trading application designed for the Binance Futures Testnet (USDT-M). It features a structured API layer, a robust CLI for manual orders, and an automated multi-strategy bot engine with a real-time React dashboard.

## Task Submission Details
- **Candidate Objective**: Build a simplified trading bot for Binance Futures Testnet.
- **Key Deliverables**: Public repository, Market/Limit order support, CLI interface, and structured logging.

## Key Features

- **Binance Futures Testnet Integration**: Real-time order placement (Market & Limit) on USDT-M futures.
- **Dual Mode**: Switch between Paper Trading (internal simulation) and Binance Testnet in one click.
- **Manual Trade Execution (USD-based)**: Execute trades by specifying the USD amount. The bot handles leverage (default 20x) and quantity calculations automatically to match Binance requirements.
- **One-Click Manual Closure**: Close any open position directly from the dashboard with the new "CLOSE" button.
- **Robust CLI**: Complete command-line interface for placing orders and validating inputs.
- **Structured Logging**: All API requests, responses, and errors are logged to `backend/logs/tradebot.log`.
- **AI-Powered Insights**: (Bonus) Multi-strategy signal fusion and ML-based directional bias.

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

## Setup & Execution

### 1. Prerequisites
- Python 3.9+
- Binance Futures Testnet API Key & Secret ([Register here](https://testnet.binancefuture.com))

### 2. Installation
```bash
git clone https://github.com/priyanshugaurav/tradingBot.git
cd tradingBot/backend
pip install -r requirements.txt
```

### 3. Configuration
Create a `.env` file in the `backend/` directory:
```env
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret
```

### 4. Running the Bot
#### CLI Interface (Task Requirement)
```bash
# Place a Market BUY order
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.01

# Place a Limit SELL order
python cli.py place --symbol ETHUSDT --side SELL --type LIMIT --qty 0.1 --price 3500
```

### 5. GUI Mode Switching (New)
You can now shift between simulation and live testnet trading directly from the dashboard:
1. Locate the **Mode Toggle** in the top header.
2. Select **PAPER** for risk-free local simulation using the internal engine.
3. Select **BINANCE** to connect to the Binance Futures Testnet.
   - The bot will fetch your real Testnet balance and display it as **Net: $X.XX**.
   - All orders (Market/Limit) will be routed to the Binance Testnet API.
   - Ensure your `.env` is configured for this mode to work.

---

## Assumptions
- Uses USDT-M (USDT-margined) futures exclusively.
- Quantity is specified in base asset units (e.g., BTC, ETH).
- Logging follows the structured format requested in the task.

---

## Disclaimer
Educational purpose only. Trade at your own risk.
