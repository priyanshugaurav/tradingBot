import os
import asyncio
import math
import logging
from decimal import Decimal, ROUND_DOWN, ROUND_FLOOR
from binance.client import Client
from binance.enums import *
from dotenv import load_dotenv
from event_log import log, EventType, EventSeverity

logger = logging.getLogger(__name__)

load_dotenv()

class BinanceFuturesClient:
    def __init__(self, api_key=None, api_secret=None, testnet=True):
        self.api_key = api_key or os.getenv("BINANCE_API_KEY")
        self.api_secret = api_secret or os.getenv("BINANCE_API_SECRET")
        self.testnet = testnet
        
        # Initialize client with testnet flag
        # python-binance handled the base URLs internally when testnet=True
        self.client = Client(self.api_key, self.api_secret, testnet=self.testnet)
        
        # Cache for symbol filters (stepSize, tickSize)
        self._symbol_cache = {}
        self._available_symbols = set()
        self._initialized = False

    async def initialize(self):
        """Explicitly initialize the client (load symbols, sync time)."""
        if self._initialized: return
        await self.sync_time()
        await self._load_available_symbols()
        self._initialized = True
        log("Binance Client Initialized", EventType.SYSTEM, EventSeverity.INFO)

    async def _load_available_symbols(self):
        """Pre-loads all available symbols for the active environment."""
        try:
            info = await asyncio.to_thread(self.client.futures_exchange_info)
            self._available_symbols = {s['symbol'] for s in info['symbols']}
            # Also populate cache with basic info
            for s in info['symbols']:
                filters = {f['filterType']: f for f in s['filters'] if 'filterType' in f}
                if 'LOT_SIZE' in filters and 'PRICE_FILTER' in filters:
                    self._symbol_cache[s['symbol']] = {
                        'stepSize': Decimal(filters['LOT_SIZE']['stepSize']),
                        'tickSize': Decimal(filters['PRICE_FILTER']['tickSize'])
                    }
        except:
            pass

    def is_valid_symbol(self, symbol):
        """Synchronous check against loaded symbols."""
        symbol = symbol.replace("/", "").upper()
        return symbol in self._available_symbols
        
    async def sync_time(self):
        """Syncs local offset with server time specifically for Futures."""
        try:
            import time
            # Wrap blocking call in to_thread
            server_time = await asyncio.to_thread(self.client.futures_time)
            self.client.timestamp_offset = server_time['serverTime'] - int(1000 * time.time())
        except:
            pass
        
    async def get_account_balance(self):
        """Fetches USDT balance for Futures account."""
        try:
            balances = await asyncio.to_thread(self.client.futures_account_balance)
            for b in balances:
                if b['asset'] == 'USDT':
                    return float(b['balance'])
            return 0.0
        except Exception as e:
            raise Exception(f"Failed to fetch balance: {str(e)}")

    async def _get_symbol_info(self, symbol):
        """Fetches and caches symbol filters for precision."""
        # Sanitize: Handle "BTC/USDT" and "BTC/USDT:USDT"
        symbol = symbol.split(':')[0].replace("/", "").upper()
        if symbol in self._symbol_cache:
            return self._symbol_cache[symbol]
        
        try:
            info = await asyncio.to_thread(self.client.futures_exchange_info)
            for s in info['symbols']:
                if s['symbol'] == symbol:
                    filters = {f['filterType']: f for f in s['filters']}
                    self._symbol_cache[symbol] = {
                        'stepSize': Decimal(filters['LOT_SIZE']['stepSize']),
                        'tickSize': Decimal(filters['PRICE_FILTER']['tickSize'])
                    }
                    return self._symbol_cache[symbol]
            return None
        except Exception as e:
            logger.error(f"Error fetching symbol info for {symbol}: {e}")
            return None

    def round_step(self, value, step_size):
        """Rounds a value to the nearest step size using Decimal quantize."""
        if value is None: return None
        val_dec = Decimal(str(value))
        step_dec = Decimal(str(step_size))
        
        # Using quantize is the most reliable way to match Binance precision
        # We use ROUND_FLOOR to avoid rounding UP beyond balance/stop
        rounded = val_dec.quantize(step_dec, rounding=ROUND_FLOOR)
        
        # Return as string to preserve exact precision for the API call
        return str(rounded.normalize())

    async def place_order(self, symbol, side, order_type, quantity, price=None, reduce_only=False, position_side=None):
        """Places a Market or Limit order on Binance Futures."""
        # CRITICAL: Handle CCXT format (BTC/USDT:USDT) and remove slashes
        symbol = symbol.split(':')[0].replace("/", "").upper() 
        info = await self._get_symbol_info(symbol)
        
        if not info:
            err_msg = f"Symbol {symbol} not found in this Binance environment ({'Testnet' if self.testnet else 'Mainnet'})."
            log(err_msg, EventType.SYSTEM, EventSeverity.DANGER, symbol)
            raise ValueError(err_msg)
        
        # Apply strict Decimal rounding
        rounded_qty = self.round_step(quantity, info['stepSize'])
        rounded_price = self.round_step(price, info['tickSize']) if price else None

        # Sync time right before placing order to ensure valid signature
        await self.sync_time()

        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": order_type.upper(),
            "quantity": rounded_qty,
            "recvWindow": 10000 
        }
        
        if reduce_only:
            params["reduceOnly"] = "true" # API expects string or bool depending on wrapper
        
        if position_side:
            params["positionSide"] = position_side.upper()
        
        if order_type.upper() == "LIMIT":
            if not price:
                raise ValueError("Price is required for LIMIT orders.")
            params["price"] = rounded_price
            params["timeInForce"] = "GTC"
            
        try:
            log(f"Placing {side} {symbol}: Qty={rounded_qty} RO={reduce_only}", EventType.SYSTEM, EventSeverity.INFO, symbol)
            
            # Using futures_create_order for USDT-M Futures
            response = await asyncio.to_thread(self.client.futures_create_order, **params)
            
            # Log success with order ID
            order_id = response.get('orderId', 'unknown')
            log(f"Binance Order Placed: {symbol} {side} ID={order_id}", EventType.SYSTEM, EventSeverity.SUCCESS, symbol)
            
            return response
        except Exception as e:
            msg = str(e)
            log(f"Order FAILED: {symbol} {side} - {msg}", EventType.ERROR, EventSeverity.DANGER, symbol)
            raise Exception(f"Order failed: {msg}")
