import logging
from collections import deque
from typing import Dict, Any, List

from services.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class Strategy(BaseStrategy):
    """
    RSI Mean Reversion Strategy.

    Buys into oversold dips (RSI < 30) with confirmation from Bollinger Bands.
    Sells into overbought peaks (RSI > 70).
    Ideal for ranging/sideways markets.
    """

    name = "rsi_mean_reversion"
    description = "RSI oversold/overbought with Bollinger Band confirmation"

    def __init__(self, core, rsi_period: int = 14, bb_period: int = 20,
                 bb_std: float = 2.0, oversold: float = 30.0,
                 overbought: float = 70.0, symbol: str = "ETH/USD",
                 trade_amount: float = 0.05):
        super().__init__(core)
        self.rsi_period = rsi_period
        self.bb_period = bb_period
        self.bb_std = bb_std
        self.oversold = oversold
        self.overbought = overbought
        self.symbol = symbol
        self.trade_amount = trade_amount
        self.prices: deque = deque(maxlen=100)

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        asset = self.symbol.split("/")[0]
        price = self.core.tokeninfo_service.get_token_price(asset)

        if not price:
            return {"signal": "hold", "confidence": 0, "reason": "No price data"}

        self.prices.append(price)
        prices = list(self.prices)

        if len(prices) < max(self.rsi_period, self.bb_period) + 1:
            return {"signal": "hold", "confidence": 0, "reason": "Building history"}

        rsi = self._rsi(prices)
        bb_upper, bb_mid, bb_lower = self._bollinger_bands(prices)
        bb_width_pct = (bb_upper - bb_lower) / bb_mid * 100

        # Only trade when BB width suggests a ranging market (not trending hard)
        if bb_width_pct > 15:
            return {"signal": "hold", "confidence": 0, "reason": f"High volatility BB={bb_width_pct:.1f}%"}

        if rsi < self.oversold and price <= bb_lower * 1.01:
            # Deep oversold at lower band
            distance_below = (bb_lower - price) / bb_lower
            confidence = min(0.85, 0.5 + (self.oversold - rsi) / 20 + distance_below * 5)
            return {
                "signal": "buy",
                "confidence": confidence,
                "symbol": self.symbol,
                "amount": self.trade_amount,
                "reason": f"RSI oversold={rsi:.1f}, price at/below BB lower={bb_lower:.2f}",
                "rsi": rsi,
                "bb_lower": bb_lower,
                "price": price,
            }

        if rsi > self.overbought and price >= bb_upper * 0.99:
            # Deep overbought at upper band
            distance_above = (price - bb_upper) / bb_upper
            confidence = min(0.85, 0.5 + (rsi - self.overbought) / 20 + distance_above * 5)
            return {
                "signal": "sell",
                "confidence": confidence,
                "symbol": self.symbol,
                "amount": self.trade_amount,
                "reason": f"RSI overbought={rsi:.1f}, price at/above BB upper={bb_upper:.2f}",
                "rsi": rsi,
                "bb_upper": bb_upper,
                "price": price,
            }

        return {
            "signal": "hold",
            "confidence": 0,
            "reason": f"RSI={rsi:.1f} BB_w={bb_width_pct:.1f}%",
        }

    def _rsi(self, prices: List[float]) -> float:
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-self.rsi_period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-self.rsi_period:]]
        avg_gain = sum(gains) / self.rsi_period
        avg_loss = sum(losses) / self.rsi_period
        if avg_loss == 0:
            return 100.0
        return 100 - (100 / (1 + avg_gain / avg_loss))

    def _bollinger_bands(self, prices: List[float]):
        import statistics
        window = prices[-self.bb_period:]
        mid = sum(window) / len(window)
        std = statistics.stdev(window)
        return mid + self.bb_std * std, mid, mid - self.bb_std * std
