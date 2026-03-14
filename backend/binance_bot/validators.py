def validate_order_input(symbol, side, order_type, quantity, price):
    errors = []
    
    if not symbol:
        errors.append("Symbol is required (e.g., BTCUSDT)")
    
    if side.upper() not in ["BUY", "SELL"]:
        errors.append("Side must be either BUY or SELL")
        
    if order_type.upper() not in ["MARKET", "LIMIT"]:
        errors.append("Order type must be either MARKET or LIMIT")
        
    try:
        qty = float(quantity)
        if qty <= 0:
            errors.append("Quantity must be greater than zero")
    except ValueError:
        errors.append("Quantity must be a valid number")
        
    if order_type.upper() == "LIMIT":
        try:
            p = float(price)
            if p <= 0:
                errors.append("Price must be greater than zero for LIMIT orders")
        except (ValueError, TypeError):
            errors.append("Price is required and must be a valid number for LIMIT orders")
            
    return errors
