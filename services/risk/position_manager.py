class PositionManager:
    def __init__(self, portfolio_service, risk_limits):
        self.portfolio_service = portfolio_service
        self.risk_limits = risk_limits

    def size_position(self, signal, confidence, asset):
        balance = self.portfolio_service.get_balances().get(asset, 0)
        max_size = self.risk_limits.get("max_pos_size", 0.2)
        return min(balance * confidence, balance * max_size)

    def check_stop_loss(self, position, current_price):
        return current_price < position["entry"] * (1 - position.get("stop_loss", 0))

    def dynamic_trailing_stop(self, position, current_price):
        return None

    def auto_hedge(self, asset, portfolio):
        return None

    def get_exposure_report(self):
        return {"exposure": "stub"}
