import time
import logging
import json
import os

class MarginManager:
    """
    Advanced lifecycle manager for margin debt: handles borrowing, repaying, PnL, event logging, and persistent storage.
    Integrates with broker, portfolio_service, interest_tracker, and supports auto-liquidation hooks.
    """
    def __init__(
        self,
        broker,
        portfolio_service,
        interest_tracker,
        event_log_file='margin_events.jsonl',
        state_file='margin_positions.json'
    ):
        self.broker = broker
        self.portfolio_service = portfolio_service
        self.interest_tracker = interest_tracker
        self.margin_positions = {}  # key: symbol, value: dict
        self.event_log_file = event_log_file
        self.state_file = state_file
        self.logger = logging.getLogger("MarginManager")
        self._load_state()

    def borrow(self, symbol, amount, rate=None):
        tx = self.broker.borrow(symbol, amount, rate)
        self.margin_positions[symbol] = {
            "amount": amount,
            "borrow_time": time.time(),
            "rate": rate,
            "last_interest_update": time.time(),
        }
        self.interest_tracker.add_position(symbol, amount, rate)
        self._log_event("borrow", symbol, amount, rate, tx)
        self._save_state()
        return tx

    def repay(self, symbol, amount):
        tx = self.broker.repay(symbol, amount)
        if symbol in self.margin_positions:
            pos = self.margin_positions[symbol]
            pos["amount"] -= amount
            if pos["amount"] <= 0:
                del self.margin_positions[symbol]
                self.interest_tracker.remove_position(symbol)
            else:
                self.margin_positions[symbol] = pos
                self.interest_tracker.update_position(symbol, pos["amount"])
        self._log_event("repay", symbol, amount, None, tx)
        self._save_state()
        return tx

    def get_margin_status(self, symbol):
        debt = self.margin_positions.get(symbol, {}).get("amount", 0)
        interest = self.interest_tracker.get_interest(symbol)
        margin_ratio = self.portfolio_service.get_margin_ratio(symbol)
        return {
            "debt": debt,
            "accrued_interest": interest,
            "margin_ratio": margin_ratio,
        }

    def get_all_positions(self):
        summary = {}
        for symbol in self.margin_positions:
            summary[symbol] = self.get_margin_status(symbol)
        return summary

    def auto_liquidate(self, symbol):
        """Repay full position if possible (auto-liquidation)."""
        if symbol in self.margin_positions:
            amount = self.margin_positions[symbol]["amount"]
            self.logger.warning(f"Auto-liquidating {symbol} for amount {amount}")
            tx = self.repay(symbol, amount)
            self._log_event("auto_liquidate", symbol, amount, None, tx)
            return tx
        return None

    def _log_event(self, action, symbol, amount, rate, tx):
        event = {
            "action": action,
            "symbol": symbol,
            "amount": amount,
            "rate": rate,
            "tx": str(tx),
            "timestamp": time.time()
        }
        self.logger.info(f"Margin event: {event}")
        with open(self.event_log_file, "a") as f:
            f.write(json.dumps(event) + "\n")

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.margin_positions, f)

    def _load_state(self):
        if os.path.isfile(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    self.margin_positions = json.load(f)
            except Exception:
                self.margin_positions = {}

    def reload_state(self):
        self._load_state()