"""
Configuration module for Binance Futures Trading Bot.

This module manages all configuration settings including API credentials,
trading parameters, and logging configuration.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class BotConfig:
    """Central configuration class for the trading bot."""
    
    # API Configuration
    BINANCE_API_KEY = os.getenv("BINANCE_API_KEY", "your-api-key-here")
    BINANCE_API_SECRET = os.getenv("BINANCE_API_SECRET", "your-api-secret-here")
    BINANCE_BASE_URL = "https://fapi.binance.com"
    
    # Trading Configuration
    TESTNET_MODE = os.getenv("TESTNET_MODE", "True").lower() == "true"
    TESTNET_API_KEY = os.getenv("TESTNET_API_KEY", "testnet-api-key")
    TESTNET_API_SECRET = os.getenv("TESTNET_API_SECRET", "testnet-api-secret")
    TESTNET_BASE_URL = "https://testnet.binancefuture.com"
    
    # Default Trading Parameters
    DEFAULT_LEVERAGE = 1
    MAX_LEVERAGE = 125
    DEFAULT_POSITION_MODE = "One-way"  # One-way or Hedge
    
    # Order Validation
    MIN_NOTIONAL = 10  # Minimum order value in USDT
    PRICE_PRECISION = 4
    QUANTITY_PRECISION = 3
    
    # Grid Trading Parameters
    GRID_MAX_LEVELS = 100
    GRID_MIN_LEVELS = 2
    
    # TWAP Configuration
    TWAP_MIN_INTERVAL = 1  # Minimum 1 second between orders
    TWAP_MAX_INTERVAL = 3600  # Maximum 1 hour between orders
    
    # Logging Configuration
    LOG_DIR = Path(__file__).parent.parent / "logs"
    LOG_FILE = LOG_DIR / "bot.log"
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    MAX_LOG_SIZE = 10_000_000  # 10MB
    BACKUP_COUNT = 5
    
    # Ensure log directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)


class OrderDefaults:
    """Default values for different order types."""
    
    # Market Order
    MARKET_SLIPPAGE = 0.5  # Percentage
    
    # Limit Order
    LIMIT_ORDER_TIMEOUT = 300  # 5 minutes
    
    # Stop-Limit Order
    STOP_LIMIT_TIMEOUT = 600  # 10 minutes
    
    # OCO Order
    OCO_TIMEOUT = 3600  # 1 hour
    
    # TWAP
    TWAP_SLICES = 10
    TWAP_DURATION = 300  # 5 minutes
    
    # Grid
    GRID_PROFIT_PERCENTAGE = 1.0
    GRID_ORDERS_PER_SIDE = 5


class RiskManagement:
    """Risk management settings."""
    
    # Position Sizing
    MAX_POSITION_SIZE_PERCENTAGE = 5  # Max 5% of account per position
    MAX_TOTAL_EXPOSURE_PERCENTAGE = 50  # Max 50% total exposure
    
    # Stop Loss & Take Profit
    DEFAULT_STOP_LOSS_PERCENTAGE = 2.0
    DEFAULT_TAKE_PROFIT_PERCENTAGE = 5.0
    
    # Rate Limiting
    MAX_ORDERS_PER_MINUTE = 50
    MAX_REQUESTS_PER_SECOND = 10
    
    # Drawdown Protection
    MAX_DAILY_LOSS_PERCENTAGE = 5.0
    MAX_WEEKLY_LOSS_PERCENTAGE = 10.0


# Validation ranges
VALID_ORDER_TYPES = ["MARKET", "LIMIT", "STOP_LOSS", "TAKE_PROFIT", "OCO", "TWAP", "GRID"]
VALID_SIDES = ["BUY", "SELL"]
VALID_TIME_IN_FORCE = ["GTC", "IOC", "FOK", "GTX"]
VALID_POSITION_SIDES = ["LONG", "SHORT", "BOTH"]
