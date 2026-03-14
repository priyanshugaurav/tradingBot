import sys
sys.path.append(r'd:\Project-Saas\stock\backend')
import bot_engine
import traceback
from datetime import datetime, timedelta

try:
    print("Testing Binance fetch via yfinance")
    # Date 20 days ago so we definitely have data
    start_time = datetime.utcnow() - timedelta(days=20)
    start_ms = int(start_time.timestamp() * 1000)
    
    print("Calling run_backtest with start_ms=", start_ms)
    res = bot_engine.run_backtest('BTC/USDT', '15m', start_ms, 10000.0)
    print("Result:", res)
    
    import event_log
    for ev in event_log.get_recent(5):
        print("LOG:", ev)
except Exception as e:
    print("Error:", e)
    traceback.print_exc()
