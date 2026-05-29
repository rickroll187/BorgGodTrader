import time
import json
import os

class InterestTracker:
    """
    Tracks and accrues interest on open margin positions.
    Supports persistent storage (autosave on update).
    """
    def __init__(self, state_file="interest_positions.json"):
        self.positions = {}  # symbol: {amount, rate, last_update, accrued_interest}
        self.state_file = state_file
        self._load_state()

    def add_position(self, symbol, amount, rate):
        self.positions[symbol] = {
            "amount": amount,
            "rate": rate or 0.05,
            "last_update": time.time(),
            "accrued_interest": 0.0
        }
        self._save_state()

    def update_position(self, symbol, new_amount):
        if symbol in self.positions:
            self.accrue_interest(symbol)
            self.positions[symbol]["amount"] = new_amount
            self._save_state()

    def remove_position(self, symbol):
        if symbol in self.positions:
            del self.positions[symbol]
            self._save_state()

    def accrue_interest(self, symbol):
        pos = self.positions[symbol]
        now = time.time()
        elapsed = now - pos["last_update"]
        interest = pos["amount"] * pos["rate"] * (elapsed / (365*24*3600))
        pos["accrued_interest"] += interest
        pos["last_update"] = now
        self.positions[symbol] = pos

    def get_interest(self, symbol):
        if symbol in self.positions:
            self.accrue_interest(symbol)
            self._save_state()
            return self.positions[symbol]["accrued_interest"]
        return 0.0

    def get_all_accrued(self):
        for symbol in self.positions:
            self.accrue_interest(symbol)
        self._save_state()
        return {s: p["accrued_interest"] for s, p in self.positions.items()}

    def get_all_interest(self):
        """Alias for get_all_accrued for API compatibility."""
        return self.get_all_accrued()

    def start_tracking(self, symbol, amount, rate):
        """Alias for add_position for API compatibility."""
        self.add_position(symbol, amount, rate)

    def stop_tracking(self, symbol):
        """Alias for remove_position for API compatibility."""
        self.remove_position(symbol)

    def _save_state(self):
        with open(self.state_file, "w") as f:
            json.dump(self.positions, f)

    def _load_state(self):
        if os.path.isfile(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    self.positions = json.load(f)
            except Exception:
                self.positions = {}