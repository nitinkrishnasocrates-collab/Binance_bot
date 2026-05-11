"""
Validation module for the Binance Futures Trading Bot.

Provides comprehensive input validation for all order types and parameters,
ensuring data integrity before API calls.
"""

from decimal import Decimal, InvalidOperation
from typing import Tuple, Optional
from logger import get_bot_logger, OrderLogger
from config import BotConfig, OrderDefaults, RiskManagement, VALID_ORDER_TYPES, VALID_SIDES


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


class SymbolValidator:
    """Validates trading symbols and their properties."""
    
    # Common USDT-M Futures symbols (can be expanded)
    SUPPORTED_SYMBOLS = {
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "XRPUSDT", "ADAUSDT",
        "DOGEUSDT", "SOLUSDT", "AVAXUSDT", "LINKUSDT", "MATICUSDT",
        "LTCUSDT", "UNIUSDT", "ATOMUSDT", "XLMUSDT", "FILUSDT",
        "SANDUSDT", "MANAUSDT", "GRTUSDT", "SLPUSDT", "VETUSDT",
    }
    
    @staticmethod
    def validate_symbol(symbol: str) -> bool:
        """
        Validate if symbol is properly formatted and supported.
        
        Args:
            symbol: Trading pair symbol (e.g., "BTCUSDT")
        
        Returns:
            True if valid
        
        Raises:
            ValidationError: If symbol is invalid
        """
        if not symbol:
            raise ValidationError("Symbol cannot be empty")
        
        symbol = symbol.upper()
        
        if not symbol.endswith("USDT"):
            raise ValidationError(f"Only USDT-M futures are supported. Got: {symbol}")
        
        if len(symbol) < 6:  # Minimum: "XUSDT"
            raise ValidationError(f"Invalid symbol format: {symbol}")
        
        # Note: In production, fetch actual tradeable symbols from Binance API
        # For now, we validate format
        if not all(c.isalpha() for c in symbol[:-4]):  # Check characters before "USDT"
            raise ValidationError(f"Symbol contains invalid characters: {symbol}")
        
        return True
    
    @staticmethod
    def get_symbol_base(symbol: str) -> str:
        """Extract base asset from symbol (e.g., 'BTC' from 'BTCUSDT')."""
        return symbol.replace("USDT", "")


class QuantityValidator:
    """Validates order quantities and amounts."""
    
    @staticmethod
    def validate_quantity(quantity: float, symbol: str) -> bool:
        """
        Validate order quantity.
        
        Args:
            quantity: Order quantity
            symbol: Trading pair symbol
        
        Returns:
            True if valid
        
        Raises:
            ValidationError: If quantity is invalid
        """
        if quantity <= 0:
            raise ValidationError(f"Quantity must be positive. Got: {quantity}")
        
        try:
            decimal_qty = Decimal(str(quantity))
        except InvalidOperation:
            raise ValidationError(f"Invalid quantity format: {quantity}")
        
        # Check precision (typically 3 decimal places for futures)
        decimal_places = abs(decimal_qty.as_tuple().exponent)
        if decimal_places > BotConfig.QUANTITY_PRECISION:
            raise ValidationError(
                f"Quantity exceeds precision limit ({BotConfig.QUANTITY_PRECISION} decimals). "
                f"Got: {quantity}"
            )
        
        return True
    
    @staticmethod
    def round_quantity(quantity: float) -> float:
        """Round quantity to acceptable precision."""
        return round(quantity, BotConfig.QUANTITY_PRECISION)


