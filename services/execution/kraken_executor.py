import os
import time
import hashlib
import hmac
import base64
import urllib.parse
import requests
import logging
from typing import Dict, Optional, Any, List
from decimal import Decimal

logger = logging.getLogger(__name__)


class KrakenExecutor:
    """
    Real Kraken exchange executor using their REST API.
    Handles authentication, order placement, and account management.
    """

    API_URL = "https://api.kraken.com"
    API_VERSION = "0"

    # Kraken pair mappings (Kraken uses different symbols)
    PAIR_MAP = {
        "BTC/USD": "XXBTZUSD",
        "ETH/USD": "XETHZUSD",
        "ETH/BTC": "XETHXXBT",
        "XRP/USD": "XXRPZUSD",
        "LTC/USD": "XLTCZUSD",
        "ADA/USD": "ADAUSD",
        "DOT/USD": "DOTUSD",
        "SOL/USD": "SOLUSD",
        "MATIC/USD": "MATICUSD",
        "LINK/USD": "LINKUSD",
        "AVAX/USD": "AVAXUSD",
        "ATOM/USD": "ATOMUSD",
        "UNI/USD": "UNIUSD",
        "AAVE/USD": "AAVEUSD",
    }

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None, logger_service=None):
        self.api_key = api_key or os.getenv("KRAKEN_API_KEY")
        self.api_secret = api_secret or os.getenv("KRAKEN_API_SECRET")
        self.trade_logger = logger_service
        self._nonce_offset = 0

        if not self.api_key or not self.api_secret:
            logger.warning("Kraken API credentials not configured - operating in read-only mode")

    def _get_nonce(self) -> int:
        """Generate unique nonce for API calls."""
        return int(time.time() * 1000) + self._nonce_offset

    def _sign_request(self, url_path: str, data: Dict[str, Any]) -> str:
        """Sign request for Kraken API authentication."""
        post_data = urllib.parse.urlencode(data)
        encoded = (str(data['nonce']) + post_data).encode()
        message = url_path.encode() + hashlib.sha256(encoded).digest()
        signature = hmac.new(
            base64.b64decode(self.api_secret),
            message,
            hashlib.sha512
        )
        return base64.b64encode(signature.digest()).decode()

    def _public_request(self, method: str, params: Dict = None) -> Dict:
        """Make public API request (no auth needed)."""
        url = f"{self.API_URL}/{self.API_VERSION}/public/{method}"
        try:
            resp = requests.get(url, params=params or {}, timeout=10)
            data = resp.json()
            if data.get('error'):
                logger.error(f"Kraken API error: {data['error']}")
            return data
        except Exception as e:
            logger.error(f"Kraken public request failed: {e}")
            return {"error": [str(e)]}

    def _private_request(self, method: str, params: Dict = None) -> Dict:
        """Make authenticated private API request."""
        if not self.api_key or not self.api_secret:
            return {"error": ["API credentials not configured"]}

        url_path = f"/{self.API_VERSION}/private/{method}"
        url = f"{self.API_URL}{url_path}"

        params = params or {}
        params['nonce'] = self._get_nonce()

        headers = {
            'API-Key': self.api_key,
            'API-Sign': self._sign_request(url_path, params)
        }

        try:
            resp = requests.post(url, data=params, headers=headers, timeout=10)
            data = resp.json()
            if data.get('error'):
                logger.error(f"Kraken API error: {data['error']}")
            return data
        except Exception as e:
            logger.error(f"Kraken private request failed: {e}")
            return {"error": [str(e)]}

    def _normalize_pair(self, symbol: str) -> str:
        """Convert standard pair format to Kraken format."""
        # Handle formats like "BTCUSD", "BTC/USD", "BTC-USD"
        symbol = symbol.upper().replace("-", "/")
        if "/" not in symbol:
            # Assume USD pair
            symbol = f"{symbol}/USD"
        return self.PAIR_MAP.get(symbol, symbol.replace("/", ""))

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get current ticker data."""
        pair = self._normalize_pair(symbol)
        result = self._public_request("Ticker", {"pair": pair})
        if result.get('result'):
            ticker_data = list(result['result'].values())[0]
            return {
                "ask": float(ticker_data['a'][0]),
                "bid": float(ticker_data['b'][0]),
                "last": float(ticker_data['c'][0]),
                "volume": float(ticker_data['v'][1]),
                "vwap": float(ticker_data['p'][1]),
                "high": float(ticker_data['h'][1]),
                "low": float(ticker_data['l'][1]),
            }
        return {}

    def get_balance(self) -> Dict[str, float]:
        """Get account balances."""
        result = self._private_request("Balance")
        if result.get('result'):
            balances = {}
            for asset, balance in result['result'].items():
                # Convert Kraken asset names (XXBT -> BTC, ZUSD -> USD)
                clean_asset = asset.lstrip('XZ')
                if clean_asset == "XBT":
                    clean_asset = "BTC"
                balances[clean_asset] = float(balance)
            return balances
        return {}

    def get_open_orders(self) -> List[Dict]:
        """Get all open orders."""
        result = self._private_request("OpenOrders")
        if result.get('result', {}).get('open'):
            orders = []
            for order_id, order in result['result']['open'].items():
                orders.append({
                    "id": order_id,
                    "pair": order['descr']['pair'],
                    "type": order['descr']['type'],
                    "side": order['descr']['ordertype'],
                    "price": float(order['descr']['price']) if order['descr']['price'] else None,
                    "volume": float(order['vol']),
                    "filled": float(order['vol_exec']),
                    "status": order['status'],
                })
            return orders
        return []

    def buy(self, symbol: str, amount: float, price: Optional[float] = None,
            order_type: str = "market") -> Dict[str, Any]:
        """Place a buy order."""
        return self._place_order(symbol, "buy", amount, price, order_type)

    def sell(self, symbol: str, amount: float, price: Optional[float] = None,
             order_type: str = "market") -> Dict[str, Any]:
        """Place a sell order."""
        return self._place_order(symbol, "sell", amount, price, order_type)

    def _place_order(self, symbol: str, side: str, amount: float,
                     price: Optional[float], order_type: str) -> Dict[str, Any]:
        """Internal order placement."""
        pair = self._normalize_pair(symbol)

        params = {
            "pair": pair,
            "type": side,
            "ordertype": order_type,
            "volume": str(amount),
        }

        if order_type == "limit" and price:
            params["price"] = str(price)

        result = self._private_request("AddOrder", params)

        order_result = {
            "exchange": "kraken",
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "amount": amount,
            "price": price,
            "status": "submitted" if not result.get('error') else "failed",
            "error": result.get('error'),
            "order_id": result.get('result', {}).get('txid', [None])[0],
            "timestamp": time.time(),
        }

        if self.trade_logger:
            self.trade_logger.log_trade(order_result)

        if result.get('error'):
            logger.error(f"Order failed: {result['error']}")
        else:
            logger.info(f"Order placed: {side} {amount} {symbol} @ {price or 'market'}")

        return order_result

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an open order."""
        result = self._private_request("CancelOrder", {"txid": order_id})
        return {
            "order_id": order_id,
            "cancelled": not result.get('error'),
            "error": result.get('error'),
        }

    def get_trade_history(self, start: Optional[int] = None, end: Optional[int] = None) -> List[Dict]:
        """Get trade history."""
        params = {}
        if start:
            params['start'] = start
        if end:
            params['end'] = end

        result = self._private_request("TradesHistory", params)
        if result.get('result', {}).get('trades'):
            trades = []
            for trade_id, trade in result['result']['trades'].items():
                trades.append({
                    "id": trade_id,
                    "pair": trade['pair'],
                    "side": trade['type'],
                    "price": float(trade['price']),
                    "volume": float(trade['vol']),
                    "cost": float(trade['cost']),
                    "fee": float(trade['fee']),
                    "time": trade['time'],
                })
            return trades
        return []

    def get_deposit_address(self, asset: str, method: str = None) -> Optional[str]:
        """Get deposit address for an asset."""
        params = {"asset": asset}
        if method:
            params["method"] = method

        result = self._private_request("DepositAddresses", params)
        if result.get('result'):
            return result['result'][0].get('address')
        return None

    def withdraw(self, asset: str, amount: float, address: str, key: str) -> Dict[str, Any]:
        """Withdraw funds (requires withdrawal key set up in Kraken)."""
        result = self._private_request("Withdraw", {
            "asset": asset,
            "key": key,
            "amount": str(amount),
        })
        return {
            "asset": asset,
            "amount": amount,
            "status": "submitted" if not result.get('error') else "failed",
            "error": result.get('error'),
            "refid": result.get('result', {}).get('refid'),
        }
