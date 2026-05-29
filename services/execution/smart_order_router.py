import os
import time
import logging
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)


class SmartOrderRouter:
    """
    Smart Order Router that finds the best execution venue for orders.
    Compares prices across multiple exchanges and routes to the best one.
    """

    def __init__(self, executors: Dict[str, Any]):
        """
        Args:
            executors: Dict mapping exchange names to executor instances
                       e.g., {"kraken": KrakenExecutor(), "gemini": GeminiExecutor()}
        """
        self.executors = executors
        self.fee_rates = {
            "kraken": {"maker": 0.0016, "taker": 0.0026},
            "gemini": {"maker": 0.002, "taker": 0.004},
            "defi": {"maker": 0.003, "taker": 0.003},  # Uniswap fee tier
        }
        self.last_quotes: Dict[str, Dict] = {}

    def add_executor(self, name: str, executor: Any, fees: Dict[str, float] = None):
        """Add a new executor to the router."""
        self.executors[name] = executor
        if fees:
            self.fee_rates[name] = fees

    def remove_executor(self, name: str):
        """Remove an executor from the router."""
        self.executors.pop(name, None)
        self.fee_rates.pop(name, None)

    def get_quotes(self, symbol: str, side: str, amount: float) -> Dict[str, Dict]:
        """
        Get quotes from all available exchanges in parallel.

        Returns dict of exchange -> {price, fee, total_cost, available}
        """
        quotes = {}

        def fetch_quote(name: str, executor: Any) -> tuple:
            try:
                if hasattr(executor, 'get_ticker'):
                    ticker = executor.get_ticker(symbol)
                    if ticker:
                        price = ticker.get('ask') if side == 'buy' else ticker.get('bid')
                        if price:
                            fees = self.fee_rates.get(name, {"taker": 0.003})
                            fee_amount = amount * price * fees['taker']
                            return name, {
                                "price": price,
                                "fee_rate": fees['taker'],
                                "fee_amount": fee_amount,
                                "total_cost": (amount * price) + fee_amount if side == 'buy' else (amount * price) - fee_amount,
                                "available": True,
                            }
            except Exception as e:
                logger.debug(f"Quote fetch failed for {name}: {e}")
            return name, {"available": False, "error": str(e) if 'e' in dir() else "No ticker"}

        with ThreadPoolExecutor(max_workers=len(self.executors)) as pool:
            futures = {pool.submit(fetch_quote, name, ex): name for name, ex in self.executors.items()}
            for future in as_completed(futures, timeout=5):
                try:
                    name, quote = future.result()
                    quotes[name] = quote
                except Exception as e:
                    logger.debug(f"Quote future failed: {e}")

        self.last_quotes[symbol] = {"quotes": quotes, "timestamp": time.time()}
        return quotes

    def find_best_exchange(self, symbol: str, side: str, amount: float) -> Optional[str]:
        """Find the best exchange for an order based on price + fees."""
        quotes = self.get_quotes(symbol, side, amount)

        available = {name: q for name, q in quotes.items() if q.get('available')}
        if not available:
            logger.warning(f"No available exchanges for {symbol}")
            return None

        if side == 'buy':
            # For buys, minimize total cost
            best = min(available.items(), key=lambda x: x[1]['total_cost'])
        else:
            # For sells, maximize proceeds
            best = max(available.items(), key=lambda x: x[1]['total_cost'])

        logger.info(f"Best exchange for {side} {amount} {symbol}: {best[0]} @ {best[1]['price']}")
        return best[0]

    def route_order(self, symbol: str, side: str, amount: float,
                    order_type: str = "market", price: float = None,
                    preferred_exchange: str = None) -> Dict[str, Any]:
        """
        Route and execute an order on the best available exchange.

        Args:
            symbol: Trading pair (e.g., "BTC/USD")
            side: "buy" or "sell"
            amount: Order amount
            order_type: "market" or "limit"
            price: Limit price (required for limit orders)
            preferred_exchange: Force routing to specific exchange
        """
        # Determine exchange
        if preferred_exchange and preferred_exchange in self.executors:
            exchange = preferred_exchange
        else:
            exchange = self.find_best_exchange(symbol, side, amount)

        if not exchange:
            return {
                "status": "failed",
                "error": "No available exchange",
                "symbol": symbol,
                "side": side,
                "amount": amount,
            }

        executor = self.executors[exchange]

        # Execute order
        try:
            if side == "buy":
                result = executor.buy(symbol, amount, price=price, order_type=order_type)
            else:
                result = executor.sell(symbol, amount, price=price, order_type=order_type)

            result['routed_exchange'] = exchange
            result['routing_quotes'] = self.last_quotes.get(symbol, {}).get('quotes', {})

            return result

        except Exception as e:
            logger.error(f"Order execution failed on {exchange}: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "exchange": exchange,
                "symbol": symbol,
                "side": side,
                "amount": amount,
            }

    def split_order(self, symbol: str, side: str, total_amount: float,
                    max_exchanges: int = 3) -> List[Dict[str, Any]]:
        """
        Split a large order across multiple exchanges for better execution.
        Returns list of order results.
        """
        quotes = self.get_quotes(symbol, side, total_amount)
        available = [(name, q) for name, q in quotes.items() if q.get('available')]

        if not available:
            return [{"status": "failed", "error": "No available exchanges"}]

        # Sort by price (best first)
        if side == 'buy':
            available.sort(key=lambda x: x[1]['price'])
        else:
            available.sort(key=lambda x: x[1]['price'], reverse=True)

        # Split evenly across top exchanges
        exchanges_to_use = available[:max_exchanges]
        amount_per_exchange = total_amount / len(exchanges_to_use)

        results = []
        for name, quote in exchanges_to_use:
            result = self.route_order(
                symbol, side, amount_per_exchange,
                preferred_exchange=name
            )
            results.append(result)

        return results

    def get_arbitrage_opportunities(self, symbols: List[str] = None,
                                    min_spread_pct: float = 0.5) -> List[Dict]:
        """
        Find arbitrage opportunities across exchanges.

        Args:
            symbols: List of symbols to check (defaults to common pairs)
            min_spread_pct: Minimum spread percentage to report
        """
        if symbols is None:
            symbols = ["BTC/USD", "ETH/USD", "SOL/USD"]

        opportunities = []

        for symbol in symbols:
            quotes = self.get_quotes(symbol, "buy", 1)  # Get both bid/ask
            available = {name: q for name, q in quotes.items() if q.get('available')}

            if len(available) < 2:
                continue

            prices = [(name, q['price']) for name, q in available.items()]
            min_price = min(prices, key=lambda x: x[1])
            max_price = max(prices, key=lambda x: x[1])

            spread_pct = ((max_price[1] - min_price[1]) / min_price[1]) * 100

            if spread_pct >= min_spread_pct:
                opportunities.append({
                    "symbol": symbol,
                    "buy_exchange": min_price[0],
                    "buy_price": min_price[1],
                    "sell_exchange": max_price[0],
                    "sell_price": max_price[1],
                    "spread_pct": spread_pct,
                    "timestamp": time.time(),
                })

        return opportunities

    def health_check(self) -> Dict[str, bool]:
        """Check connectivity to all exchanges."""
        status = {}
        for name, executor in self.executors.items():
            try:
                if hasattr(executor, 'get_balance'):
                    executor.get_balance()
                    status[name] = True
                elif hasattr(executor, 'is_connected'):
                    status[name] = executor.is_connected()
                else:
                    status[name] = True  # Assume working if no health method
            except Exception:
                status[name] = False
        return status
