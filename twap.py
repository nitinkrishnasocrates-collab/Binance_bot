"""
TWAP (Time-Weighted Average Price) order implementation for Binance Futures.

TWAP is an execution strategy that splits a large order into smaller chunks
and executes them over time to minimize market impact and achieve an average
execution price close to the weighted average during the execution period.

Use Cases:
- Execute large orders without moving the market
- Minimize slippage on large positions
- Average entry/exit prices over time
- Reduce market impact and detection by others
"""

import time
import threading
from typing import Dict, List, Optional, Callable
from datetime import datetime, timedelta
from decimal import Decimal
from logger import get_bot_logger, OrderLogger, TradeLogger
from validator import OrderValidator, QuantityValidator, PriceValidator
from api_client import BinanceAPIClient, APIError


class TWAPOrder:
    """
    Implements TWAP (Time-Weighted Average Price) order execution.
    
    TWAP divides a large order into smaller slices and executes them
    at regular intervals over a specified time period.
    
    Example:
        Order 10 BTC over 10 minutes in 10 slices
        -> Executes 1 BTC every 60 seconds
        -> Reduces price impact and averages execution price
    """
    
    def __init__(self, api_client: BinanceAPIClient):
        """
        Initialize TWAP order.
        
        Args:
            api_client: Binance API client instance
        """
        self.api_client = api_client
        self.logger = get_bot_logger()
        self.active_twap_orders = {}
    
    def validate_parameters(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        num_slices: int,
        interval_seconds: int
    ) -> tuple:
        """
        Validate TWAP order parameters.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            total_quantity: Total quantity to execute
            num_slices: Number of sub-orders to create
            interval_seconds: Seconds between each slice execution
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            OrderValidator.validate_twap_order(
                symbol, side, total_quantity, num_slices, interval_seconds
            )
            return True, None
        except Exception as e:
            return False, str(e)
    
    def execute(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        num_slices: int = None,
        interval_seconds: int = None,
        total_duration_seconds: int = None,
        order_type: str = 'MARKET',
        limit_price: float = None,
        client_order_id: str = None,
        callback: Callable = None
    ) -> Dict:
        """
        Execute a TWAP order.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL'
            total_quantity: Total quantity to execute
            num_slices: Number of sub-orders (default: 10)
            interval_seconds: Seconds between executions (default: total_duration / num_slices)
            total_duration_seconds: Total execution time (default: 300)
            order_type: 'MARKET' or 'LIMIT'
            limit_price: Limit price for LIMIT orders
            client_order_id: Optional custom order ID prefix
            callback: Optional callback function after each slice execution
        
        Returns:
            TWAP execution summary
        
        Raises:
            ValueError: If parameters are invalid
            APIError: If order execution fails
        """
        # Set defaults
        if num_slices is None:
            num_slices = 10
        if total_duration_seconds is None:
            total_duration_seconds = 300  # 5 minutes
        if interval_seconds is None:
            interval_seconds = total_duration_seconds // num_slices
        
        # Validate inputs
        is_valid, error_msg = self.validate_parameters(
            symbol, side, total_quantity, num_slices, interval_seconds
        )
        if not is_valid:
            raise ValueError(f"Invalid TWAP order: {error_msg}")
        
        # Calculate slice quantity
        per_slice_quantity = QuantityValidator.round_quantity(
            total_quantity / num_slices
        )
        
        try:
            self.logger.info(
                f"[TWAP] Executing {side} {total_quantity} {symbol} | "
                f"Slices: {num_slices} | Interval: {interval_seconds}s | "
                f"Per slice: {per_slice_quantity}"
            )
            
            twap_id = f"{client_order_id}_TWAP_{int(time.time())}" if client_order_id else f"TWAP_{int(time.time())}"
            
            # Create execution plan
            execution_plan = self._create_execution_plan(
                symbol, side, per_slice_quantity, num_slices,
                interval_seconds, order_type, limit_price, client_order_id
            )
            
            # Store TWAP order info
            self.active_twap_orders[twap_id] = {
                'symbol': symbol,
                'side': side,
                'total_quantity': total_quantity,
                'num_slices': num_slices,
                'interval': interval_seconds,
                'status': 'running',
                'executed_slices': 0,
                'orders': []
            }
            
            # Execute in background thread to avoid blocking
            execution_thread = threading.Thread(
                target=self._execute_twap_thread,
                args=(twap_id, execution_plan, callback),
                daemon=True
            )
            execution_thread.start()
            
            return {
                'twap_id': twap_id,
                'symbol': symbol,
                'side': side,
                'total_quantity': total_quantity,
                'per_slice': per_slice_quantity,
                'num_slices': num_slices,
                'interval_seconds': interval_seconds,
                'status': 'started',
                'message': f'TWAP order started. Will execute {num_slices} orders of {per_slice_quantity} each.'
            }
        
        except Exception as e:
            error_msg = f"Failed to start TWAP order: {str(e)}"
            OrderLogger.log_order_error("TWAP", error_msg)
            self.logger.error(error_msg)
            raise
    
    def _create_execution_plan(
        self,
        symbol: str,
        side: str,
        per_slice_quantity: float,
        num_slices: int,
        interval_seconds: int,
        order_type: str,
        limit_price: float,
        client_order_id: str
    ) -> List[Dict]:
        """
        Create the execution plan for TWAP.
        
        Args:
            symbol: Trading pair
            side: Order side
            per_slice_quantity: Quantity per slice
            num_slices: Number of slices
            interval_seconds: Interval between slices
            order_type: Order type for slices
            limit_price: Limit price if applicable
            client_order_id: Base order ID
        
        Returns:
            List of execution instructions
        """
        plan = []
        start_time = time.time()
        
        for i in range(num_slices):
            execution_time = start_time + (i * interval_seconds)
            
            order_instruction = {
                'slice_number': i + 1,
                'execution_time': execution_time,
                'delay_seconds': i * interval_seconds,
                'symbol': symbol,
                'side': side,
                'quantity': per_slice_quantity,
                'order_type': order_type,
                'limit_price': limit_price,
                'client_order_id': f"{client_order_id}_SLICE_{i+1}" if client_order_id else None
            }
            plan.append(order_instruction)
        
        return plan
    
    def _execute_twap_thread(
        self,
        twap_id: str,
        execution_plan: List[Dict],
        callback: Optional[Callable] = None
    ):
        """
        Execute TWAP orders in background thread.
        
        Args:
            twap_id: TWAP order identifier
            execution_plan: List of execution instructions
            callback: Optional callback after each slice
        """
        try:
            self.logger.info(f"TWAP execution thread started: {twap_id}")
            start_time = time.time()
            
            for instruction in execution_plan:
                slice_num = instruction['slice_number']
                delay = instruction['delay_seconds']
                
                # Wait until execution time
                elapsed = time.time() - start_time
                if elapsed < delay:
                    sleep_time = delay - elapsed
                    self.logger.debug(f"TWAP Slice {slice_num}: Waiting {sleep_time:.1f}s")
                    time.sleep(sleep_time)
                
                # Execute slice
                try:
                    self.logger.info(
                        f"TWAP Executing slice {slice_num}/{len(execution_plan)} | "
                        f"Quantity: {instruction['quantity']}"
                    )
                    
                    if instruction['order_type'] == 'MARKET':
                        order_response = self.api_client.place_market_order(
                            instruction['symbol'],
                            instruction['side'],
                            instruction['quantity']
                        )
                    else:  # LIMIT
                        order_response = self.api_client.place_limit_order(
                            instruction['symbol'],
                            instruction['side'],
                            instruction['quantity'],
                            instruction['limit_price']
                        )
                    
                    order_id = order_response.get('orderId')
                    executed_qty = float(order_response.get('executedQty', 0))
                    
                    # Log slice execution
                    OrderLogger.log_order_placed(
                        order_id, f"TWAP_SLICE_{slice_num}", 
                        instruction['symbol'], instruction['side']
                    )
                    
                    # Update TWAP status
                    self.active_twap_orders[twap_id]['executed_slices'] += 1
                    self.active_twap_orders[twap_id]['orders'].append(order_id)
                    
                    # Execute callback if provided
                    if callback:
                        callback({
                            'slice': slice_num,
                            'order_id': order_id,
                            'quantity': executed_qty,
                            'response': order_response
                        })
                    
                    self.logger.info(
                        f"✓ TWAP Slice {slice_num} executed | Order ID: {order_id} | "
                        f"Qty: {executed_qty}"
                    )
                
                except APIError as e:
                    self.logger.error(
                        f"TWAP Slice {slice_num} failed: {str(e)}. Continuing with next slice."
                    )
                    # Continue with next slice even if one fails
            
            # Mark TWAP as completed
            self.active_twap_orders[twap_id]['status'] = 'completed'
            self.logger.info(
                f"✓ TWAP order completed: {twap_id} | "
                f"Total slices executed: {self.active_twap_orders[twap_id]['executed_slices']}"
            )
        
        except Exception as e:
            self.logger.error(f"TWAP execution error: {str(e)}")
            self.active_twap_orders[twap_id]['status'] = 'failed'
    
    def cancel_twap(self, twap_id: str) -> Dict:
        """
        Cancel a TWAP order.
        
        Stops further slice executions and cancels remaining orders.
        
        Args:
            twap_id: TWAP order identifier
        
        Returns:
            Cancellation summary
        """
        try:
            if twap_id not in self.active_twap_orders:
                raise ValueError(f"TWAP order not found: {twap_id}")
            
            twap_info = self.active_twap_orders[twap_id]
            twap_info['status'] = 'cancelled'
            
            self.logger.info(f"Cancelling TWAP order: {twap_id}")
            
            # Try to cancel remaining open orders
            cancelled_count = 0
            for order_id in twap_info['orders']:
                try:
                    self.api_client.cancel_order(twap_info['symbol'], order_id=order_id)
                    cancelled_count += 1
                except:
                    pass  # Order may already be filled
            
            self.logger.info(
                f"TWAP cancelled: {twap_id} | "
                f"Slices executed: {twap_info['executed_slices']} | "
                f"Orders cancelled: {cancelled_count}"
            )
            
            return {
                'twap_id': twap_id,
                'status': 'cancelled',
                'slices_executed': twap_info['executed_slices'],
                'orders_cancelled': cancelled_count
            }
        
        except Exception as e:
            self.logger.error(f"Failed to cancel TWAP: {str(e)}")
            raise
    
    def get_twap_status(self, twap_id: str) -> Dict:
        """
        Get the status of a TWAP order.
        
        Args:
            twap_id: TWAP order identifier
        
        Returns:
            TWAP status details
        """
        if twap_id not in self.active_twap_orders:
            raise ValueError(f"TWAP order not found: {twap_id}")
        
        return self.active_twap_orders[twap_id]
