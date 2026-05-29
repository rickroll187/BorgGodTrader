import time
import logging
from typing import Dict, Any

from services.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class Strategy(BaseStrategy):
    """
    Fear & Greed Contrarian Strategy.

    "Be fearful when others are greedy, and greedy when others are fearful."
    - Warren Buffett

    Combines the Crypto Fear & Greed Index with RSI and on-chain sentiment
    to take contrarian positions at extreme sentiment levels.
    """

    name = "fear_greed_contrarian"
    description = "Contrarian strategy using Fear & Greed Index + RSI"

    def __init__(self, core, extreme_fear_threshold: float = 20,
                 extreme_greed_threshold: float = 80,
                 rsi_oversold: float = 35, rsi_overbought: float = 65,
                 symbol: str = "BTC/USD", trade_amount: float = 0.01):
        super().__init__(core)
        self.extreme_fear_threshold = extreme_fear_threshold
        self.extreme_greed_threshold = extreme_greed_threshold
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.symbol = symbol
        self.trade_amount = trade_amount

        self.price_history = []
        self._last_fg_fetch = 0
        self._fg_cache = None

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        asset = self.symbol.split("/")[0]
        price = self.core.tokeninfo_service.get_token_price(asset)

        if not price:
            return {"signal": "hold", "confidence": 0, "reason": "No price data"}

        self.price_history.append(price)

        # Get Fear & Greed (cached 1 hour)
        now = time.time()
        if not self._fg_cache or now - self._last_fg_fetch > 3600:
            self._fg_cache = self.core.data_sources.get_fear_greed_index()
            self._last_fg_fetch = now

        fg = self._fg_cache or {"value": 50, "classification": "Neutral"}
        fg_value = fg.get("value", 50)
        fg_class = fg.get("classification", "Neutral")

        # Get market sentiment from news
        news_sentiment = self.core.news_scraper.get_sentiment_summary([asset])
        news_score = news_sentiment.get("score", 0)

        # RSI
        rsi = self._rsi(self.price_history, 14)

        reasons = []

        # Extreme fear = potential buy
        if fg_value <= self.extreme_fear_threshold and rsi <= self.rsi_oversold:
            fear_depth = (self.extreme_fear_threshold - fg_value) / self.extreme_fear_threshold
            rsi_depth = (self.rsi_oversold - rsi) / self.rsi_oversold
            confidence = min(0.85, 0.55 + fear_depth * 0.2 + rsi_depth * 0.1)

            # News confirming fear? Even better (deeper dip)
            if news_score < -0.2:
                confidence = min(0.90, confidence + 0.05)
                reasons.append("news also bearish")

            return {
                "signal": "buy",
                "confidence": confidence,
                "symbol": self.symbol,
                "amount": self.trade_amount,
                "reason": f"Extreme fear FG={fg_value} ({fg_class}), RSI={rsi:.1f}" + (f", {', '.join(reasons)}" if reasons else ""),
                "fear_greed": fg_value,
                "rsi": rsi,
                "price": price,
            }

        # Extreme greed = potential sell
        if fg_value >= self.extreme_greed_threshold and rsi >= self.rsi_overbought:
            greed_depth = (fg_value - self.extreme_greed_threshold) / (100 - self.extreme_greed_threshold)
            rsi_depth = (rsi - self.rsi_overbought) / (100 - self.rsi_overbought)
            confidence = min(0.85, 0.55 + greed_depth * 0.2 + rsi_depth * 0.1)

            if news_score > 0.2:
                confidence = min(0.90, confidence + 0.05)
                reasons.append("news also bullish")

            return {
                "signal": "sell",
                "confidence": confidence,
                "symbol": self.symbol,
                "amount": self.trade_amount,
                "reason": f"Extreme greed FG={fg_value} ({fg_class}), RSI={rsi:.1f}" + (f", {', '.join(reasons)}" if reasons else ""),
                "fear_greed": fg_value,
                "rsi": rsi,
                "price": price,
            }

        return {
            "signal": "hold",
            "confidence": 0,
            "reason": f"FG={fg_value} ({fg_class}), RSI={rsi:.1f}",
        }

    def _rsi(self, prices, period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        deltas = [prices[i] - prices[i-1] for i in range(len(prices)-period, len(prices))]
        gains = sum(d for d in deltas if d > 0) / period
        losses = sum(-d for d in deltas if d < 0) / period
        if losses == 0:
            return 100.0
        return 100 - (100 / (1 + gains / losses))
