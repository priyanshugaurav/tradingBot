# 🤖 TradeBot: Advanced Binance Futures Trading Suite

> [!NOTE]
> This is a small version of my own trading bot with almost every feature, including Binance demo account connection and paper trading capabilities.

TradeBot is a high-performance trading ecosystem designed for the **Binance Futures Testnet (USDT-M)**. It combines institutional-grade market analysis, machine learning directional bias, and a premium real-time dashboard to provide a complete trading solution.

---

## 🚀 Quick Start Guide (Step-by-Step)

### 1. Prerequisites
- **Python 3.9+**
- **Node.js 16+** (for the Dashboard)
- **Binance Futures Testnet Account** ([Join here](https://testnet.binancefuture.com/))

### 2. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Environment Configuration
Create a `.env` file in the `backend/` directory:
```env
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_api_secret
```

### 4. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### 5. Launch
Start the backend server:
```bash
cd backend
uvicorn main:app --reload
```
Now visit `http://localhost:5173` to see your mission control.

---

## 🖥️ The Mission Control (GUI Dashboard)

Our premium React dashboard provides real-time oversight and total control over your trading operations.

- **Market Scanner**: High-speed parallel analysis of 120+ USDT pairs. It ranks coins by "Opportunity Score" using RSI, ADX, and Volume Surge.
- **AI Pattern Library**: Real-time detection of chart patterns (Head & Shoulders, Flags, etc.) combined with Ensemble ML predictions.
- **Active Trade Management**: View all open positions with live PNL tracking.
- **One-Click Manual Exit**: A new **"CLOSE"** button on every trade card allows for immediate, `reduce-only` exits on Binance.
- **Strategy Weights**: Dynamically adjust the influence of different technical indicators (EMA, MACD, etc.) through the UI.

---

## ⌨️ Command Line Interface (CLI)

For power users, the `cli.py` provides a robust interface for manual orders and environment validation.

### Position Management
```bash
# Place a leveraged Market BUY
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --qty 0.01

# Place a precise Limit SELL
python cli.py place --symbol ETHUSDT --side SELL --type LIMIT --qty 0.1 --price 3500
```

### System Health
```bash
# Verify Binance Connectivity and Balance
python cli.py balance
```

---

## 🌩️ Binance Testnet & Paper Trading

TradeBot features a seamless dual-mode engine.

1. **PAPER Mode**: Uses a local simulation engine. Ideal for testing strategies without risk.
2. **BINANCE Mode**: Connects directly to the **Binance Futures Testnet**.
   - **Leverage Awareness**: The system defaults to **20x leverage**. 
   - **USD-Based Execution**: When you trade from the GUI, you specify the **USD amount**. The bot automatically calculates the required quantity and leverage parameters for Binance.
   - **Reduce-Only Guards**: Manual and automated closures use `reduce-only` orders to prevent accidental position reversals.

---

## 🧠 Advanced Technology Stack

- **Core Engine**: Python, FastAPI, CCXT.
- **Machine Learning**: Random Forest & Gradient Boosting Ensemble for directional probability.
- **Database**: SQLAlchemy with SQLite for trade persistence.
- **Frontend**: React, Vite, Tailwind CSS, Lucide Icons.
- **Real-time**: High-frequency OHLCV fetching and event-based logging.

---

## 📜 Disclaimer
This software is for educational and research purposes only. Cryptocurrency trading involves high risk. **Trade at your own risk.**
