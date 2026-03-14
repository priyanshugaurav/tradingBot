import sys
sys.path.append(r'd:\Project-Saas\stock\backend')
import ccxt
import time

ex = ccxt.binance({
    'enableRateLimit': True,
    'options': {
        'defaultType': 'future', # In case we need futures
    }
})
try:
    print("Testing Binance fetch...")
    # Jan 1 2023
    timestamp = 1672531200000
    data = ex.fetch_ohlcv('BTC/USDT', '15m', since=timestamp, limit=50)
    print(f"Success! Got {len(data)} candles.")
    if data:
        print("First candle:", data[0])
except Exception as e:
    print("Exception occurred:", type(e).__name__, str(e))
