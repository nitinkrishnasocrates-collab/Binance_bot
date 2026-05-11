"""
Binance Futures Trading Bot Package
"""

from api_client import BinanceAPIClient
from market_orders import CoreOrders, MarketOrder, LimitOrder
from advanced.stop_limit import StopLimitOrder
from advanced.oco import OCOOrder
from advanced.twap import TWAPOrder
from advanced.grid_trading import GridOrder

__version__ = "1.0.0"
__all__ = [
    "BinanceAPIClient",
    "CoreOrders",
    "MarketOrder",
    "LimitOrder",
    "StopLimitOrder",
    "OCOOrder",
    "TWAPOrder",
    "GridOrder",
]