class PriceValidator:
    """Validates order prices and price ranges."""
    
    @staticmethod
    def validate_price(price: float) -> bool:
        """
        Validate order price.
        
        Args:
            price: Order price in USDT
        
        Returns:
            True if valid
        
        Raises:
            ValidationError: If price is invalid
        """
        if price <= 0:
            raise ValidationError(f"Price must be positive. Got: {price}")
        
        try:
            decimal_price = Decimal(str(price))
        except InvalidOperation:
            raise ValidationError(f"Invalid price format: {price}")
        
        # Check precision (typically 4 decimal places for futures)
        decimal_places = abs(decimal_price.as_tuple().exponent)
        if decimal_places > BotConfig.PRICE_PRECISION:
            raise ValidationError(
                f"Price exceeds precision limit ({BotConfig.PRICE_PRECISION} decimals). "
                f"Got: {price}"
            )
        
        return True
    
    @staticmethod
    def validate_price_range(entry_price: float, stop_price: float, take_profit_price: float) -> bool:
        """
        Validate logical price relationships.
        
        Args:
            entry_price: Entry/current price
            stop_price: Stop loss price
            take_profit_price: Take profit price
        
        Returns:
            True if valid
        
        Raises:
            ValidationError: If relationship is illogical
        """
        if stop_price >= entry_price:
            raise ValidationError(
                f"Stop price ({stop_price}) must be below entry price ({entry_price})"
            )
        
        if take_profit_price <= entry_price:
            raise ValidationError(
                f"Take profit price ({take_profit_price}) must be above entry price ({entry_price})"
            )
        
        return True
    
    @staticmethod
    def round_price(price: float) -> float:
        """Round price to acceptable precision."""
        return round(price, BotConfig.PRICE_PRECISION)


class OrderValidator:
    """Validates complete order parameters."""
    
    @staticmethod
    def validate_market_order(symbol: str, side: str, quantity: float) -> bool:
        """Validate market order parameters."""
        SymbolValidator.validate_symbol(symbol)
        SideValidator.validate_side(side)
        QuantityValidator.validate_quantity(quantity, symbol)
        return True
    
    @staticmethod
    def validate_limit_order(symbol: str, side: str, quantity: float, price: float) -> bool:
        """Validate limit order parameters."""
        SymbolValidator.validate_symbol(symbol)
        SideValidator.validate_side(side)
        QuantityValidator.validate_quantity(quantity, symbol)
        PriceValidator.validate_price(price)
        return True
    
    @staticmethod
    def validate_stop_limit_order(
        symbol: str,
        side: str,
        quantity: float,
        stop_price: float,
        limit_price: float
    ) -> bool:
        """Validate stop-limit order parameters."""
        SymbolValidator.validate_symbol(symbol)
        SideValidator.validate_side(side)
        QuantityValidator.validate_quantity(quantity, symbol)
        PriceValidator.validate_price(stop_price)
        PriceValidator.validate_price(limit_price)
        
        # For SELL orders: stop > limit, for BUY orders: stop < limit
        if side == "BUY" and stop_price >= limit_price:
            raise ValidationError(
                f"For BUY: stop price ({stop_price}) must be < limit price ({limit_price})"
            )
        elif side == "SELL" and stop_price <= limit_price:
            raise ValidationError(
                f"For SELL: stop price ({stop_price}) must be > limit price ({limit_price})"
            )
        
        return True
    
    @staticmethod
    def validate_oco_order(
        symbol: str,
        side: str,
        quantity: float,
        take_profit_price: float,
        stop_loss_price: float
    ) -> bool:
        """Validate OCO order parameters."""
        SymbolValidator.validate_symbol(symbol)
        SideValidator.validate_side(side)
        QuantityValidator.validate_quantity(quantity, symbol)
        PriceValidator.validate_price(take_profit_price)
        PriceValidator.validate_price(stop_loss_price)
        
        if side == "BUY":
            if take_profit_price <= 0:
                raise ValidationError("Take profit price must be positive")
            if stop_loss_price >= take_profit_price:
                raise ValidationError(
                    f"Stop loss ({stop_loss_price}) must be below take profit ({take_profit_price})"
                )
        else:  # SELL
            if stop_loss_price <= take_profit_price:
                raise ValidationError(
                    f"Stop loss ({stop_loss_price}) must be above take profit ({take_profit_price})"
                )
        
        return True
    
    @staticmethod
    def validate_grid_order(
        symbol: str,
        side: str,
        total_quantity: float,
        upper_price: float,
        lower_price: float,
        grid_levels: int
    ) -> bool:
        """Validate grid order parameters."""
        SymbolValidator.validate_symbol(symbol)
        SideValidator.validate_side(side)
        QuantityValidator.validate_quantity(total_quantity, symbol)
        PriceValidator.validate_price(upper_price)
        PriceValidator.validate_price(lower_price)
        
        if upper_price <= lower_price:
            raise ValidationError(f"Upper price ({upper_price}) must be > lower price ({lower_price})")
        
        if grid_levels < BotConfig.GRID_MIN_LEVELS or grid_levels > BotConfig.GRID_MAX_LEVELS:
            raise ValidationError(
                f"Grid levels must be between {BotConfig.GRID_MIN_LEVELS} "
                f"and {BotConfig.GRID_MAX_LEVELS}. Got: {grid_levels}"
            )
        
        return True
    
    @staticmethod
    def validate_twap_order(
        symbol: str,
        side: str,
        total_quantity: float,
        num_slices: int,
        interval_seconds: int
    ) -> bool:
        """Validate TWAP order parameters."""
        SymbolValidator.validate_symbol(symbol)
        SideValidator.validate_side(side)
        QuantityValidator.validate_quantity(total_quantity, symbol)
        
        if num_slices < 2:
            raise ValidationError(f"Number of slices must be >= 2. Got: {num_slices}")
        
        if interval_seconds < BotConfig.TWAP_MIN_INTERVAL:
            raise ValidationError(
                f"Interval must be >= {BotConfig.TWAP_MIN_INTERVAL} seconds. "
                f"Got: {interval_seconds}"
            )
        
        if interval_seconds > BotConfig.TWAP_MAX_INTERVAL:
            raise ValidationError(
                f"Interval must be <= {BotConfig.TWAP_MAX_INTERVAL} seconds. "
                f"Got: {interval_seconds}"
            )
        
        per_slice_qty = total_quantity / num_slices
        QuantityValidator.validate_quantity(per_slice_qty, symbol)
        
        return True


