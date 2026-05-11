"""
Stop-Limit order implementation for Binance Futures.

A stop-limit order combines a stop loss trigger with a limit order.
When the stop price is reached, a limit order is placed at the specified limit price.
"""

from typing import Dict, Optional, Tuple
from datetime import datetime
import time
from logger import get_bot_logger, OrderLogger
from validator import OrderValidator, PriceValidator
from api_client import BinanceAPIClient, APIError


class StopLimitOrder:
    """
    Represents a stop-limit order that triggers a limit order at a specified price.
    
    Process:
    1. User sets stop price (trigger level) and limit price (execution price)
    2. Order waits until market price hits stop price
    3. When triggered, a limit order is placed at the limit price
    4. Order may fill partially or not at all if price doesn't reach limit
    
    Use Cases:
    - Close a losing position at a specific price below market
    - Enter a position if price drops to a target level
    - Capture a support bounce with precise entry
    """
    
    def __init__(self, api_client: BinanceAPIClient):
        """
        Initialize stop-limit order.
        
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
        stop_price: float,
        limit_price: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate stop-limit order parameters.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            stop_price: Price that triggers the order
            limit_price: Price at which limit order is placed
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            OrderValidator.validate_stop_limit_order(
                symbol, side, quantity, stop_price, limit_price
            )
            return True, None
        except Exception as e:
            return False, str(e)
    
    def execute(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        limit_price: float,
        client_order_id: str = None,
        time_in_force: str = 'GTC'
    ) -> Dict:
        """
        Execute a stop-limit order.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            stop_price: Trigger price
            limit_price: Limit price for the actual order
            client_order_id: Optional custom order ID
            time_in_force: 'GTC', 'IOC', or 'FOK'
        
        Returns:
            Order response from API
        
        Raises:
            ValueError: If parameters are invalid
            APIError: If API call fails
        """
        # Validate inputs
        is_valid, error_msg = self.validate_parameters(
            symbol, side, quantity, stop_price, limit_price
        )
        if not is_valid:
            raise ValueError(f"Invalid stop-limit order: {error_msg}")
        
        # Round prices to proper precision
        stop_price = PriceValidator.round_price(stop_price)
        limit_price = PriceValidator.round_price(limit_price)
        
        try:
            # Log order creation
            self.logger.info(
                f"[STOP-LIMIT] Creating {side} order for {quantity} {symbol} | "
                f"Stop: {stop_price} | Limit: {limit_price}"
            )
            
            # Build order parameters for Binance API
            order_params = {
                'symbol': symbol,
                'side': side,
                'type': 'STOP',  # Binance uses 'STOP' for stop orders
                'timeInForce': time_in_force,
                'quantity': quantity,
                'price': limit_price,  # Limit price (execution price)
                'stopPrice': stop_price  # Stop trigger price
            }
            
            if client_order_id:
                order_params['newClientOrderId'] = client_order_id
            
            # Submit order to API
            response = self.api_client.place_order(order_params)
            
            order_id = response.get('orderId')
            OrderLogger.log_order_placed(order_id, "STOP-LIMIT", symbol, side)
            
            self.logger.info(
                f"✓ Stop-limit order placed successfully | ID: {order_id} | "
                f"Waiting for stop price ({stop_price}) to trigger"
            )
            
            return response
        
        except APIError as e:
            error_msg = f"Failed to place stop-limit order: {str(e)}"
            OrderLogger.log_order_error("STOP-LIMIT", error_msg)
            self.logger.error(error_msg)
            raise
        
        except Exception as e:
            error_msg = f"Unexpected error in stop-limit order: {str(e)}"
            OrderLogger.log_order_error("STOP-LIMIT", error_msg)
            self.logger.error(error_msg)
            raise
    
    def create_trailing_stop(
        self,
        symbol: str,
        side: str,
        quantity: float,
        stop_distance_percentage: float,
        client_order_id: str = None
    ) -> Dict:
        """
        Create a trailing stop order (advanced variant).
        
        A trailing stop automatically adjusts the stop price as the market
        moves in favorable direction, helping to lock in profits.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            stop_distance_percentage: Distance in percentage from current price
            client_order_id: Optional custom order ID
        
        Returns:
            Order response from API
        
        Raises:
            APIError: If API call fails
        """
        try:
            # Get current market price
            current_price = self.api_client.get_current_price(symbol)
            self.logger.debug(f"Current price for {symbol}: {current_price}")
            
            # Calculate stop price based on distance
            if side == "SELL":  # Selling, stop below current
                stop_price = current_price * (1 - stop_distance_percentage / 100)
            else:  # Buying, stop above current
                stop_price = current_price * (1 + stop_distance_percentage / 100)
            
            stop_price = PriceValidator.round_price(stop_price)
            
            # For trailing stop, limit price is slightly below/above stop
            # This ensures the order fills when triggered
            if side == "SELL":
                limit_price = stop_price * 0.98  # 2% below stop
            else:
                limit_price = stop_price * 1.02  # 2% above stop
            
            limit_price = PriceValidator.round_price(limit_price)
            
            self.logger.info(
                f"[TRAILING STOP] Creating for {quantity} {symbol} | "
                f"Current: {current_price} | Stop: {stop_price} | Limit: {limit_price}"
            )
            
            return self.execute(
                symbol, side, quantity, stop_price, limit_price, client_order_id
            )
        
        except Exception as e:
            error_msg = f"Failed to create trailing stop: {str(e)}"
            OrderLogger.log_order_error("TRAILING_STOP", error_msg)
            self.logger.error(error_msg)
            raise
    
    def cancel_order(self, symbol: str, order_id: int) -> Dict:
        """
        Cancel a stop-limit order.
        
        Args:
            symbol: Trading pair
            order_id: Order ID to cancel
        
        Returns:
            Cancelled order response
        """
        try:
            self.logger.info(f"Cancelling stop-limit order {order_id}")
            response = self.api_client.cancel_order(symbol, order_id=order_id)
            
            OrderLogger.log_order_cancelled(order_id, "Stop-limit cancelled")
            self.logger.info(f"Stop-limit order cancelled | ID: {order_id}")
            
            return response
        
        except APIError as e:
            error_msg = f"Failed to cancel stop-limit order: {str(e)}"
            OrderLogger.log_order_error("STOP-LIMIT", error_msg)
            self.logger.error(error_msg)
            raise
    
    def get_order_status(self, symbol: str, order_id: int) -> Dict:
        """
        Check the status of a stop-limit order.
        
        Args:
            symbol: Trading pair
            order_id: Order ID to check
        
        Returns:
            Order status details
        """
        try:
            order = self.api_client.get_order(symbol, order_id=order_id)
            
            status = order.get('status')
            stop_price = float(order.get('stopPrice', 0))
            price = float(order.get('price', 0))
            
            self.logger.debug(
                f"Stop-limit order status | ID: {order_id} | Status: {status} | "
                f"Stop: {stop_price} | Limit: {price}"
            )
            
            return order
        
        except APIError as e:
            self.logger.error(f"Failed to get stop-limit order status: {str(e)}")
            raise
