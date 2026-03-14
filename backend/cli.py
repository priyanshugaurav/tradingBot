import typer
from typing import Optional
from binance_bot.validators import validate_order_input
from binance_bot.orders import place_binance_order
from binance_bot.logging_config import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

app = typer.Typer(help="TradeBot CLI - Binance Futures Testnet Order Placement")
console = Console()

@app.command()
def place(
    symbol: str = typer.Option(..., "--symbol", "-s", help="Trading pair (e.g., BTCUSDT)"),
    side: str = typer.Option(..., "--side", "-side", help="BUY or SELL"),
    order_type: str = typer.Option(..., "--type", "-t", help="MARKET or LIMIT"),
    quantity: float = typer.Option(..., "--qty", "-q", help="Quantity to trade"),
    price: Optional[float] = typer.Option(None, "--price", "-p", help="Price (required for LIMIT)")
):
    """
    Places an order on Binance Futures Testnet.
    """
    # 1. Validate Input
    errors = validate_order_input(symbol, side, order_type, quantity, price)
    if errors:
        for err in errors:
            console.print(f"[bold red]Validation Error:[/bold red] {err}")
        raise typer.Exit(code=1)

    # 2. Print Summary
    console.print(Panel(
        f"[bold cyan]Order Request Summary[/bold cyan]\n"
        f"Symbol: {symbol.upper()}\n"
        f"Side: {side.upper()}\n"
        f"Type: {order_type.upper()}\n"
        f"Quantity: {quantity}\n"
        f"Price: {price if price else 'N/A'}",
        title="TradeBot CLI"
    ))

    # 3. Place Order
    try:
        with console.status("[bold green]Placing order on Binance Testnet...[/bold green]"):
            response = place_binance_order(symbol, side, order_type, quantity, price)
        
        # 4. Print Details
        table = Table(title="Order Response Details")
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="magenta")
        
        table.add_row("Order ID", str(response.get("orderId")))
        table.add_row("Status", str(response.get("status")))
        table.add_row("Executed Qty", str(response.get("executedQty")))
        table.add_row("Avg Price", str(response.get("avgPrice", "N/A")))
        
        console.print(table)
        console.print("\n[bold green]✅ Order placed successfully![/bold green]")
        
    except Exception as e:
        console.print(f"\n[bold red]❌ Order Failed:[/bold red] {str(e)}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
