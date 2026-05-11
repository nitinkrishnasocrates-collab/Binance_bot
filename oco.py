"""
OCO (One-Cancels-the-Other) order implementation for Binance Futures.

An OCO order places two orders simultaneously:
1. Take-profit order (limit order at a higher/lower price)
2. Stop-loss order (stop-limit order at a lower/higher price)

Only one of these orders can execute. When one executes, the other is automatically cancelled.
This is ideal for automated risk management and profit taking.
"""

from typing import Dict, Optional, Tuple
from datetime import datetime
from logger import get_bot_logger, OrderLogger, TradeLogger
from validator import OrderValidator, PriceValidator, QuantityValidator
from api_client import BinanceAPIClient, APIError


class OCOOrder:
    """
    Represents an OCO (One-Cancels-the-Other) order.
    
    An OCO order combines:
    - A TAKE_PROFIT order (sells at profit target)
    - A STOP_LOSS order (sells at loss limit)
    
    Only one executes; the other is cancelled automatically.
    
    Perfect for:
    - Risk management with predetermined profit targets and stop losses
    - Hands-off trading where you set and forget
    - Protecting positions while locking in gains
    """
    
    def __init__(self, api_client: BinanceAPIClient):
        """
        Initialize OCO order.
        
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
        take_profit_price: float,
        stop_loss_price: float,
        stop_limit_price: float = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate OCO order parameters.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Position quantity
            take_profit_price: Target profit price
            stop_loss_price: Maximum loss price
            stop_limit_price: Limit price for stop loss execution
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            OrderValidator.validate_oco_order(
                symbol, side, quantity, take_profit_price, stop_loss_price
            )
            return True, None
        except Exception as e:
            return False, str(e)
    
    def execute(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float,
        stop_limit_price: float = None,
        client_order_id: str = None
    ) -> Dict:
        """
        Execute an OCO order.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Position quantity
            take_profit_price: Profit target price
            stop_loss_price: Stop loss price
            stop_limit_price: Limit price for stop order (default: stop_loss_price)
            client_order_id: Optional custom order ID
        
        Returns:
            Order response from API
        
        Raises:
            ValueError: If parameters are invalid
            APIError: If API call fails
        """
        # Validate inputs
        is_valid, error_msg = self.validate_parameters(
            symbol, side, quantity, take_profit_price, stop_loss_price
        )
        if not is_valid:
            raise ValueError(f"Invalid OCO order: {error_msg}")
        
        # If stop limit price not specified, use stop loss price
        if stop_limit_price is None:
            stop_limit_price = stop_loss_price * 0.99 if side == "SELL" else stop_loss_price * 1.01
        
        # Round prices to proper precision
        quantity = QuantityValidator.round_quantity(quantity)
        take_profit_price = PriceValidator.round_price(take_profit_price)
        stop_loss_price = PriceValidator.round_price(stop_loss_price)
        stop_limit_price = PriceValidator.round_price(stop_limit_price)
        
        try:
            # Log OCO creation
            self.logger.info(
                f"[OCO] Creating {side} OCO for {quantity} {symbol} | "
                f"TP: {take_profit_price} | SL: {stop_loss_price}"
            )
            
            # Build OCO order parameters
            order_params = {
                'symbol': symbol,
                'side': side,
                'quantity': quantity,
                'price': take_profit_price,  # Take profit limit price
                'stopPrice': stop_loss_price,  # Stop loss trigger price
                'stopLimitPrice': stop_limit_price,  # Stop loss limit price
                'stopLimitTimeInForce': 'GTC'
            }
            
            if client_order_id:
                order_params['newClientOrderId'] = client_order_id
            
            # Submit OCO order via API
            response = self.api_client.request(
                "POST",
                "/fapi/v1/order/oco",  # Note: OCO endpoint may vary by Binance version
                order_params,
                require_signature=True
            )
            
            order_id = response.get('orderId')
            OrderLogger.log_order_placed(order_id, "OCO", symbol, side)
            
            self.logger.info(
                f"✓ OCO order placed successfully | ID: {order_id} | "
                f"TP: {take_profit_price} | SL: {stop_loss_price}"
            )
            
            return response
        
        except APIError as e:
            # If OCO endpoint not available, create as separate orders
            self.logger.warning(f"OCO endpoint error: {e}. Attempting manual OCO...")
            return self._create_manual_oco(
                symbol, side, quantity, take_profit_price,
                stop_loss_price, stop_limit_price, client_order_id
            )
        
        except Exception as e:
            error_msg = f"Unexpected error in OCO order: {str(e)}"
            OrderLogger.log_order_error("OCO", error_msg)
            self.logger.error(error_msg)
            raise
    
    def _create_manual_oco(
        self,
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float,
        stop_limit_price: float,
        client_order_id: str = None
    ) -> Dict:
        """
        Create OCO manually using two separate orders (fallback method).
        
        This creates:
        1. A take-profit limit order at take_profit_price
        2. A stop-limit order at stop_loss_price
        
        Note: This is NOT a true OCO - both orders might fill if market gaps through.
        This is only used as fallback if native OCO is unavailable.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            quantity: Order quantity
            take_profit_price: Take profit limit price
            stop_loss_price: Stop loss trigger price
            stop_limit_price: Stop loss limit price
            client_order_id: Optional order ID
        
        Returns:
            Dictionary with both order responses
        """
        try:
            self.logger.warning(
                "Creating manual OCO (fallback). Use native OCO when possible."
            )
            
            results = {
                'take_profit_order': None,
                'stop_loss_order': None,
                'method': 'manual'
            }
            
            # Create take-profit order
            tp_order_id = f"{client_order_id}_TP" if client_order_id else None
            tp_response = self.api_client.place_order({
                'symbol': symbol,
                'side': side,
                'type': 'LIMIT',
                'timeInForce': 'GTC',
                'quantity': quantity,
                'price': take_profit_price,
                'newClientOrderId': tp_order_id
            })
            results['take_profit_order'] = tp_response
            self.logger.info(f"TP order placed: {tp_response.get('orderId')}")
            
            # Create stop-loss order
            sl_order_id = f"{client_order_id}_SL" if client_order_id else None
            sl_response = self.api_client.place_order({
                'symbol': symbol,
                'side': side,
                'type': 'STOP',
                'timeInForce': 'GTC',
                'quantity': quantity,
                'price': stop_limit_price,
                'stopPrice': stop_loss_price,
                'newClientOrderId': sl_order_id
            })
            results['stop_loss_order'] = sl_response
            self.logger.info(f"SL order placed: {sl_response.get('orderId')}")
            
            return results
        
        except APIError as e:
            error_msg = f"Failed to create manual OCO: {str(e)}"
            OrderLogger.log_order_error("OCO_MANUAL", error_msg)
            self.logger.error(error_msg)
            raise
    
    def cancel_oco(self, symbol: str, order_list_id: int) -> Dict:
        """
        Cancel an OCO order.
        
        Cancelling the OCO will cancel both the TP and SL orders.
        
        Args:
            symbol: Trading pair
            order_list_id: OCO list ID from response
        
        Returns:
            Cancellation response
        """
        try:
            self.logger.info(f"Cancelling OCO order {order_list_id}")
            
            response = self.api_client.request(
                "DELETE",
                "/fapi/v1/orderList",
                {
                    'symbol': symbol,
                    'orderListId': order_list_id
                },
                require_signature=True
            )
            
            OrderLogger.log_order_cancelled(order_list_id, "OCO cancelled")
            self.logger.info(f"OCO order cancelled | ID: {order_list_id}")
            
            return response
        
        except APIError as e:
            error_msg = f"Failed to cancel OCO: {str(e)}"
            OrderLogger.log_order_error("OCO", error_msg)
            self.logger.error(error_msg)
            raise
    
    def get_oco_status(self, symbol: str, order_list_id: int) -> Dict:
        """
        Check the status of an OCO order.
        
        Args:
            symbol: Trading pair
            order_list_id: OCO list ID
        
        Returns:
            OCO status details
        """
        try:
            response = self.api_client.request(
                "GET",
                "/fapi/v1/orderList",
                {
                    'symbol': symbol,
                    'orderListId': order_list_id
                },
                require_signature=True
            )
            
            status = response.get('status')
            self.logger.debug(f"OCO status: {status}")
            
            return response
        
        except APIError as e:
            self.logger.error(f"Failed to get OCO status: {str(e)}")
            raise
