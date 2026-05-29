import time
import logging
from collections import deque
from typing import Dict, Any, List

from services.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class Strategy(BaseStrategy):
    """
    Momentum / Trend-Following Strategy.

    Uses Rate of Change (ROC), Volume surge detection, and MACD histogram
    to identify strong trending moves and ride them.

    Best for breakout situations and strong directional markets.
    """

    name = "momentum"
    description = "ROC + Volume surge + MACD trend following"

    def __init__(self, core, roc_period: int = 10, macd_fast: int = 12,
                 macd_slow: int = 26, macd_signal: int = 9,
                 volume_surge_threshold: float = 2.0,
                 symbol: str = "BTC/USD", trade_amount: float = 0.01):
        super().__init__(core)
        self.roc_period = roc_period
        self.macd_fast = macd_fast
        self.macd_slow = macd_slow
        self.macd_signal = macd_signal
        self.volume_surge_threshold = volume_surge_threshold
        self.symbol = symbol
        self.trade_amount = trade_amount

        self.prices: deque = deque(maxlen=200)
        self.volumes: deque = deque(maxlen=50)

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        asset = self.symbol.split("/")[0]

        # Get price
        price = self.core.tokeninfo_service.get_token_price(asset)
        if not price:
            return {"signal": "hold", "confidence": 0, "reason": "No price data"}

        self.prices.append(price)

        # Try to get volume from market data
        mkt = self.core.tokeninfo_service.get_market_data(asset)
        volume = mkt.get("volume_24h", 0) if mkt else 0
        if volume:
            self.volumes.append(volume)

        prices = list(self.prices)

        min_needed = max(self.macd_slow, self.roc_period) + self.macd_signal + 5
        if len(prices) < min_needed:
            return {"signal": "hold", "confidence": 0, "reason": "Building history"}

        # Rate of Change
        roc = (prices[-1] - prices[-self.roc_period]) / prices[-self.roc_period] * 100

        # MACD
        macd_line, signal_line, histogram = self._macd(prices)

        # Volume surge
        volume_surge = False
        if len(self.volumes) >= 5:
            avg_vol = sum(list(self.volumes)[:-1]) / (len(self.volumes) - 1)
            if avg_vol > 0:
                current_vol_ratio = list(self.volumes)[-1] / avg_vol
                volume_surge = current_vol_ratio >= self.volume_surge_threshold

        # Determine signal
        bullish_macd = histogram > 0 and macd_line > signal_line
        bearish_macd = histogram < 0 and macd_line < signal_line

        if roc > 1.5 and bullish_macd:
            confidence = min(0.88, 0.5 + abs(roc) / 20 + (0.1 if volume_surge else 0))
            return {
                "signal": "buy",
                "confidence": confidence,
                "symbol": self.symbol,
                "amount": self.trade_amount,
                "reason": f"Momentum ROC={roc:.2f}% MACD bullish{' +volume' if volume_surge else ''}",
                "roc": roc,
                "macd": macd_line,
                "price": price,
            }

        if roc < -1.5 and bearish_macd:
            confidence = min(0.88, 0.5 + abs(roc) / 20 + (0.1 if volume_surge else 0))
            return {
                "signal": "sell",
                "confidence": confidence,
                "symbol": self.symbol,
                "amount": self.trade_amount,
                "reason": f"Momentum ROC={roc:.2f}% MACD bearish{' +volume' if volume_surge else ''}",
                "roc": roc,
                "macd": macd_line,
                "price": price,
            }

        return {
            "signal": "hold",
            "confidence": 0,
            "reason": f"ROC={roc:.2f}% MACD_hist={histogram:.4f}",
        }

    def _ema(self, prices: List[float], period: int) -> float:
        if len(prices) < period:
            return sum(prices) / len(prices)
        k = 2.0 / (period + 1)
        ema = sum(prices[:period]) / period
        for p in prices[period:]:
            ema = p * k + ema * (1 - k)
        return ema

    def _macd(self, prices: List[float]):
        fast_ema = self._ema(prices, self.macd_fast)
        slow_ema = self._ema(prices, self.macd_slow)
        macd_line = fast_ema - slow_ema

        # Signal line: EMA of MACD over last N periods
        macd_values = []
        for i in range(len(prices) - self.macd_signal, len(prices)):
            f = self._ema(prices[:i + 1], self.macd_fast)
            s = self._ema(prices[:i + 1], self.macd_slow)
            macd_values.append(f - s)

        signal_line = sum(macd_values) / len(macd_values) if macd_values else macd_line
        histogram = macd_line - signal_line

        return macd_line, signal_line, histogram
