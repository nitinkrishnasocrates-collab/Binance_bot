"""
Main CLI trading bot interface for Binance Futures.

Provides command-line interface for executing all order types
with proper error handling and user feedback.
"""

import sys
import argparse
from typing import Optional
from logger import get_bot_logger
from api_client import BinanceAPIClient, APIError
from market_orders import CoreOrders, MarketOrder, LimitOrder
from advanced.stop_limit import StopLimitOrder
from advanced.oco import OCOOrder
from advanced.twap import TWAPOrder
from advanced.grid_trading import GridOrder
from validator import ValidationError, validate_all_inputs


class BinanceTradingBot:
    """
    Main trading bot with CLI interface.
    
    Provides command-line methods for all order types and trading operations.
    """
    
    def __init__(self, use_testnet: bool = True):
        """
        Initialize trading bot.
        
        Args:
            use_testnet: Use testnet for safety (default: True)
        """
        self.logger = get_bot_logger()
        self.api_client = BinanceAPIClient(use_testnet=use_testnet)
        
        # Initialize order managers
        self.core_orders = CoreOrders(self.api_client)
        self.stop_limit = StopLimitOrder(self.api_client)
        self.oco = OCOOrder(self.api_client)
        self.twap = TWAPOrder(self.api_client)
        self.grid = GridOrder(self.api_client)
        
        self.logger.info(f"Trading bot initialized (Testnet: {use_testnet})")
    
    # Core Orders
    
    def market_buy(self, symbol: str, quantity: float) -> dict:
        """
        Execute a market buy order.
        
        Usage: python bot.py market_buy BTCUSDT 0.01
        """
        try:
            self.logger.info(f"Executing market buy: {quantity} {symbol}")
            result = self.core_orders.place_market_buy(symbol, quantity)
            self._print_order_result(result)
            return result
        except Exception as e:
            self._print_error(f"Market buy failed: {str(e)}")
            self.logger.error(f"Market buy error: {str(e)}")
            raise
    
    def market_sell(self, symbol: str, quantity: float) -> dict:
        """
        Execute a market sell order.
        
        Usage: python bot.py market_sell BTCUSDT 0.01
        """
        try:
            self.logger.info(f"Executing market sell: {quantity} {symbol}")
            result = self.core_orders.place_market_sell(symbol, quantity)
            self._print_order_result(result)
            return result
        except Exception as e:
            self._print_error(f"Market sell failed: {str(e)}")
            self.logger.error(f"Market sell error: {str(e)}")
            raise
    
    def limit_buy(self, symbol: str, quantity: float, price: float) -> dict:
        """
        Execute a limit buy order.
        
        Usage: python bot.py limit_buy BTCUSDT 0.01 35000
        """
        try:
            self.logger.info(f"Executing limit buy: {quantity} {symbol} @ {price}")
            result = self.core_orders.place_limit_buy(symbol, quantity, price)
            self._print_order_result(result)
            return result
        except Exception as e:
            self._print_error(f"Limit buy failed: {str(e)}")
            self.logger.error(f"Limit buy error: {str(e)}")
            raise
    
    def limit_sell(self, symbol: str, quantity: float, price: float) -> dict:
        """
        Execute a limit sell order.
        
        Usage: python bot.py limit_sell BTCUSDT 0.01 40000
        """
        try:
            self.logger.info(f"Executing limit sell: {quantity} {symbol} @ {price}")
            result = self.core_orders.place_limit_sell(symbol, quantity, price)
            self._print_order_result(result)
            return result
        except Exception as e:
            self._print_error(f"Limit sell failed: {str(e)}")
            self.logger.error(f"Limit sell error: {str(e)}")
            raise
    
    # Advanced Orders
    
    def stop_limit(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        limit_price: float
    ) -> dict:
        """
        Execute a stop-limit order.
        
        Usage: python bot.py stop_limit BTCUSDT SELL 0.01 32000 31500
        """
        try:
            self.logger.info(
                f"Executing stop-limit: {side} {quantity} {symbol} | "
                f"Stop: {stop_price} | Limit: {limit_price}"
            )
            result = self.stop_limit.execute(
                symbol, side, quantity, stop_price, limit_price
            )
            self._print_order_result(result)
            return result
        except Exception as e:
            self._print_error(f"Stop-limit order failed: {str(e)}")
            self.logger.error(f"Stop-limit error: {str(e)}")
            raise
    
    def oco_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float
    ) -> dict:
        """
        Execute an OCO (One-Cancels-the-Other) order.
        
        Usage: python bot.py oco BTCUSDT BUY 0.01 40000 32000
        """
        try:
            self.logger.info(
                f"Executing OCO: {side} {quantity} {symbol} | "
                f"TP: {take_profit_price} | SL: {stop_loss_price}"
            )
            result = self.oco.execute(
                symbol, side, quantity, take_profit_price, stop_loss_price
            )
            self._print_order_result(result)
            return result
        except Exception as e:
            self._print_error(f"OCO order failed: {str(e)}")
            self.logger.error(f"OCO error: {str(e)}")
            raise
    
    def twap_order(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        num_slices: int = 10,
        interval_seconds: int = 30
    ) -> dict:
        """
        Execute a TWAP (Time-Weighted Average Price) order.
        
        Usage: python bot.py twap BTCUSDT BUY 1.0 --slices 10 --interval 30
        """
        try:
            self.logger.info(
                f"Executing TWAP: {side} {total_quantity} {symbol} | "
                f"Slices: {num_slices} | Interval: {interval_seconds}s"
            )
            result = self.twap.execute(
                symbol, side, total_quantity,
                num_slices=num_slices,
                interval_seconds=interval_seconds
            )
            self._print_order_result(result)
            return result
        except Exception as e:
            self._print_error(f"TWAP order failed: {str(e)}")
            self.logger.error(f"TWAP error: {str(e)}")
            raise
    
    def grid_order(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        upper_price: float,
        lower_price: float,
        grid_levels: int = 10
    ) -> dict:
        """
        Create a grid trading strategy.
        
        Usage: python bot.py grid BTCUSDT BUY 1.0 40000 30000 --levels 10
        """
        try:
            self.logger.info(
                f"Creating grid: {side} {total_quantity} {symbol} | "
                f"Range: {lower_price} - {upper_price} | Levels: {grid_levels}"
            )
            result = self.grid.create_grid(
                symbol, side, total_quantity,
                upper_price, lower_price, grid_levels
            )
            self._print_order_result(result)
            return result
        except Exception as e:
            self._print_error(f"Grid order failed: {str(e)}")
            self.logger.error(f"Grid error: {str(e)}")
            raise
    
    # Account & Info
    
    def account_info(self) -> dict:
        """Get account information and balance."""
        try:
            account = self.api_client.get_account_info()
            balance = self.api_client.get_account_balance()
            
            self.logger.info("Account info retrieved")
            
            print("\n" + "="*60)
            print("ACCOUNT INFORMATION")
            print("="*60)
            print(f"Available USDT: {balance['available']:.2f}")
            print(f"Total USDT: {balance['total']:.2f}")
            print("="*60 + "\n")
            
            return {
                'available': balance['available'],
                'total': balance['total']
            }
        except Exception as e:
            self._print_error(f"Failed to get account info: {str(e)}")
            raise
    
    def get_price(self, symbol: str) -> float:
        """Get current price of a symbol."""
        try:
            price = self.api_client.get_current_price(symbol)
            self.logger.info(f"{symbol} price: {price}")
            print(f"\n{symbol} Current Price: {price}\n")
            return price
        except Exception as e:
            self._print_error(f"Failed to get price: {str(e)}")
            raise
    
    # Utility Methods
    
    @staticmethod
    def _print_order_result(result: dict):
        """Pretty print order result."""
        print("\n" + "="*60)
        print("ORDER RESULT")
        print("="*60)
        for key, value in result.items():
            if key not in ['fills']:
                print(f"{key:.<40} {value}")
        print("="*60 + "\n")
    
    @staticmethod
    def _print_error(message: str):
        """Print error message."""
        print(f"\n❌ ERROR: {message}\n")
    
    @staticmethod
    def _print_success(message: str):
        """Print success message."""
        print(f"\n✓ {message}\n")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Binance Futures Trading Bot with Multiple Order Types"
    )
    
    parser.add_argument("--testnet", type=bool, default=True,
                       help="Use testnet (default: True for safety)")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # Market Orders
    market_buy = subparsers.add_parser("market_buy", help="Market buy order")
    market_buy.add_argument("symbol", help="Trading pair (e.g., BTCUSDT)")
    market_buy.add_argument("quantity", type=float, help="Order quantity")
    
    market_sell = subparsers.add_parser("market_sell", help="Market sell order")
    market_sell.add_argument("symbol", help="Trading pair")
    market_sell.add_argument("quantity", type=float, help="Order quantity")
    
    # Limit Orders
    limit_buy = subparsers.add_parser("limit_buy", help="Limit buy order")
    limit_buy.add_argument("symbol", help="Trading pair")
    limit_buy.add_argument("quantity", type=float, help="Order quantity")
    limit_buy.add_argument("price", type=float, help="Limit price")
    
    limit_sell = subparsers.add_parser("limit_sell", help="Limit sell order")
    limit_sell.add_argument("symbol", help="Trading pair")
    limit_sell.add_argument("quantity", type=float, help="Order quantity")
    limit_sell.add_argument("price", type=float, help="Limit price")
    
    # Stop-Limit
    stop_limit = subparsers.add_parser("stop_limit", help="Stop-limit order")
    stop_limit.add_argument("symbol", help="Trading pair")
    stop_limit.add_argument("side", choices=["BUY", "SELL"], help="Order side")
    stop_limit.add_argument("quantity", type=float, help="Order quantity")
    stop_limit.add_argument("stop_price", type=float, help="Stop trigger price")
    stop_limit.add_argument("limit_price", type=float, help="Limit execution price")
    
    # OCO
    oco = subparsers.add_parser("oco", help="OCO order")
    oco.add_argument("symbol", help="Trading pair")
    oco.add_argument("side", choices=["BUY", "SELL"], help="Order side")
    oco.add_argument("quantity", type=float, help="Order quantity")
    oco.add_argument("take_profit", type=float, help="Take profit price")
    oco.add_argument("stop_loss", type=float, help="Stop loss price")
    
    # TWAP
    twap = subparsers.add_parser("twap", help="TWAP order")
    twap.add_argument("symbol", help="Trading pair")
    twap.add_argument("side", choices=["BUY", "SELL"], help="Order side")
    twap.add_argument("quantity", type=float, help="Total quantity")
    twap.add_argument("--slices", type=int, default=10, help="Number of slices")
    twap.add_argument("--interval", type=int, default=30, help="Interval in seconds")
    
    # Grid
    grid = subparsers.add_parser("grid", help="Grid trading")
    grid.add_argument("symbol", help="Trading pair")
    grid.add_argument("side", choices=["BUY", "SELL"], help="Grid direction")
    grid.add_argument("quantity", type=float, help="Total quantity")
    grid.add_argument("upper_price", type=float, help="Upper price bound")
    grid.add_argument("lower_price", type=float, help="Lower price bound")
    grid.add_argument("--levels", type=int, default=10, help="Number of levels")
    
    # Info
    account = subparsers.add_parser("account", help="Get account info")
    price = subparsers.add_parser("price", help="Get current price")
    price.add_argument("symbol", help="Trading pair")
    
    return parser


