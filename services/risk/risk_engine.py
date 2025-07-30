import numpy as np

class RiskEngine:
    """
    Calculates real-time risk metrics for portfolio.
    """
    def __init__(self):
        self.positions = []

    def update_positions(self, positions):
        self.positions = positions

    def portfolio_delta(self):
        return float(np.sum([p['delta'] for p in self.positions]))

    def portfolio_gamma(self):
        return float(np.sum([p.get('gamma', 0) for p in self.positions]))

    def portfolio_vega(self):
        return float(np.sum([p.get('vega', 0) for p in self.positions]))

    def risk_overlay(self):
        return {
            "delta": self.portfolio_delta(),
            "gamma": self.portfolio_gamma(),
            "vega": self.portfolio_vega()
        }