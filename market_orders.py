"""
Core order types: Market and Limit orders for Binance Futures.

These are the fundamental order types used in futures trading.
"""

from decimal import Decimal
from typing import Dict, Optional, Tuple
from datetime import datetime
from logger import get_bot_logger, OrderLogger, TradeLogger
from validator import OrderValidator, QuantityValidator, PriceValidator
from api_client import BinanceAPIClient, APIError


class MarketOrder:
    """
    Represents a market order that executes immediately at current market price.
    
    A market order buys/sells the specified quantity at the best available price
    in the order book. Execution is immediate but price is not guaranteed.
    """
    
    def __init__(self, api_client: BinanceAPIClient):
        """
        Initialize market order.
        
        Args:
            api_client: Binance API client instance
        """
        self.api_client = api_client
        self.logger = get_bot_logger()
    
    def validate_parameters(self, symbol: str, side: str, quantity: float) -> Tuple[bool, Optional[str]]:
        """
        Validate market order parameters before submission.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            side: 'BUY' or 'SELL'
            quantity: Order quantity
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            OrderValidator.validate_market_order(symbol, side, quantity)
            return True, None
        except Exception as e:
            return False, str(e)
    
    def execute(
        self,
        symbol: str,
        side: str,
        quantity: float,
        client_order_id: str = None
    ) -> Dict:
        """
        Execute a market order.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            client_order_id: Optional custom order ID for tracking
        
        Returns:
            Order response from API
        
        Raises:
            ValueError: If parameters are invalid
            APIError: If API call fails
        """
        # Validate inputs
        is_valid, error_msg = self.validate_parameters(symbol, side, quantity)
        if not is_valid:
            raise ValueError(f"Invalid market order: {error_msg}")
        
        # Round quantity to proper precision
        quantity = QuantityValidator.round_quantity(quantity)
        
        try:
            # Log order creation attempt
            OrderLogger.log_order_creation("MARKET", symbol, side, quantity)
            
            # Get current price for logging purposes
            try:
                current_price = self.api_client.get_current_price(symbol)
            except:
                current_price = None
            
            # Build order parameters
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': 'MARKET',
                'quantity': quantity
            }
            
            if client_order_id:
                order_params['newClientOrderId'] = client_order_id
            
            # Submit order to API
            response = self.api_client.place_order(order_params)
            
            # Log successful placement
            order_id = response.get('orderId')
            OrderLogger.log_order_placed(order_id, "MARKET", symbol, side)
            
            # Log execution details
            executed_qty = float(response.get('executedQty', 0))
            if executed_qty > 0:
                avg_price = self._calculate_average_price(response)
                OrderLogger.log_order_executed(order_id, executed_qty, avg_price)
                TradeLogger.log_position_opened(symbol, side, executed_qty, avg_price)
            
            self.logger.info(f"Market order executed successfully | Response: {response}")
            return response
        
        except APIError as e:
            error_msg = f"Failed to place market order: {str(e)}"
            OrderLogger.log_order_error("MARKET", error_msg)
            self.logger.error(error_msg)
            raise
        
        except Exception as e:
            error_msg = f"Unexpected error in market order: {str(e)}"
            OrderLogger.log_order_error("MARKET", error_msg)
            self.logger.error(error_msg)
            raise
    
    @staticmethod
    def _calculate_average_price(order_response: Dict) -> float:
        """
        Calculate average execution price from order response.
        
        Args:
            order_response: Order response from API
        
        Returns:
            Average execution price
        """
        try:
            fills = order_response.get('fills', [])
            if not fills:
                return 0
            
            total_cost = sum(float(fill['price']) * float(fill['qty']) for fill in fills)
            total_qty = sum(float(fill['qty']) for fill in fills)
            
            return total_cost / total_qty if total_qty > 0 else 0
        except:
            return 0


class LimitOrder:
    """
    Represents a limit order that executes only at a specified price or better.
    
    A limit order places an order in the order book with a maximum (BUY) or
    minimum (SELL) price. It may not fill immediately or at all.
    """
    
    def __init__(self, api_client: BinanceAPIClient):
        """
        Initialize limit order.
        
        Args:
            api_client: Binance API client instance
        """
        self.api_client = api_client
        self.logger = get_bot_logger()
    
    def validate_parameters(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = 'GTC'
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate limit order parameters.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Limit price
            time_in_force: 'GTC' (Good-Till-Cancel), 'IOC' (Immediate-Or-Cancel), 'FOK' (Fill-Or-Kill)
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            OrderValidator.validate_limit_order(symbol, side, quantity, price)
            
            if time_in_force not in ['GTC', 'IOC', 'FOK']:
                return False, f"Invalid timeInForce: {time_in_force}"
            
            return True, None
        
        except Exception as e:
            return False, str(e)
    
    def execute(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = 'GTC',
        client_order_id: str = None
    ) -> Dict:
        """
        Execute a limit order.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            price: Limit price
            time_in_force: Order time in force
            client_order_id: Optional custom order ID
        
        Returns:
            Order response from API
        
        Raises:
            ValueError: If parameters are invalid
            APIError: If API call fails
        """
        # Validate inputs
        is_valid, error_msg = self.validate_parameters(symbol, side, quantity, price, time_in_force)
        if not is_valid:
            raise ValueError(f"Invalid limit order: {error_msg}")
        
        # Round to proper precision
        quantity = QuantityValidator.round_quantity(quantity)
        price = PriceValidator.round_price(price)
        
        try:
            # Log order creation
            OrderLogger.log_order_creation("LIMIT", symbol, side, quantity, price)
            
            # Build order parameters
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': 'LIMIT',
                'timeInForce': time_in_force,
                'quantity': quantity,
                'price': price
            }
            
            if client_order_id:
                order_params['newClientOrderId'] = client_order_id
            
            # Submit order
            response = self.api_client.place_order(order_params)
            
            # Log placement
            order_id = response.get('orderId')
            order_status = response.get('status')
            
            OrderLogger.log_order_placed(order_id, "LIMIT", symbol, side)
            
            # Log execution if filled
            executed_qty = float(response.get('executedQty', 0))
            if executed_qty > 0:
                OrderLogger.log_order_executed(order_id, executed_qty, price)
                TradeLogger.log_position_opened(symbol, side, executed_qty, price)
            else:
                self.logger.info(f"Limit order placed and waiting for fill | Status: {order_status}")
            
            self.logger.info(f"Limit order placed successfully | Order ID: {order_id}")
            return response
        
        except APIError as e:
            error_msg = f"Failed to place limit order: {str(e)}"
            OrderLogger.log_order_error("LIMIT", error_msg)
            self.logger.error(error_msg)
            raise
        
        except Exception as e:
            error_msg = f"Unexpected error in limit order: {str(e)}"
            OrderLogger.log_order_error("LIMIT", error_msg)
            self.logger.error(error_msg)
            raise
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """
        Cancel a limit order that hasn't been fully filled.
        
        Args:
            symbol: Trading pair
            order_id: Order ID to cancel
        
        Returns:
            Cancelled order response
        """
        try:
            self.logger.info(f"Attempting to cancel limit order {order_id}")
            response = self.api_client.cancel_order(symbol, order_id=order_id)
            
            OrderLogger.log_order_cancelled(order_id, "User initiated")
            self.logger.info(f"Order cancelled successfully | ID: {order_id}")
            
            return response
        
        except APIError as e:
            error_msg = f"Failed to cancel order: {str(e)}"
            OrderLogger.log_order_error("LIMIT", error_msg)
            self.logger.error(error_msg)
            raise
    
    def get_order_status(self, symbol: str, order_id: int) -> Dict:
        """
        Check the status of a limit order.
        
        Args:
            symbol: Trading pair
            order_id: Order ID to check
        
        Returns:
            Order status details
        """
        try:
            order = self.api_client.get_order(symbol, order_id=order_id)
            
            status = order.get('status')
            executed_qty = float(order.get('executedQty', 0))
            original_qty = float(order.get('origQty', 0))
            price = float(order.get('price', 0))
            
            self.logger.debug(
                f"Order status check | ID: {order_id} | Status: {status} | "
                f"Filled: {executed_qty}/{original_qty} @ {price}"
            )
            
            return order
        
        except APIError as e:
            self.logger.error(f"Failed to get order status: {str(e)}")
            raise


class CoreOrders:
    """
    Manager class for core order types (Market and Limit).
    
    Provides a unified interface for placing and managing basic orders.
    """
    
    def __init__(self, api_client: BinanceAPIClient):
        """
        Initialize core orders manager.
        
        Args:
            api_client: Binance API client instance
        """
        self.api_client = api_client
        self.market = MarketOrder(api_client)
        self.limit = LimitOrder(api_client)
        self.logger = get_bot_logger()
    
    def place_market_buy(self, symbol: str, quantity: float) -> Dict:
        """
        Convenience method for market buy order.
        
        Args:
            symbol: Trading pair
            quantity: Buy quantity
        
        Returns:
            Order response
        """
        return self.market.execute(symbol, "BUY", quantity)
    
    def place_market_sell(self, symbol: str, quantity: float) -> Dict:
        """
        Convenience method for market sell order.
        
        Args:
            symbol: Trading pair
            quantity: Sell quantity
        
        Returns:
            Order response
        """
        return self.market.execute(symbol, "SELL", quantity)
    
    def place_limit_buy(
        self,
        symbol: str,
        quantity: float,
        price: float,
        time_in_force: str = 'GTC'
    ) -> Dict:
        """
        Convenience method for limit buy order.
        
        Args:
            symbol: Trading pair
            quantity: Buy quantity
            price: Limit price
            time_in_force: Order time in force
        
        Returns:
            Order response
        """
        return self.limit.execute(symbol, "BUY", quantity, price, time_in_force)
    
    def place_limit_sell(
        self,
        symbol: str,
        quantity: float,
        price: float,
        time_in_force: str = 'GTC'
    ) -> Dict:
        """
        Convenience method for limit sell order.
        
        Args:
            symbol: Trading pair
            quantity: Sell quantity
            price: Limit price
            time_in_force: Order time in force
        
        Returns:
            Order response
        """
        return self.limit.execute(symbol, "SELL", quantity, price, time_in_force)
