import time
import logging
import requests
from collections import deque
from typing import Dict, Any, List, Optional
from services.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class Strategy(BaseStrategy):
    """
    Moving Average Crossover Strategy.

    Buys when fast EMA crosses above slow EMA (golden cross).
    Sells when fast EMA crosses below slow EMA (death cross).
    Uses RSI to avoid buying into overbought conditions.
    """

    name = "ma_cross"
    description = "EMA crossover with RSI filter"

    def __init__(self, core, fast_period: int = 12, slow_period: int = 26,
                 rsi_period: int = 14, symbol: str = "BTC/USD",
                 trade_amount: float = 0.01):
        super().__init__(core)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.rsi_period = rsi_period
        self.symbol = symbol
        self.trade_amount = trade_amount

        # Keep rolling price history
        self.prices: deque = deque(maxlen=max(slow_period, rsi_period) * 3)
        self.last_cross: Optional[str] = None

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        # Fetch current price
        asset = self.symbol.split("/")[0]
        price = self.core.tokeninfo_service.get_token_price(asset)

        if not price:
            return {"signal": "hold", "confidence": 0, "reason": "No price data"}

        self.prices.append(price)

        if len(self.prices) < self.slow_period + 5:
            return {
                "signal": "hold",
                "confidence": 0,
                "reason": f"Building history ({len(self.prices)}/{self.slow_period})"
            }

        prices_list = list(self.prices)

        # Calculate EMAs
        fast_ema = self._ema(prices_list, self.fast_period)
        slow_ema = self._ema(prices_list, self.slow_period)

        if len(prices_list) >= self.slow_period + 1:
            prev_fast_ema = self._ema(prices_list[:-1], self.fast_period)
            prev_slow_ema = self._ema(prices_list[:-1], self.slow_period)
        else:
            prev_fast_ema = fast_ema
            prev_slow_ema = slow_ema

        # Calculate RSI
        rsi = self._rsi(prices_list, self.rsi_period)

        # Detect crossover
        fast_above = fast_ema > slow_ema
        was_fast_above = prev_fast_ema > prev_slow_ema
        golden_cross = fast_above and not was_fast_above
        death_cross = not fast_above and was_fast_above

        ema_spread_pct = abs(fast_ema - slow_ema) / slow_ema * 100

        if golden_cross and rsi < 70:
            confidence = min(0.9, 0.5 + ema_spread_pct * 0.1)
            return {
                "signal": "buy",
                "confidence": confidence,
                "symbol": self.symbol,
                "amount": self.trade_amount,
                "reason": f"Golden cross EMA{self.fast_period}/{self.slow_period}, RSI={rsi:.1f}",
                "fast_ema": fast_ema,
                "slow_ema": slow_ema,
                "rsi": rsi,
                "price": price,
            }

        if death_cross and rsi > 30:
            confidence = min(0.9, 0.5 + ema_spread_pct * 0.1)
            return {
                "signal": "sell",
                "confidence": confidence,
                "symbol": self.symbol,
                "amount": self.trade_amount,
                "reason": f"Death cross EMA{self.fast_period}/{self.slow_period}, RSI={rsi:.1f}",
                "fast_ema": fast_ema,
                "slow_ema": slow_ema,
                "rsi": rsi,
                "price": price,
            }

        return {
            "signal": "hold",
            "confidence": 0,
            "reason": f"EMA fast={fast_ema:.2f} slow={slow_ema:.2f} RSI={rsi:.1f}",
        }

    def _ema(self, prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average."""
        if len(prices) < period:
            return sum(prices) / len(prices)

        k = 2.0 / (period + 1)
        ema = sum(prices[:period]) / period

        for price in prices[period:]:
            ema = price * k + ema * (1 - k)

        return ema

    def _rsi(self, prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        if len(prices) < period + 1:
            return 50.0

        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0 for d in deltas[-period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-period:]]

        avg_gain = sum(gains) / period
        avg_loss = sum(losses) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))
