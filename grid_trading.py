"""
Grid Trading strategy implementation for Binance Futures.

Grid trading automatically places buy and sell orders at regular price intervals
within a defined range, profiting from price oscillations.

How it works:
1. Define upper and lower price bounds
2. Define number of grid levels
3. Bot places buy orders below current price
4. Bot places sell orders above current price
5. As price bounces within the range, orders execute for profit
6. Each filled buy-sell pair locks in profit

Perfect for:
- Ranging (sideways) markets
- Capturing volatility without directional bias
- Passive income from price oscillations
- Highly volatile altcoins
"""

from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from logger import get_bot_logger, OrderLogger, TradeLogger
from validator import OrderValidator, PriceValidator, QuantityValidator
from api_client import BinanceAPIClient, APIError


class GridOrder:
    """
    Implements grid trading strategy.
    
    Grid trading places orders at predetermined price intervals and automatically
    profits when prices oscillate between buy and sell levels.
    """
    
    def __init__(self, api_client: BinanceAPIClient):
        """
        Initialize grid order.
        
        Args:
            api_client: Binance API client instance
        """
        self.api_client = api_client
        self.logger = get_bot_logger()
        self.active_grids = {}
    
    def validate_parameters(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        upper_price: float,
        lower_price: float,
        grid_levels: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate grid order parameters.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL' (grid direction)
            total_quantity: Total quantity for all grid levels
            upper_price: Upper price boundary
            lower_price: Lower price boundary
            grid_levels: Number of grid levels
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            OrderValidator.validate_grid_order(
                symbol, side, total_quantity, upper_price, lower_price, grid_levels
            )
            return True, None
        except Exception as e:
            return False, str(e)
    
    def create_grid(
        self,
        symbol: str,
        side: str,
        total_quantity: float,
        upper_price: float,
        lower_price: float,
        grid_levels: int,
        profit_percentage: float = None,
        client_order_id: str = None
    ) -> Dict:
        """
        Create a grid trading setup.
        
        Args:
            symbol: Trading pair
            side: 'BUY' or 'SELL' (initial grid direction)
            total_quantity: Total quantity to deploy across grid
            upper_price: Maximum price in range
            lower_price: Minimum price in range
            grid_levels: Number of levels in grid
            profit_percentage: Profit target per level (default: 1%)
            client_order_id: Optional custom order ID
        
        Returns:
            Grid setup summary with all orders
        
        Raises:
            ValueError: If parameters are invalid
            APIError: If order placement fails
        """
        # Validate inputs
        is_valid, error_msg = self.validate_parameters(
            symbol, side, total_quantity, upper_price, lower_price, grid_levels
        )
        if not is_valid:
            raise ValueError(f"Invalid grid order: {error_msg}")
        
        if profit_percentage is None:
            profit_percentage = 1.0  # 1% profit per grid level
        
        try:
            self.logger.info(
                f"[GRID] Creating {side} grid for {total_quantity} {symbol} | "
                f"Range: {lower_price} - {upper_price} | Levels: {grid_levels}"
            )
            
            # Calculate grid parameters
            grid_id = f"GRID_{int(time.time())}"
            per_level_quantity = QuantityValidator.round_quantity(
                total_quantity / grid_levels
            )
            
            # Generate grid prices
            grid_prices = self._generate_grid_prices(
                lower_price, upper_price, grid_levels
            )
            
            self.logger.debug(f"Grid prices: {grid_prices}")
            
            # Place orders at each grid level
            placed_orders = self._place_grid_orders(
                grid_id, symbol, side, per_level_quantity,
                grid_prices, profit_percentage, client_order_id
            )
            
            # Store grid information
            self.active_grids[grid_id] = {
                'symbol': symbol,
                'side': side,
                'total_quantity': total_quantity,
                'per_level_quantity': per_level_quantity,
                'grid_levels': grid_levels,
                'upper_price': upper_price,
                'lower_price': lower_price,
                'grid_prices': grid_prices,
                'profit_percentage': profit_percentage,
                'status': 'active',
                'orders': placed_orders,
                'completed_pairs': 0
            }
            
            self.logger.info(
                f"✓ Grid created: {grid_id} | "
                f"Orders placed: {len(placed_orders)} | "
                f"Per level: {per_level_quantity} {symbol}"
            )
            
            return {
                'grid_id': grid_id,
                'symbol': symbol,
                'side': side,
                'total_quantity': total_quantity,
                'grid_levels': grid_levels,
                'per_level_quantity': per_level_quantity,
                'range': {'lower': lower_price, 'upper': upper_price},
                'orders_placed': len(placed_orders),
                'status': 'active'
            }
        
        except Exception as e:
            error_msg = f"Failed to create grid: {str(e)}"
            OrderLogger.log_order_error("GRID", error_msg)
            self.logger.error(error_msg)
            raise
    
    def _generate_grid_prices(
        self,
        lower_price: float,
        upper_price: float,
        num_levels: int
    ) -> List[float]:
        """
        Generate evenly spaced grid prices.
        
        Args:
            lower_price: Minimum grid price
            upper_price: Maximum grid price
            num_levels: Number of grid levels
        
        Returns:
            List of grid prices (lowest to highest)
        """
        prices = []
        
        # Use logarithmic spacing for better distribution on larger ranges
        lower_log = Decimal(str(lower_price)).ln()
        upper_log = Decimal(str(upper_price)).ln()
        
        for i in range(num_levels):
            # Linear interpolation in log space
            ratio = i / (num_levels - 1) if num_levels > 1 else 0
            log_price = lower_log + (upper_log - lower_log) * Decimal(str(ratio))
            price = float(log_price.exp())
            prices.append(PriceValidator.round_price(price))
        
        return sorted(list(set(prices)))  # Remove duplicates and sort
    
    def _place_grid_orders(
        self,
        grid_id: str,
        symbol: str,
        side: str,
        per_level_quantity: float,
        grid_prices: List[float],
        profit_percentage: float,
        client_order_id: str
    ) -> List[Dict]:
        """
        Place all grid orders on exchange.
        
        Args:
            grid_id: Grid identifier
            symbol: Trading pair
            side: Grid direction
            per_level_quantity: Quantity per grid level
            grid_prices: List of grid prices
            profit_percentage: Profit per level
            client_order_id: Base order ID
        
        Returns:
            List of placed order responses
        """
        placed_orders = []
        
        try:
            for i, price in enumerate(grid_prices):
                # For BUY grid: place buy orders below, sell orders above
                # For SELL grid: place sell orders above, buy orders below
                
                # Place buy order at this level
                buy_order_id = f"{client_order_id}_BUY_{i}" if client_order_id else None
                
                try:
                    buy_response = self.api_client.place_limit_order(
                        symbol, 'BUY', per_level_quantity, price,
                        time_in_force='GTC'
                    )
                    placed_orders.append({
                        'type': 'BUY',
                        'level': i,
                        'price': price,
                        'quantity': per_level_quantity,
                        'order_id': buy_response.get('orderId'),
                        'status': 'placed'
                    })
                    
                    OrderLogger.log_order_placed(
                        buy_response.get('orderId'), "GRID_BUY", symbol, "BUY"
                    )
                    TradeLogger.log_grid_trade(symbol, "BUY", i, price)
                    
                except APIError as e:
                    self.logger.warning(f"Failed to place buy order at level {i}: {e}")
                
                # Place sell order at profit level
                sell_price = price * (1 + profit_percentage / 100)
                sell_price = PriceValidator.round_price(sell_price)
                sell_order_id = f"{client_order_id}_SELL_{i}" if client_order_id else None
                
                try:
                    sell_response = self.api_client.place_limit_order(
                        symbol, 'SELL', per_level_quantity, sell_price,
                        time_in_force='GTC'
                    )
                    placed_orders.append({
                        'type': 'SELL',
                        'level': i,
                        'price': sell_price,
                        'quantity': per_level_quantity,
                        'order_id': sell_response.get('orderId'),
                        'status': 'placed'
                    })
                    
                    OrderLogger.log_order_placed(
                        sell_response.get('orderId'), "GRID_SELL", symbol, "SELL"
                    )
                    TradeLogger.log_grid_trade(symbol, "SELL", i, sell_price)
                
                except APIError as e:
                    self.logger.warning(f"Failed to place sell order at level {i}: {e}")
        
        except Exception as e:
            self.logger.error(f"Error placing grid orders: {str(e)}")
        
        return placed_orders
    
    def cancel_grid(self, grid_id: str) -> Dict:
        """
        Cancel all orders in a grid.
        
        Args:
            grid_id: Grid identifier
        
        Returns:
            Cancellation summary
        """
        try:
            if grid_id not in self.active_grids:
                raise ValueError(f"Grid not found: {grid_id}")
            
            grid_info = self.active_grids[grid_id]
            symbol = grid_info['symbol']
            
            self.logger.info(f"Cancelling grid: {grid_id}")
            
            cancelled_count = 0
            for order in grid_info['orders']:
                try:
                    self.api_client.cancel_order(symbol, order_id=order['order_id'])
                    cancelled_count += 1
                    OrderLogger.log_order_cancelled(order['order_id'], "Grid cancelled")
                except:
                    pass  # Order may already be filled
            
            grid_info['status'] = 'cancelled'
            
            self.logger.info(
                f"Grid cancelled: {grid_id} | Orders cancelled: {cancelled_count}"
            )
            
            return {
                'grid_id': grid_id,
                'status': 'cancelled',
                'orders_cancelled': cancelled_count
            }
        
        except Exception as e:
            self.logger.error(f"Failed to cancel grid: {str(e)}")
            raise
    
    def get_grid_status(self, grid_id: str) -> Dict:
        """
        Get detailed grid status.
        
        Args:
            grid_id: Grid identifier
        
        Returns:
            Grid status and performance
        """
        if grid_id not in self.active_grids:
            raise ValueError(f"Grid not found: {grid_id}")
        
        grid_info = self.active_grids[grid_id]
        
        # Calculate statistics
        total_orders = len(grid_info['orders'])
        buy_orders = sum(1 for o in grid_info['orders'] if o['type'] == 'BUY')
        sell_orders = sum(1 for o in grid_info['orders'] if o['type'] == 'SELL')
        
        return {
            'grid_id': grid_id,
            'symbol': grid_info['symbol'],
            'status': grid_info['status'],
            'grid_levels': grid_info['grid_levels'],
            'total_orders': total_orders,
            'buy_orders': buy_orders,
            'sell_orders': sell_orders,
            'per_level_quantity': grid_info['per_level_quantity'],
            'price_range': {
                'lower': grid_info['lower_price'],
                'upper': grid_info['upper_price']
            },
            'completed_cycles': grid_info['completed_pairs'],
            'profit_percentage_per_level': grid_info['profit_percentage']
        }


import time  # Import at end to avoid circular imports