def main():
    """Main entry point for CLI bot."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    try:
        # Initialize bot
        bot = BinanceTradingBot(use_testnet=args.testnet)
        
        # Route commands
        if args.command == "market_buy":
            bot.market_buy(args.symbol, args.quantity)
        
        elif args.command == "market_sell":
            bot.market_sell(args.symbol, args.quantity)
        
        elif args.command == "limit_buy":
            bot.limit_buy(args.symbol, args.quantity, args.price)
        
        elif args.command == "limit_sell":
            bot.limit_sell(args.symbol, args.quantity, args.price)
        
        elif args.command == "stop_limit":
            bot.stop_limit(args.symbol, args.side, args.quantity,
                          args.stop_price, args.limit_price)
        
        elif args.command == "oco":
            bot.oco_order(args.symbol, args.side, args.quantity,
                         args.take_profit, args.stop_loss)
        
        elif args.command == "twap":
            bot.twap_order(args.symbol, args.side, args.quantity,
                          num_slices=args.slices, interval_seconds=args.interval)
        
        elif args.command == "grid":
            bot.grid_order(args.symbol, args.side, args.quantity,
                          args.upper_price, args.lower_price, args.levels)
        
        elif args.command == "account":
            bot.account_info()
        
        elif args.command == "price":
            bot.get_price(args.symbol)
        
        else:
            parser.print_help()
    
    except KeyboardInterrupt:
        print("\n\nBot interrupted by user.")
        sys.exit(0)
    
    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