class SideValidator:
    """Validates order side (BUY/SELL)."""
    
    @staticmethod
    def validate_side(side: str) -> bool:
        """
        Validate order side.
        
        Args:
            side: "BUY" or "SELL"
        
        Returns:
            True if valid
        
        Raises:
            ValidationError: If side is invalid
        """
        if not side or side.upper() not in VALID_SIDES:
            raise ValidationError(f"Invalid side. Must be BUY or SELL. Got: {side}")
        
        return True


class NotionalValidator:
    """Validates order notional value (quantity × price)."""
    
    @staticmethod
    def validate_notional(quantity: float, price: float, symbol: str = None) -> bool:
        """
        Validate order notional value meets minimum requirements.
        
        Args:
            quantity: Order quantity
            price: Order price
            symbol: Trading pair (optional, for logging)
        
        Returns:
            True if valid
        
        Raises:
            ValidationError: If notional is too small
        """
        notional = quantity * price
        
        if notional < BotConfig.MIN_NOTIONAL:
            raise ValidationError(
                f"Order notional ({notional:.2f} USDT) is below minimum "
                f"({BotConfig.MIN_NOTIONAL} USDT)"
            )
        
        return True


def validate_all_inputs(
    symbol: str,
    side: str,
    quantity: float,
    order_type: str,
    **kwargs
) -> Tuple[bool, Optional[str]]:
    """
    Comprehensive validation of all inputs.
    
    Args:
        symbol: Trading pair
        side: BUY or SELL
        quantity: Order quantity
        order_type: Type of order
        **kwargs: Additional parameters for specific order types
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        SymbolValidator.validate_symbol(symbol)
        SideValidator.validate_side(side)
        QuantityValidator.validate_quantity(quantity, symbol)
        
        if order_type == "MARKET":
            # Get current price estimate for notional check
            pass
        elif order_type == "LIMIT":
            price = kwargs.get("price")
            if not price:
                return False, "Price is required for LIMIT orders"
            PriceValidator.validate_price(price)
            NotionalValidator.validate_notional(quantity, price, symbol)
        elif order_type == "STOP_LIMIT":
            stop_price = kwargs.get("stop_price")
            limit_price = kwargs.get("limit_price")
            if not stop_price or not limit_price:
                return False, "Stop price and limit price are required"
            OrderValidator.validate_stop_limit_order(symbol, side, quantity, stop_price, limit_price)
        
        return True, None
    
    except ValidationError as e:
        return False, str(e)
    except Exception as e:
        return False, f"Unexpected validation error: {str(e)}"
