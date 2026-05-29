import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class BaseStrategy(ABC):
    """
    Base class for all trading strategies.
    Extend this to create custom strategies.
    """

    name: str = "base"
    description: str = "Base strategy class"

    def __init__(self, core):
        self.core = core
        self.enabled = True
        self.last_run: Optional[float] = None
        self.last_signal: Optional[Dict[str, Any]] = None
        self.positions: Dict[str, float] = {}

    @abstractmethod
    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze market data and return signal.

        Returns:
            Dict with keys: signal ("buy", "sell", "hold"), confidence (0-1), reason
        """
        pass

    def run(self, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute the strategy."""
        context = context or {}
        self.last_run = time.time()

        try:
            signal = self.analyze(context)
            self.last_signal = signal

            if signal.get('signal') in ('buy', 'sell') and signal.get('confidence', 0) > 0.7:
                if self.should_execute(signal):
                    result = self.execute(signal, context)
                    return {"signal": signal, "executed": True, "result": result}

            return {"signal": signal, "executed": False}

        except Exception as e:
            logger.error(f"Strategy {self.name} error: {e}")
            return {"error": str(e)}

    def should_execute(self, signal: Dict[str, Any]) -> bool:
        """Check if we should execute based on risk limits."""
        # Override in subclass for custom risk checks
        return self.enabled

    def execute(self, signal: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a trade based on signal."""
        symbol = signal.get('symbol', context.get('symbol', 'BTC/USD'))
        side = signal['signal']
        amount = signal.get('amount', self._calculate_position_size(symbol, signal))

        return self.core.execute_trade(
            symbol=symbol,
            side=side,
            amount=amount
        )

    def _calculate_position_size(self, symbol: str, signal: Dict[str, Any]) -> float:
        """Calculate appropriate position size based on risk parameters."""
        # Get portfolio value
        portfolio = self.core.portfolio_service.get_portfolio_overview(self.core.tokeninfo_service)
        total_value = portfolio.get('total_usd', 10000)

        # Max position size from config
        max_size_pct = self.core.max_position_size

        # Adjust by confidence
        confidence = signal.get('confidence', 0.5)
        position_pct = max_size_pct * confidence

        # Get current price
        price = self.core.tokeninfo_service.get_token_price(symbol.split('/')[0])
        if not price:
            return 0.01  # Minimum fallback

        return (total_value * position_pct) / price

    def get_status(self) -> Dict[str, Any]:
        """Get strategy status."""
        return {
            "name": self.name,
            "enabled": self.enabled,
            "last_run": self.last_run,
            "last_signal": self.last_signal,
            "positions": self.positions,
        }
