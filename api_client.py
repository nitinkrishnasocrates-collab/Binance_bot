"""
Binance API client for USDT-M Futures trading.

Provides secure, well-tested API client with request signing,
error handling, and rate limiting.
"""

import requests
import hashlib
import hmac
import time
from typing import Dict, Optional, Any
from urllib.parse import urlencode
from datetime import datetime
from logger import get_bot_logger, APILogger
from config import BotConfig


class BinanceAPIClient:
    """
    Client for interacting with Binance Futures API.
    
    Handles authentication, request signing, and error handling.
    """
    
    def __init__(self, use_testnet: bool = None):
        """
        Initialize Binance API client.
        
        Args:
            use_testnet: Use testnet (default: from config)
        """
        self.logger = get_bot_logger()
        
        if use_testnet is None:
            use_testnet = BotConfig.TESTNET_MODE
        
        self.use_testnet = use_testnet
        
        if use_testnet:
            self.base_url = BotConfig.TESTNET_BASE_URL
            self.api_key = BotConfig.TESTNET_API_KEY
            self.api_secret = BotConfig.TESTNET_API_SECRET
        else:
            self.base_url = BotConfig.BINANCE_BASE_URL
            self.api_key = BotConfig.BINANCE_API_KEY
            self.api_secret = BotConfig.BINANCE_API_SECRET
        
        self.session = requests.Session()
        self.session.headers.update({
            'X-MBX-APIKEY': self.api_key,
            'Content-Type': 'application/json'
        })
        
        # Rate limiting
        self.last_request_time = 0
        self.min_request_interval = 1 / BotConfig.MAX_REQUESTS_PER_SECOND
        
        self.logger.info(f"Binance API client initialized (Testnet: {use_testnet})")
    
    def _wait_for_rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.min_request_interval:
            time.sleep(self.min_request_interval - elapsed)
    
    def _generate_signature(self, data: Dict) -> str:
        """
        Generate HMAC-SHA256 signature for request.
        
        Args:
            data: Request parameters
        
        Returns:
            Signature string
        """
        query_string = urlencode(data)
        signature = hmac.new(
            self.api_secret.encode(),
            query_string.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _build_request_params(self, params: Dict, require_signature: bool = True) -> Dict:
        """
        Build request parameters with timestamp and signature.
        
        Args:
            params: Original parameters
            require_signature: Whether to add signature (for private endpoints)
        
        Returns:
            Complete request parameters
        """
        if require_signature:
            params['timestamp'] = int(time.time() * 1000)
            params['signature'] = self._generate_signature(params)
        
        return params
    
    def request(
        self,
        method: str,
        endpoint: str,
        params: Dict = None,
        require_signature: bool = False
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Binance API.
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            endpoint: API endpoint path (e.g., '/fapi/v1/order')
            params: Request parameters
            require_signature: Whether request requires signature
        
        Returns:
            Response data as dictionary
        
        Raises:
            APIError: If request fails
        """
        self._wait_for_rate_limit()
        
        params = params or {}
        
        if require_signature:
            params = self._build_request_params(params, require_signature=True)
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            APILogger.log_api_request(method, endpoint, params)
            
            if method == "GET":
                response = self.session.get(url, params=params)
            elif method == "POST":
                response = self.session.post(url, params=params)
            elif method == "DELETE":
                response = self.session.delete(url, params=params)
            elif method == "PUT":
                response = self.session.put(url, params=params)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
            
            self.last_request_time = time.time()
            
            # Handle response
            if response.status_code == 200:
                data = response.json()
                APILogger.log_api_response(response.status_code, data)
                return data
            else:
                error_data = response.json() if response.text else {}
                error_msg = error_data.get('msg', response.text)
                error_code = error_data.get('code', response.status_code)
                raise APIError(error_msg, error_code)
        
        except requests.exceptions.RequestException as e:
            APILogger.log_api_error(str(e))
            raise APIError(f"Request failed: {str(e)}")
        
        except Exception as e:
            APILogger.log_api_error(str(e))
            raise APIError(f"Unexpected error: {str(e)}")
    
    # Public API Methods (No signature required)
    
    def get_server_time(self) -> int:
        """Get Binance server time."""
        data = self.request("GET", "/fapi/v1/time")
        return data.get('serverTime', 0)
    
    def get_exchange_info(self) -> Dict:
        """Get exchange information and trading rules."""
        return self.request("GET", "/fapi/v1/exchangeInfo")
    
    def get_current_price(self, symbol: str) -> float:
        """
        Get current price of a symbol.
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
        
        Returns:
            Current price
        """
        data = self.request("GET", "/fapi/v1/ticker/price", {"symbol": symbol})
        return float(data.get('price', 0))
    
    def get_mark_price(self, symbol: str) -> Dict:
        """Get mark price and funding rate."""
        return self.request("GET", "/fapi/v1/fundingRate", {
            "symbol": symbol,
            "limit": 1
        })
    
    def get_order_book(self, symbol: str, limit: int = 20) -> Dict:
        """Get order book for a symbol."""
        return self.request("GET", "/fapi/v1/depth", {
            "symbol": symbol,
            "limit": limit
        })
    
    def get_recent_trades(self, symbol: str, limit: int = 100) -> list:
        """Get recent trades for a symbol."""
        return self.request("GET", "/fapi/v1/trades", {
            "symbol": symbol,
            "limit": limit
        })
    
    # Account Methods
    
    def get_account_info(self) -> Dict:
        """Get account information including balance."""
        return self.request("GET", "/fapi/v2/account", {}, require_signature=True)
    
    def get_account_balance(self) -> Dict:
        """Get USDT balance in account."""
        account = self.get_account_info()
        for asset in account.get('assets', []):
            if asset['asset'] == 'USDT':
                return {
                    'available': float(asset['availableBalance']),
                    'total': float(asset['walletBalance'])
                }
        return {'available': 0, 'total': 0}
    
    # Order Methods
    
    def place_order(self, params: Dict) -> Dict:
        """
        Place a new order.
        
        Args:
            params: Order parameters (symbol, side, type, quantity, etc.)
        
        Returns:
            Order response
        """
        return self.request("POST", "/fapi/v1/order", params, require_signature=True)
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict:
        """
        Place a market order.
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
        
        Returns:
            Order response
        """
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'MARKET',
            'quantity': quantity
        }
        return self.place_order(params)
    
    def place_limit_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        time_in_force: str = 'GTC'
    ) -> Dict:
        """
        Place a limit order.
        
        Args:
            symbol: Trading pair
            side: BUY or SELL
            quantity: Order quantity
            price: Limit price
            time_in_force: GTC, IOC, or FOK
        
        Returns:
            Order response
        """
        params = {
            'symbol': symbol,
            'side': side,
            'type': 'LIMIT',
            'timeInForce': time_in_force,
            'quantity': quantity,
            'price': price
        }
        return self.place_order(params)
    
    def cancel_order(self, symbol: str, order_id: int = None, client_order_id: str = None) -> Dict:
        """
        Cancel an existing order.
        
        Args:
            symbol: Trading pair
            order_id: Binance order ID
            client_order_id: Client order ID
        
        Returns:
            Cancelled order response
        """
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
        elif client_order_id:
            params['origClientOrderId'] = client_order_id
        else:
            raise ValueError("Either order_id or client_order_id is required")
        
        return self.request("DELETE", "/fapi/v1/order", params, require_signature=True)
    
    def get_open_orders(self, symbol: str = None) -> list:
        """
        Get all open orders.
        
        Args:
            symbol: Optional symbol to filter
        
        Returns:
            List of open orders
        """
        params = {}
        if symbol:
            params['symbol'] = symbol
        
        return self.request("GET", "/fapi/v1/openOrders", params, require_signature=True)
    
    def get_order(self, symbol: str, order_id: int = None, client_order_id: str = None) -> Dict:
        """
        Get order details.
        
        Args:
            symbol: Trading pair
            order_id: Binance order ID
            client_order_id: Client order ID
        
        Returns:
            Order details
        """
        params = {'symbol': symbol}
        
        if order_id:
            params['orderId'] = order_id
        elif client_order_id:
            params['origClientOrderId'] = client_order_id
        else:
            raise ValueError("Either order_id or client_order_id is required")
        
        return self.request("GET", "/fapi/v1/order", params, require_signature=True)
    
    def get_order_history(self, symbol: str, limit: int = 100) -> list:
        """
        Get order history.
        
        Args:
            symbol: Trading pair
            limit: Number of orders to return
        
        Returns:
            List of orders
        """
        return self.request("GET", "/fapi/v1/allOrders", {
            'symbol': symbol,
            'limit': limit
        }, require_signature=True)


class APIError(Exception):
    """Custom exception for API errors."""
    
    def __init__(self, message: str, code: str = None):
        """
        Initialize API error.
        
        Args:
            message: Error message
            code: Binance error code
        """
        self.message = message
        self.code = code
        super().__init__(self.message)
    
    def __str__(self):
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message
