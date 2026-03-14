"""
FastAPI Main V2 — Full API with WebSocket live stream for dashboard
"""
import asyncio
import json
import queue
from datetime import datetime, timedelta
from typing import List, Optional
import random

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import database, models, schemas
import bot_engine
import event_log as el
import market_scanner as ms

# ── Initialize DB ─────────────────────────────────────────────────────────────
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(title="TradeBot API V2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Startup ───────────────────────────────────────────────────────────────────
@app.on_event("startup")
async def startup_event():
    db = database.SessionLocal()
    portfolio = db.query(models.Portfolio).first()
    if not portfolio:
        db.add(models.Portfolio(balance=10000.0))
        db.commit()
    db.close()
    el.log("TradeBot started — paper trading engine ready", el.EventType.SYSTEM, el.EventSeverity.SUCCESS)
    asyncio.create_task(bot_engine.trade_loop())


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/")
def root(): return {"status": "ok", "version": "2.0"}


# ── Portfolio ─────────────────────────────────────────────────────────────────
@app.get("/api/portfolio", response_model=schemas.Portfolio)
def get_portfolio(db: Session = Depends(database.get_db)):
    p = db.query(models.Portfolio).first()
    if not p: raise HTTPException(404, "Portfolio not found")
    return p


@app.post("/api/portfolio/fund")
def fund_portfolio(fund: schemas.PortfolioFund, db: Session = Depends(database.get_db)):
    if fund.amount <= 0: raise HTTPException(400, "Amount must be positive")
    p = db.query(models.Portfolio).first()
    if not p: raise HTTPException(404, "Portfolio not found")
    p.balance += fund.amount
    db.commit()
    db.refresh(p)
    el.log(f"Added ${fund.amount:,.2f} to paper portfolio", el.EventType.SYSTEM, el.EventSeverity.SUCCESS)
    return p


# ── Trades ────────────────────────────────────────────────────────────────────
@app.get("/api/trades", response_model=List[schemas.Trade])
def get_trades(status: Optional[str] = None, limit: int = 200, db: Session = Depends(database.get_db)):
    q = db.query(models.Trade)
    if status:
        q = q.filter(models.Trade.status == status.upper())
    return q.order_by(models.Trade.entry_time.desc()).limit(limit).all()


@app.post("/api/trades/execute")
def execute_manual_trade(req: schemas.TradeManualExecute, db: Session = Depends(database.get_db)):
    try:
        trade = bot_engine.execute_manual_trade(req.symbol, req.side.upper(), req.amount_usd, db)
        if not trade:
            raise HTTPException(400, "Trade failed (insufficient balance or invalid symbol)")
        return trade
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/backtest/random")
async def run_random_backtest(req: schemas.BacktestRequest, db: Session = Depends(database.get_db)):
    # yfinance only allows max 60 days historical data for 15m timeframe
    days_ago = random.randint(7, 50)
    start_time = datetime.utcnow() - timedelta(days=days_ago)
    start_ms = int(start_time.timestamp() * 1000)
    
    results = await bot_engine.run_backtest(
        symbol=req.symbol,
        timeframe=req.timeframe,
        start_time_ms=start_ms,
        initial_balance=req.initial_balance
    )
    return results


# ── Event Logs ────────────────────────────────────────────────────────────────
@app.get("/api/logs")
def get_logs(limit: int = 200):
    return el.get_recent(limit)


# ── Bot Config ────────────────────────────────────────────────────────────────
@app.get("/api/bot/config")
def get_config():
    return bot_engine.bot_config


@app.post("/api/bot/config")
def update_config(update: schemas.BotConfigUpdate):
    cfg = bot_engine.bot_config
    data = update.dict(exclude_none=True)
    cfg.update(data)
    el.log(f"Bot config updated: {data}", el.EventType.SYSTEM, el.EventSeverity.INFO)
    return cfg


@app.post("/api/bot/toggle")
def toggle_bot():
    bot_engine.bot_config["trading_enabled"] = not bot_engine.bot_config["trading_enabled"]
    state = bot_engine.bot_config["trading_enabled"]
    el.log(
        f"Bot {'STARTED ▶' if state else 'STOPPED ■'}",
        el.EventType.SYSTEM,
        el.EventSeverity.SUCCESS if state else el.EventSeverity.WARNING
    )
    return {"trading_enabled": state}


# ── Scanner ───────────────────────────────────────────────────────────────────
@app.get("/api/scanner")
def get_scanner():
    return {"results": ms.get_results(), "last_scan": ms._last_scan}


@app.post("/api/scanner/run")
async def trigger_scan():
    asyncio.create_task(ms.run_scan(80))
    return {"status": "scan started"}


# ── Administration ────────────────────────────────────────────────────────────
@app.post("/api/admin/reset-db")
def reset_database():
    """
    Destructive: Resets the entire paper trading database and logs.
    """
    # 1. Stop the bot first
    bot_engine.bot_config["trading_enabled"] = False
    
    db = database.SessionLocal()
    try:
        # 2. Clear data from all tables (safer than drop_all on Windows due to file locking)
        db.query(models.Trade).delete()
        db.query(models.Portfolio).delete()
        db.query(models.EventRecord).delete()
        
        # 3. Re-initialize Portfolio
        db.add(models.Portfolio(balance=10000.0))
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Database reset failed: {str(e)}")
    finally:
        db.close()
    
    # 4. Clear in-memory logs
    with el._lock:
        el._buffer.clear()
        
    el.log("DATABASE RESET - All trades, logs, and portfolio balance cleared", el.EventType.SYSTEM, el.EventSeverity.DANGER)
    
    return {"status": "success", "message": "Database and logs reset successfully"}


# ── Predictions & Patterns ────────────────────────────────────────────────────
@app.get("/api/predictions")
def get_predictions():
    return bot_engine.predictions_cache


@app.get("/api/patterns")
def get_patterns():
    return bot_engine.patterns_cache


# ── Charts ────────────────────────────────────────────────────────────────────
@app.get("/api/chart")
async def get_chart(symbol: str, timeframe: str = "15m", limit: int = 500):
    try:
        df = await bot_engine.fetch_ohlcv(symbol, timeframe, limit)
        if df is None or df.empty:
            raise HTTPException(404, "No chart data found")
        
        data = []
        for timestamp, row in df.iterrows():
            data.append({
                "time": int(timestamp.timestamp()),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "value": float(row["volume"])
            })
        return data
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Strategy Stats ────────────────────────────────────────────────────────────
@app.get("/api/strategies")
def get_strategy_stats():
    stats = bot_engine.strategy_stats
    weights = bot_engine.bot_config["strategy_weights"]
    out = {}
    for name, s in stats.items():
        total = s["wins"] + s["losses"]
        out[name] = {
            **s,
            "total": total,
            "win_rate": round(s["wins"] / total * 100, 1) if total > 0 else 0,
            "weight": weights.get(name, 1.0),
        }
    return out


# ── Performance KPIs ──────────────────────────────────────────────────────────
@app.get("/api/performance")
def get_performance(db: Session = Depends(database.get_db)):
    all_trades = db.query(models.Trade).all()
    closed = [t for t in all_trades if t.status == "CLOSED"]
    open_t = [t for t in all_trades if t.status == "OPEN"]

    total_pnl   = sum(t.pnl or 0 for t in closed)
    wins        = [t for t in closed if (t.pnl or 0) > 0]
    losses      = [t for t in closed if (t.pnl or 0) <= 0]
    win_rate    = round(len(wins) / len(closed) * 100, 1) if closed else 0
    avg_win     = round(sum(t.pnl for t in wins) / len(wins), 4) if wins else 0
    avg_loss    = round(sum(t.pnl for t in losses) / len(losses), 4) if losses else 0
    profit_factor = round(abs(sum(t.pnl for t in wins)) / max(abs(sum(t.pnl for t in losses)), 1e-8), 2)

    portfolio   = db.query(models.Portfolio).first()
    balance     = portfolio.balance if portfolio else 10000.0

    # Equity curve (cumulative PNL per closed trade)
    equity_curve = []
    running = 10000.0
    for t in sorted(closed, key=lambda x: x.entry_time):
        running += (t.pnl or 0)
        equity_curve.append({
            "time": t.exit_time.isoformat() + "Z" if t.exit_time else None,
            "balance": round(running, 2),
            "pnl": round(t.pnl or 0, 4),
            "symbol": t.symbol
        })

    return {
        "balance": balance,
        "total_pnl": round(total_pnl, 4),
        "total_trades": len(closed),
        "open_trades": len(open_t),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "profit_factor": profit_factor,
        "equity_curve": equity_curve,
        "ml_trained_on": len(getattr(__import__('ml_predictor'), '_training_data', [])),
    }


# ── WebSocket Live Event Stream ───────────────────────────────────────────────
class ConnectionManager:
    def __init__(self):
        self._connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self._connections:
            self._connections.remove(ws)

    async def broadcast(self, msg: dict):
        dead = []
        for ws in self._connections:
            try:
                await ws.send_json(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    await manager.connect(websocket)
    q: queue.SimpleQueue = queue.SimpleQueue()
    el.subscribe(q)

    # Send last 50 events on connect
    try:
        recent = el.get_recent(50)
        for ev in reversed(recent):
            await websocket.send_json(ev)
    except Exception:
        pass

    try:
        while True:
            # Check queue for new events from event_log
            try:
                while not q.empty():
                    event = q.get_nowait()
                    await websocket.send_json(event)
            except Exception:
                pass
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        el.unsubscribe(q)