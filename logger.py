"""
Logging module for the Binance Futures Trading Bot.

Provides structured logging with file rotation, proper formatting,
and multiple log levels for different severity levels.
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from config import BotConfig


class BotLogger:
    """Centralized logging configuration for the trading bot."""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        """Implement singleton pattern to ensure single logger instance."""
        if cls._instance is None:
            cls._instance = super(BotLogger, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize the logger with file rotation and console handlers."""
        if BotLogger._initialized:
            return
        
        self.logger = logging.getLogger("BinanceBot")
        self.logger.setLevel(getattr(logging, BotConfig.LOG_LEVEL))
        
        # Prevent duplicate handlers
        if self.logger.handlers:
            return
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt="%(asctime)s | %(name)s | %(levelname)-8s | %(funcName)s:%(lineno)d | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        console_formatter = logging.Formatter(
            fmt="[%(levelname)s] %(asctime)s - %(message)s",
            datefmt="%H:%M:%S"
        )
        
        # File handler with rotation
        try:
            file_handler = logging.handlers.RotatingFileHandler(
                filename=BotConfig.LOG_FILE,
                maxBytes=BotConfig.MAX_LOG_SIZE,
                backupCount=BotConfig.BACKUP_COUNT
            )
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(detailed_formatter)
            self.logger.addHandler(file_handler)
        except Exception as e:
            print(f"Warning: Could not setup file logging: {e}")
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        
        BotLogger._initialized = True
        self.logger.info("=" * 80)
        self.logger.info(f"Binance Futures Trading Bot started at {datetime.now()}")
        self.logger.info(f"Running in {'TESTNET' if BotConfig.TESTNET_MODE else 'LIVE'} mode")
        self.logger.info("=" * 80)
    
    def get_logger(self):
        """Return the configured logger instance."""
        return self.logger


def get_bot_logger():
    """Convenience function to get the bot logger."""
    return BotLogger().get_logger()


class APILogger:
    """Specialized logging for API calls and responses."""
    
    @staticmethod
    def log_api_request(method: str, endpoint: str, params: dict = None):
        """Log API request details."""
        logger = get_bot_logger()
        logger.debug(f"API Request: {method} {endpoint} | Params: {params}")
    
    @staticmethod
    def log_api_response(status_code: int, response_data: dict):
        """Log API response details."""
        logger = get_bot_logger()
        logger.debug(f"API Response: Status {status_code} | Data: {response_data}")
    
    @staticmethod
    def log_api_error(error_msg: str, error_code: str = None):
        """Log API errors with context."""
        logger = get_bot_logger()
        if error_code:
            logger.error(f"API Error [{error_code}]: {error_msg}")
        else:
            logger.error(f"API Error: {error_msg}")


class OrderLogger:
    """Specialized logging for order-related operations."""
    
    @staticmethod
    def log_order_creation(order_type: str, symbol: str, side: str, quantity: float, price: float = None):
        """Log order creation attempt."""
        logger = get_bot_logger()
        price_str = f"@ {price}" if price else "(Market)"
        logger.info(f"[{order_type}] Creating {side} order: {quantity} {symbol} {price_str}")
    
    @staticmethod
    def log_order_placed(order_id: str, order_type: str, symbol: str, side: str):
        """Log successful order placement."""
        logger = get_bot_logger()
        logger.info(f"✓ Order placed successfully | ID: {order_id} | Type: {order_type} | {side} {symbol}")
    
    @staticmethod
    def log_order_executed(order_id: str, executed_qty: float, executed_price: float):
        """Log order execution."""
        logger = get_bot_logger()
        logger.info(f"✓ Order executed | ID: {order_id} | Qty: {executed_qty} @ {executed_price}")
    
    @staticmethod
    def log_order_cancelled(order_id: str, reason: str = None):
        """Log order cancellation."""
        logger = get_bot_logger()
        reason_str = f" | Reason: {reason}" if reason else ""
        logger.info(f"✗ Order cancelled | ID: {order_id}{reason_str}")
    
    @staticmethod
    def log_order_error(order_type: str, error_msg: str):
        """Log order-related errors."""
        logger = get_bot_logger()
        logger.error(f"Order Error [{order_type}]: {error_msg}")


class TradeLogger:
    """Specialized logging for trading activities and P&L."""
    
    @staticmethod
    def log_position_opened(symbol: str, side: str, quantity: float, entry_price: float):
        """Log position opening."""
        logger = get_bot_logger()
        logger.info(f"Position opened: {side} {quantity} {symbol} @ {entry_price}")
    
    @staticmethod
    def log_position_closed(symbol: str, exit_price: float, pnl: float, pnl_percentage: float):
        """Log position closing with P&L."""
        logger = get_bot_logger()
        emoji = "📈" if pnl > 0 else "📉"
        logger.info(f"{emoji} Position closed | {symbol} | PnL: {pnl} USDT ({pnl_percentage:.2f}%)")
    
    @staticmethod
    def log_grid_trade(symbol: str, side: str, level: int, price: float):
        """Log grid trading execution."""
        logger = get_bot_logger()
        logger.info(f"Grid trade executed: Level {level} | {side} {symbol} @ {price}")
