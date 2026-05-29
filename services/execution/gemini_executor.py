import os
import time
import json
import hmac
import hashlib
import base64
import requests
import logging
from typing import Dict, Optional, Any, List

logger = logging.getLogger(__name__)


class GeminiExecutor:
    """
    Real Gemini exchange executor using their REST API.
    Supports spot trading, account management, and order handling.
    """

    API_URL = "https://api.gemini.com"
    SANDBOX_URL = "https://api.sandbox.gemini.com"

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 logger_service=None, sandbox: bool = False):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.api_secret = api_secret or os.getenv("GEMINI_API_SECRET")
        self.trade_logger = logger_service
        self.base_url = self.SANDBOX_URL if sandbox else self.API_URL
        self._nonce_offset = 0

        if not self.api_key or not self.api_secret:
            logger.warning("Gemini API credentials not configured - operating in read-only mode")

    def _get_nonce(self) -> int:
        """Generate unique nonce."""
        return int(time.time() * 1000) + self._nonce_offset

    def _sign_payload(self, payload: Dict) -> tuple:
        """Sign payload for authenticated requests."""
        payload['nonce'] = str(self._get_nonce())
        encoded_payload = base64.b64encode(json.dumps(payload).encode())
        signature = hmac.new(
            self.api_secret.encode(),
            encoded_payload,
            hashlib.sha384
        ).hexdigest()
        return encoded_payload, signature

    def _public_request(self, endpoint: str, params: Dict = None) -> Any:
        """Make public API request."""
        url = f"{self.base_url}{endpoint}"
        try:
            resp = requests.get(url, params=params or {}, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"Gemini API error: {resp.status_code} - {resp.text}")
            return None
        except Exception as e:
            logger.error(f"Gemini public request failed: {e}")
            return None

    def _private_request(self, endpoint: str, params: Dict = None) -> Any:
        """Make authenticated private request."""
        if not self.api_key or not self.api_secret:
            logger.error("API credentials not configured")
            return {"error": "API credentials not configured"}

        url = f"{self.base_url}{endpoint}"
        payload = {"request": endpoint}
        if params:
            payload.update(params)

        encoded_payload, signature = self._sign_payload(payload)

        headers = {
            "Content-Type": "text/plain",
            "Content-Length": "0",
            "X-GEMINI-APIKEY": self.api_key,
            "X-GEMINI-PAYLOAD": encoded_payload.decode(),
            "X-GEMINI-SIGNATURE": signature,
            "Cache-Control": "no-cache",
        }

        try:
            resp = requests.post(url, headers=headers, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            logger.error(f"Gemini API error: {resp.status_code} - {resp.text}")
            return {"error": resp.text, "status_code": resp.status_code}
        except Exception as e:
            logger.error(f"Gemini private request failed: {e}")
            return {"error": str(e)}

    def _normalize_symbol(self, symbol: str) -> str:
        """Normalize symbol to Gemini format (lowercase, no separator)."""
        return symbol.lower().replace("/", "").replace("-", "").replace("_", "")

    def get_symbols(self) -> List[str]:
        """Get list of available trading pairs."""
        result = self._public_request("/v1/symbols")
        return result if result else []

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get current ticker data."""
        symbol = self._normalize_symbol(symbol)
        result = self._public_request(f"/v1/pubticker/{symbol}")
        if result:
            return {
                "bid": float(result.get('bid', 0)),
                "ask": float(result.get('ask', 0)),
                "last": float(result.get('last', 0)),
                "volume": {
                    "base": float(result.get('volume', {}).get(symbol[:3].upper(), 0)),
                    "quote": float(result.get('volume', {}).get(symbol[3:].upper(), 0)),
                }
            }
        return {}

    def get_orderbook(self, symbol: str, limit: int = 50) -> Dict[str, List]:
        """Get order book."""
        symbol = self._normalize_symbol(symbol)
        result = self._public_request(f"/v1/book/{symbol}", {"limit_bids": limit, "limit_asks": limit})
        if result:
            return {
                "bids": [(float(b['price']), float(b['amount'])) for b in result.get('bids', [])],
                "asks": [(float(a['price']), float(a['amount'])) for a in result.get('asks', [])],
            }
        return {"bids": [], "asks": []}

    def get_balance(self) -> Dict[str, Dict[str, float]]:
        """Get account balances."""
        result = self._private_request("/v1/balances")
        if isinstance(result, list):
            balances = {}
            for item in result:
                currency = item['currency']
                balances[currency] = {
                    "available": float(item['available']),
                    "amount": float(item['amount']),
                    "available_for_withdrawal": float(item['availableForWithdrawal']),
                }
            return balances
        return {}

    def get_notional_balances(self, currency: str = "USD") -> Dict[str, float]:
        """Get balances in notional currency value."""
        result = self._private_request("/v1/notionalbalances/" + currency.lower())
        if isinstance(result, list):
            return {item['currency']: float(item['amountNotional']) for item in result}
        return {}

    def buy(self, symbol: str, amount: float, price: Optional[float] = None,
            order_type: str = "exchange limit") -> Dict[str, Any]:
        """Place a buy order."""
        return self._place_order(symbol, "buy", amount, price, order_type)

    def sell(self, symbol: str, amount: float, price: Optional[float] = None,
             order_type: str = "exchange limit") -> Dict[str, Any]:
        """Place a sell order."""
        return self._place_order(symbol, "sell", amount, price, order_type)

    def _place_order(self, symbol: str, side: str, amount: float,
                     price: Optional[float], order_type: str) -> Dict[str, Any]:
        """Internal order placement."""
        symbol = self._normalize_symbol(symbol)

        # Gemini requires limit orders with price, or IOC market orders
        if order_type == "market" or not price:
            # For market orders, use immediate-or-cancel with aggressive pricing
            ticker = self.get_ticker(symbol)
            if side == "buy":
                price = ticker.get('ask', 0) * 1.01  # 1% above ask
            else:
                price = ticker.get('bid', 0) * 0.99  # 1% below bid
            options = ["immediate-or-cancel"]
        else:
            options = []

        params = {
            "symbol": symbol,
            "amount": str(amount),
            "price": str(price),
            "side": side,
            "type": "exchange limit",
            "options": options,
        }

        result = self._private_request("/v1/order/new", params)

        order_result = {
            "exchange": "gemini",
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "amount": amount,
            "price": price,
            "status": "submitted" if not result.get('error') else "failed",
            "error": result.get('error'),
            "order_id": result.get('order_id'),
            "executed_amount": float(result.get('executed_amount', 0)),
            "remaining_amount": float(result.get('remaining_amount', amount)),
            "avg_execution_price": float(result.get('avg_execution_price', 0)) if result.get('avg_execution_price') else None,
            "timestamp": time.time(),
        }

        if self.trade_logger:
            self.trade_logger.log_trade(order_result)

        if result.get('error'):
            logger.error(f"Order failed: {result['error']}")
        else:
            logger.info(f"Order placed: {side} {amount} {symbol} @ {price}")

        return order_result

    def get_order_status(self, order_id: str) -> Dict[str, Any]:
        """Get status of an order."""
        result = self._private_request("/v1/order/status", {"order_id": order_id})
        if result and not result.get('error'):
            return {
                "order_id": result.get('order_id'),
                "symbol": result.get('symbol'),
                "side": result.get('side'),
                "type": result.get('type'),
                "price": float(result.get('price', 0)),
                "original_amount": float(result.get('original_amount', 0)),
                "executed_amount": float(result.get('executed_amount', 0)),
                "remaining_amount": float(result.get('remaining_amount', 0)),
                "is_live": result.get('is_live'),
                "is_cancelled": result.get('is_cancelled'),
            }
        return {"error": result.get('error', 'Unknown error')}

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order."""
        result = self._private_request("/v1/order/cancel", {"order_id": order_id})
        return {
            "order_id": order_id,
            "cancelled": result.get('is_cancelled', False) if not result.get('error') else False,
            "error": result.get('error'),
        }

    def cancel_all_orders(self) -> Dict[str, Any]:
        """Cancel all open orders."""
        result = self._private_request("/v1/order/cancel/all")
        return {
            "cancelled": not result.get('error'),
            "details": result.get('details', {}),
            "error": result.get('error'),
        }

    def get_open_orders(self) -> List[Dict]:
        """Get all open orders."""
        result = self._private_request("/v1/orders")
        if isinstance(result, list):
            return [{
                "order_id": order.get('order_id'),
                "symbol": order.get('symbol'),
                "side": order.get('side'),
                "type": order.get('type'),
                "price": float(order.get('price', 0)),
                "original_amount": float(order.get('original_amount', 0)),
                "remaining_amount": float(order.get('remaining_amount', 0)),
            } for order in result]
        return []

    def get_trade_history(self, symbol: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Get trade history."""
        params = {"limit_trades": limit}
        if symbol:
            params["symbol"] = self._normalize_symbol(symbol)

        result = self._private_request("/v1/mytrades", params)
        if isinstance(result, list):
            return [{
                "trade_id": trade.get('tid'),
                "order_id": trade.get('order_id'),
                "symbol": trade.get('symbol'),
                "side": trade.get('type'),
                "price": float(trade.get('price', 0)),
                "amount": float(trade.get('amount', 0)),
                "fee": float(trade.get('fee_amount', 0)),
                "fee_currency": trade.get('fee_currency'),
                "timestamp": trade.get('timestamp'),
            } for trade in result]
        return []

    def get_deposit_addresses(self, network: str = "ethereum") -> Dict[str, str]:
        """Get deposit addresses."""
        result = self._private_request("/v1/addresses/" + network)
        if isinstance(result, list):
            return {item['currency']: item['address'] for item in result}
        return {}

    def withdraw(self, currency: str, amount: float, address: str) -> Dict[str, Any]:
        """Withdraw funds."""
        result = self._private_request("/v1/withdraw/" + currency.lower(), {
            "address": address,
            "amount": str(amount),
        })
        return {
            "currency": currency,
            "amount": amount,
            "address": address,
            "status": "submitted" if not result.get('error') else "failed",
            "error": result.get('error'),
            "withdrawal_id": result.get('withdrawalId'),
        }

    def get_fee_info(self, symbol: str) -> Dict[str, float]:
        """Get trading fees for a symbol."""
        result = self._private_request("/v1/notionalvolume")
        if result and not result.get('error'):
            return {
                "maker_fee": float(result.get('maker_fee_bps', 0)) / 10000,
                "taker_fee": float(result.get('taker_fee_bps', 0)) / 10000,
                "notional_30d_volume": float(result.get('notional_30d_volume', 0)),
            }
        return {}
