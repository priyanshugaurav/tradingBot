import sys
sys.path.append(r'd:\Project-Saas\stock\backend')
import bot_engine
import traceback

try:
    print("Testing CCXT directly")
    data = bot_engine._exchange.fetch_ohlcv('BTC/USDT', '15m', since=1678665600000, limit=10)
    print("Fetched", len(data), "items")
except Exception as e:
    print("Error:", e)
    traceback.print_exc()

import event_log
from datetime import datetime, timedelta

try:
    start_ms = int((datetime.utcnow() - timedelta(days=5)).timestamp() * 1000)
    print("Calling run_backtest with start_ms=", start_ms)
    res = bot_engine.run_backtest('BTC/USDT', '15m', start_ms, 10000.0)
    print("Result:", res)
    for ev in event_log.get_recent(5):
        print("LOG:", ev)
except Exception as e:
    traceback.print_exc()
