import time
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PositionManager:
    """
    Manages trading positions with risk limits and exposure tracking.
    """

    def __init__(self, portfolio_service, risk_limits: Dict[str, float]):
        self.portfolio_service = portfolio_service
        self.risk_limits = risk_limits
        self.positions: Dict[str, Dict[str, Any]] = {}
        self.position_history: List[Dict] = []
        self.initial_portfolio_value: Optional[float] = None
        self.peak_portfolio_value: Optional[float] = None

    def open_position(self, symbol: str, side: str, amount: float,
                      entry_price: float, stop_loss: float = None,
                      take_profit: float = None) -> Dict[str, Any]:
        """Open or add to a position."""

        # Check risk limits before opening
        if not self._check_risk_limits(symbol, amount, entry_price):
            return {"status": "rejected", "reason": "Risk limits exceeded"}

        position_id = f"{symbol}_{side}_{int(time.time())}"

        position = {
            "id": position_id,
            "symbol": symbol,
            "side": side,
            "amount": amount,
            "entry_price": entry_price,
            "current_price": entry_price,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "unrealized_pnl": 0,
            "opened_at": time.time(),
        }

        self.positions[position_id] = position
        logger.info(f"Opened position: {position_id}")

        return {"status": "opened", "position": position}

    def close_position(self, position_id: str, exit_price: float) -> Dict[str, Any]:
        """Close a position."""
        if position_id not in self.positions:
            return {"status": "error", "reason": "Position not found"}

        position = self.positions[position_id]
        pnl = self._calculate_pnl(position, exit_price)

        closed_position = {
            **position,
            "exit_price": exit_price,
            "realized_pnl": pnl,
            "closed_at": time.time(),
        }

        self.position_history.append(closed_position)
        del self.positions[position_id]

        logger.info(f"Closed position {position_id}: P&L = {pnl:.2f}")
        return {"status": "closed", "position": closed_position, "pnl": pnl}

    def _calculate_pnl(self, position: Dict, current_price: float) -> float:
        """Calculate P&L for a position."""
        entry = position["entry_price"]
        amount = position["amount"]

        if position["side"] == "long":
            return (current_price - entry) * amount
        else:  # short
            return (entry - current_price) * amount

    def update_prices(self, prices: Dict[str, float]):
        """Update current prices and check stop losses / take profits."""
        alerts = []

        for position_id, position in list(self.positions.items()):
            symbol = position["symbol"]
            if symbol in prices:
                current_price = prices[symbol]
                position["current_price"] = current_price
                position["unrealized_pnl"] = self._calculate_pnl(position, current_price)

                # Check stop loss
                if position.get("stop_loss"):
                    if position["side"] == "long" and current_price <= position["stop_loss"]:
                        alerts.append({"type": "stop_loss", "position_id": position_id})
                    elif position["side"] == "short" and current_price >= position["stop_loss"]:
                        alerts.append({"type": "stop_loss", "position_id": position_id})

                # Check take profit
                if position.get("take_profit"):
                    if position["side"] == "long" and current_price >= position["take_profit"]:
                        alerts.append({"type": "take_profit", "position_id": position_id})
                    elif position["side"] == "short" and current_price <= position["take_profit"]:
                        alerts.append({"type": "take_profit", "position_id": position_id})

        return alerts

    def _check_risk_limits(self, symbol: str, amount: float, price: float) -> bool:
        """Check if a new position would exceed risk limits."""
        position_value = amount * price

        # Get total portfolio value (would need prices)
        total_value = 100000  # Placeholder - should get from portfolio service

        # Check max position size
        max_pos_size = self.risk_limits.get("max_pos_size", 0.2)
        if position_value / total_value > max_pos_size:
            logger.warning(f"Position size {position_value/total_value:.2%} exceeds max {max_pos_size:.2%}")
            return False

        # Check drawdown
        if not self._check_drawdown():
            return False

        return True

    def _check_drawdown(self) -> bool:
        """Check if current drawdown exceeds limit."""
        max_dd = self.risk_limits.get("max_drawdown", 0.15)

        total_unrealized = sum(p.get("unrealized_pnl", 0) for p in self.positions.values())

        if self.peak_portfolio_value:
            current_value = self.peak_portfolio_value + total_unrealized
            drawdown = (self.peak_portfolio_value - current_value) / self.peak_portfolio_value

            if drawdown > max_dd:
                logger.warning(f"Drawdown {drawdown:.2%} exceeds max {max_dd:.2%}")
                return False

        return True

    def get_total_exposure(self) -> Dict[str, float]:
        """Get total exposure by symbol."""
        exposure = {}
        for position in self.positions.values():
            symbol = position["symbol"]
            value = position["amount"] * position["current_price"]
            if position["side"] == "short":
                value = -value
            exposure[symbol] = exposure.get(symbol, 0) + value
        return exposure

    def get_exposure_report(self) -> Dict[str, Any]:
        """Get comprehensive exposure report."""
        total_long = 0
        total_short = 0

        for position in self.positions.values():
            value = position["amount"] * position["current_price"]
            if position["side"] == "long":
                total_long += value
            else:
                total_short += value

        total_unrealized = sum(p.get("unrealized_pnl", 0) for p in self.positions.values())
        total_realized = sum(p.get("realized_pnl", 0) for p in self.position_history)

        return {
            "open_positions": len(self.positions),
            "total_long_exposure": total_long,
            "total_short_exposure": total_short,
            "net_exposure": total_long - total_short,
            "unrealized_pnl": total_unrealized,
            "realized_pnl": total_realized,
            "exposure_by_symbol": self.get_total_exposure(),
            "risk_limits": self.risk_limits,
        }

    def get_positions(self) -> List[Dict]:
        """Get all open positions."""
        return list(self.positions.values())

    def set_stop_loss(self, position_id: str, stop_loss: float):
        """Set or update stop loss for a position."""
        if position_id in self.positions:
            self.positions[position_id]["stop_loss"] = stop_loss

    def set_take_profit(self, position_id: str, take_profit: float):
        """Set or update take profit for a position."""
        if position_id in self.positions:
            self.positions[position_id]["take_profit"] = take_profit

    def close_all_positions(self, prices: Dict[str, float]) -> List[Dict]:
        """Close all open positions (panic button)."""
        results = []
        for position_id, position in list(self.positions.items()):
            symbol = position["symbol"]
            price = prices.get(symbol, position["current_price"])
            result = self.close_position(position_id, price)
            results.append(result)
        return results
