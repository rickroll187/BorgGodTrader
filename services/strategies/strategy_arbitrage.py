import time
import logging
from typing import Dict, Any, List, Optional

from services.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class Strategy(BaseStrategy):
    """
    Cross-Exchange Arbitrage Strategy.

    Monitors price spreads across Kraken, Gemini, and Binance public API.
    Executes when spread exceeds transaction costs + minimum profit threshold.

    Requires accounts on at least two exchanges to be effective.
    """

    name = "arbitrage"
    description = "Cross-exchange price arbitrage"

    def __init__(self, core, min_spread_pct: float = 0.3,
                 symbols: List[str] = None, trade_amount: float = 0.01):
        super().__init__(core)
        self.min_spread_pct = min_spread_pct
        self.symbols = symbols or ["BTC/USD", "ETH/USD"]
        self.trade_amount = trade_amount
        self.last_opportunity: Optional[Dict] = None

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Find best arbitrage opportunity right now."""
        best_opportunity = None
        best_profit_pct = 0

        for symbol in self.symbols:
            opportunity = self._check_symbol(symbol)
            if opportunity and opportunity["spread_pct"] > best_profit_pct:
                best_profit_pct = opportunity["spread_pct"]
                best_opportunity = opportunity

        if best_opportunity and best_profit_pct >= self.min_spread_pct:
            self.last_opportunity = best_opportunity
            return {
                "signal": "buy",
                "confidence": min(0.95, 0.5 + best_profit_pct / 2),
                "symbol": best_opportunity["symbol"],
                "amount": self.trade_amount,
                "reason": (
                    f"Arb: buy {best_opportunity['buy_exchange']} @ {best_opportunity['buy_price']:.2f} "
                    f"sell {best_opportunity['sell_exchange']} @ {best_opportunity['sell_price']:.2f} "
                    f"spread={best_profit_pct:.3f}%"
                ),
                "arb_details": best_opportunity,
            }

        return {
            "signal": "hold",
            "confidence": 0,
            "reason": f"No arb opportunity above {self.min_spread_pct}%",
            "best_spread": best_profit_pct,
        }

    def execute(self, signal: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute both legs of the arbitrage simultaneously."""
        arb = signal.get("arb_details", {})
        if not arb:
            return {"status": "failed", "error": "No arb details"}

        symbol = arb["symbol"]
        amount = signal.get("amount", self.trade_amount)

        buy_executor = self.core.get_executors().get(arb["buy_exchange"])
        sell_executor = self.core.get_executors().get(arb["sell_exchange"])

        if not buy_executor or not sell_executor:
            return {"status": "failed", "error": "Missing executor for one or both exchanges"}

        # Execute both legs
        results = {}
        try:
            results["buy"] = buy_executor.buy(symbol, amount)
            results["sell"] = sell_executor.sell(symbol, amount)

            gross_profit = (arb["sell_price"] - arb["buy_price"]) * amount
            results["gross_profit"] = gross_profit
            results["status"] = "executed"

            logger.info(f"Arb executed: profit={gross_profit:.4f} {symbol}")

        except Exception as e:
            results["status"] = "failed"
            results["error"] = str(e)
            logger.error(f"Arb execution failed: {e}")

        return results

    def _check_symbol(self, symbol: str) -> Optional[Dict]:
        """Get quotes from all exchanges for a symbol."""
        quotes = {}

        # Kraken
        try:
            ticker = self.core.kraken_executor.get_ticker(symbol)
            if ticker:
                quotes["kraken"] = {
                    "ask": ticker.get("ask", 0),
                    "bid": ticker.get("bid", 0),
                }
        except Exception:
            pass

        # Gemini
        try:
            ticker = self.core.gemini_executor.get_ticker(symbol)
            if ticker:
                quotes["gemini"] = {
                    "ask": ticker.get("ask", 0),
                    "bid": ticker.get("bid", 0),
                }
        except Exception:
            pass

        # Binance (public, no auth)
        try:
            binance_sym = symbol.replace("/", "").replace("USD", "USDT")
            from services.data.data_sources import DataSources
            ds = DataSources()
            binance_price = ds.get_cross_cex_price(binance_sym)
            if binance_price:
                quotes["binance"] = {
                    "ask": binance_price * 1.0001,
                    "bid": binance_price * 0.9999,
                }
        except Exception:
            pass

        if len(quotes) < 2:
            return None

        # Find best buy (lowest ask) and best sell (highest bid)
        best_buy = min(quotes.items(), key=lambda x: x[1]["ask"] or float("inf"))
        best_sell = max(quotes.items(), key=lambda x: x[1]["bid"])

        if best_buy[0] == best_sell[0]:
            return None

        buy_price = best_buy[1]["ask"]
        sell_price = best_sell[1]["bid"]

        if buy_price <= 0 or sell_price <= 0:
            return None

        spread_pct = (sell_price - buy_price) / buy_price * 100

        return {
            "symbol": symbol,
            "buy_exchange": best_buy[0],
            "buy_price": buy_price,
            "sell_exchange": best_sell[0],
            "sell_price": sell_price,
            "spread_pct": spread_pct,
            "timestamp": time.time(),
        }

    def get_current_opportunities(self) -> List[Dict]:
        """Get all current arbitrage opportunities."""
        opportunities = []
        for symbol in self.symbols:
            opp = self._check_symbol(symbol)
            if opp and opp["spread_pct"] > 0:
                opportunities.append(opp)
        return sorted(opportunities, key=lambda x: x["spread_pct"], reverse=True)
