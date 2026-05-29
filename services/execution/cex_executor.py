import os
import time
import logging
from typing import Dict, Optional, Any, List
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class CEXExecutor:
    """
    Generic centralized exchange executor base class.
    Can be used as a simple mock/paper trading executor or extended for specific exchanges.
    """

    def __init__(self, api_key: Optional[str] = None, api_secret: Optional[str] = None,
                 trade_logger=None, paper_mode: bool = None):
        self.api_key = api_key or os.getenv("CEX_API_KEY")
        self.api_secret = api_secret or os.getenv("CEX_API_SECRET")
        self.trade_logger = trade_logger

        # Default to paper mode if no trading mode set
        trading_mode = os.getenv("TRADING_MODE", "paper")
        self.paper_mode = paper_mode if paper_mode is not None else (trading_mode == "paper")

        # Paper trading state
        self.paper_balances: Dict[str, float] = {
            "USD": 10000.0,
            "BTC": 0.0,
            "ETH": 0.0,
        }
        self.paper_orders: List[Dict] = []
        self.paper_trades: List[Dict] = []

        if self.paper_mode:
            logger.info("CEXExecutor running in PAPER TRADING mode")

    def get_balance(self) -> Dict[str, float]:
        """Get account balances."""
        if self.paper_mode:
            return {k: v for k, v in self.paper_balances.items() if v > 0}

        # Override in subclass for real exchange
        logger.warning("get_balance not implemented for live trading")
        return {}

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """Get ticker data for a symbol."""
        # Simple mock prices for paper trading
        mock_prices = {
            "BTC/USD": {"bid": 67000, "ask": 67050, "last": 67025},
            "ETH/USD": {"bid": 3400, "ask": 3405, "last": 3402},
            "SOL/USD": {"bid": 145, "ask": 145.5, "last": 145.25},
        }
        return mock_prices.get(symbol, {"bid": 100, "ask": 100.1, "last": 100.05})

    def buy(self, symbol: str, amount: float, price: Optional[float] = None,
            order_type: str = "market") -> Dict[str, Any]:
        """Place a buy order."""
        return self._execute_order(symbol, "buy", amount, price, order_type)

    def sell(self, symbol: str, amount: float, price: Optional[float] = None,
             order_type: str = "market") -> Dict[str, Any]:
        """Place a sell order."""
        return self._execute_order(symbol, "sell", amount, price, order_type)

    def _execute_order(self, symbol: str, side: str, amount: float,
                       price: Optional[float], order_type: str) -> Dict[str, Any]:
        """Execute an order (paper or live)."""
        if self.paper_mode:
            return self._paper_execute(symbol, side, amount, price, order_type)

        # Override in subclass for real trading
        logger.error("Live trading not implemented - use paper mode or specific exchange executor")
        return {"status": "failed", "error": "Live trading not implemented"}

    def _paper_execute(self, symbol: str, side: str, amount: float,
                       price: Optional[float], order_type: str) -> Dict[str, Any]:
        """Execute paper trade."""
        # Parse symbol (e.g., "BTC/USD" -> base="BTC", quote="USD")
        parts = symbol.replace("-", "/").split("/")
        if len(parts) != 2:
            return {"status": "failed", "error": f"Invalid symbol format: {symbol}"}

        base, quote = parts[0].upper(), parts[1].upper()

        # Get execution price
        ticker = self.get_ticker(symbol)
        exec_price = price or (ticker['ask'] if side == 'buy' else ticker['bid'])

        # Calculate order value
        order_value = amount * exec_price

        # Check balances
        if side == "buy":
            if self.paper_balances.get(quote, 0) < order_value:
                return {"status": "failed", "error": f"Insufficient {quote} balance"}
            # Execute
            self.paper_balances[quote] = self.paper_balances.get(quote, 0) - order_value
            self.paper_balances[base] = self.paper_balances.get(base, 0) + amount
        else:
            if self.paper_balances.get(base, 0) < amount:
                return {"status": "failed", "error": f"Insufficient {base} balance"}
            # Execute
            self.paper_balances[base] = self.paper_balances.get(base, 0) - amount
            self.paper_balances[quote] = self.paper_balances.get(quote, 0) + order_value

        order_id = f"paper_{int(time.time() * 1000)}"

        result = {
            "status": "filled",
            "order_id": order_id,
            "exchange": "paper",
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "amount": amount,
            "price": exec_price,
            "executed_amount": amount,
            "cost": order_value,
            "timestamp": time.time(),
            "paper_mode": True,
        }

        self.paper_trades.append(result)

        if self.trade_logger:
            self.trade_logger.log_trade(result)

        logger.info(f"Paper trade: {side} {amount} {base} @ {exec_price} {quote}")

        return result

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        """Cancel an order."""
        if self.paper_mode:
            return {"order_id": order_id, "cancelled": True, "paper_mode": True}
        return {"status": "failed", "error": "Not implemented"}

    def get_open_orders(self) -> List[Dict]:
        """Get open orders."""
        if self.paper_mode:
            return []  # Paper trades execute instantly
        return []

    def get_trade_history(self) -> List[Dict]:
        """Get trade history."""
        if self.paper_mode:
            return self.paper_trades
        return []

    def reset_paper_account(self, initial_balances: Dict[str, float] = None):
        """Reset paper trading account."""
        self.paper_balances = initial_balances or {"USD": 10000.0, "BTC": 0.0, "ETH": 0.0}
        self.paper_orders = []
        self.paper_trades = []
        logger.info("Paper trading account reset")

    def borrow(self, symbol: str, amount: float, rate: float = None) -> Dict[str, Any]:
        """Borrow assets (margin trading)."""
        if self.paper_mode:
            self.paper_balances[symbol] = self.paper_balances.get(symbol, 0) + amount
            return {
                "status": "success",
                "symbol": symbol,
                "amount": amount,
                "rate": rate or 0.0001,
                "paper_mode": True,
            }
        return {"status": "failed", "error": "Margin not implemented for live trading"}

    def repay(self, symbol: str, amount: float) -> Dict[str, Any]:
        """Repay borrowed assets."""
        if self.paper_mode:
            if self.paper_balances.get(symbol, 0) >= amount:
                self.paper_balances[symbol] -= amount
                return {"status": "success", "symbol": symbol, "amount": amount, "paper_mode": True}
            return {"status": "failed", "error": "Insufficient balance to repay"}
        return {"status": "failed", "error": "Margin not implemented for live trading"}
