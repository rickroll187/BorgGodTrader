class PositionManager:
    def __init__(self, portfolio_service, risk_limits):
        self.portfolio_service = portfolio_service
        self.risk_limits = risk_limits

    def size_position(self, signal, confidence, asset):
        balance = self.portfolio_service.get_balance(asset)
        max_size = self.risk_limits.get("max_pos_size", 0.2)
        return min(balance * confidence, balance * max_size)

    def check_stop_loss(self, position, current_price):
        if current_price < position["entry"] * (1 - position["stop_loss"]):
            return True
        return False

    def dynamic_trailing_stop(self, position, current_price):
        pass

    def auto_hedge(self, asset, portfolio):
        pass

    def get_exposure_report(self):
        # Stub: Return current exposure
        return {"exposure": "stub"}