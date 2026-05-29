import time
import logging
from typing import Dict, Any

from services.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)


class Strategy(BaseStrategy):
    """
    Funding Rate Strategy (Basis Trade).

    When funding rates are highly positive, longs are paying shorts.
    Opening short on perpetuals while long spot = "cash and carry" yield.

    Also uses funding rate as directional signal:
    - Extreme positive funding → market overleveraged long → correction likely
    - Extreme negative funding → market overleveraged short → squeeze likely
    """

    name = "funding_rate"
    description = "Funding rate contrarian + basis trade detection"

    def __init__(self, core, symbol: str = "ETH/USD",
                 extreme_positive: float = 0.01,   # 0.01 = 1% per 8h (very high)
                 extreme_negative: float = -0.005,  # -0.005 = -0.5% per 8h
                 trade_amount: float = 0.05):
        super().__init__(core)
        self.symbol = symbol
        self.extreme_positive = extreme_positive
        self.extreme_negative = extreme_negative
        self.trade_amount = trade_amount
        self._last_fetch = 0
        self._cached_data = None

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        now = time.time()

        # Cache funding data for 5 minutes
        if not self._cached_data or now - self._last_fetch > 300:
            binance_sym = self.symbol.replace("/", "").replace("USD", "USDT")
            self._cached_data = self.core.data_sources.get_futures_data(binance_sym)
            self._last_fetch = now

        data = self._cached_data or {}
        funding_rate = data.get("rate", 0)
        open_interest = data.get("open_interest", 0)
        ls_ratio = data.get("long_short_ratio", 1.0)

        if funding_rate == 0:
            return {"signal": "hold", "confidence": 0, "reason": "No funding data"}

        annual_funding = funding_rate * 3 * 365 * 100  # 3 payments/day, annualized %

        # Extreme positive funding = overleveraged longs → price correction likely
        if funding_rate >= self.extreme_positive:
            rate_intensity = min((funding_rate - self.extreme_positive) / self.extreme_positive, 1.0)
            confidence = min(0.80, 0.55 + rate_intensity * 0.25)

            # Stronger signal if long/short ratio also extreme
            if ls_ratio and ls_ratio > 1.5:
                confidence = min(0.88, confidence + 0.08)

            return {
                "signal": "sell",
                "confidence": confidence,
                "symbol": self.symbol,
                "amount": self.trade_amount,
                "reason": (
                    f"Extreme positive funding {funding_rate*100:.4f}% "
                    f"(annualized {annual_funding:.1f}%) "
                    f"L/S={ls_ratio:.2f}"
                ),
                "funding_rate": funding_rate,
                "open_interest": open_interest,
                "ls_ratio": ls_ratio,
            }

        # Extreme negative funding = overleveraged shorts → short squeeze likely
        if funding_rate <= self.extreme_negative:
            rate_intensity = min((abs(funding_rate) - abs(self.extreme_negative)) / abs(self.extreme_negative), 1.0)
            confidence = min(0.80, 0.55 + rate_intensity * 0.25)

            if ls_ratio and ls_ratio < 0.7:
                confidence = min(0.88, confidence + 0.08)

            return {
                "signal": "buy",
                "confidence": confidence,
                "symbol": self.symbol,
                "amount": self.trade_amount,
                "reason": (
                    f"Extreme negative funding {funding_rate*100:.4f}% "
                    f"potential short squeeze L/S={ls_ratio:.2f}"
                ),
                "funding_rate": funding_rate,
                "open_interest": open_interest,
                "ls_ratio": ls_ratio,
            }

        return {
            "signal": "hold",
            "confidence": 0,
            "reason": f"Funding neutral {funding_rate*100:.4f}% (ann. {annual_funding:.1f}%)",
        }
