import sys
sys.path.append(r'd:\Project-Saas\stock\backend')
import bot_engine
from database import engine
import models
models.Base.metadata.create_all(bind=engine)
from datetime import datetime, timedelta

print("Init DB done. Fetching backtest data...")
start_ms = int((datetime.utcnow() - timedelta(days=5)).timestamp() * 1000)
res = bot_engine.run_backtest('BTC/USDT', '15m', start_ms, 10000.0)

print("RESULT:", res)
