from .client import BinanceFuturesClient
from .logging_config import logger

async def place_binance_order(symbol, side, order_type, quantity, price=None):
    client = BinanceFuturesClient()
    
    logger.info(f"Preparing {order_type} {side} order for {quantity} {symbol}" + (f" at {price}" if price else ""))
    
    try:
        response = await client.place_order(symbol, side, order_type, quantity, price)
        logger.info(f"Order SUCCESS | ID: {response.get('orderId')} | Status: {response.get('status')}")
        return response
    except Exception as e:
        logger.error(f"Order FAILURE | {str(e)}")
        raise e
