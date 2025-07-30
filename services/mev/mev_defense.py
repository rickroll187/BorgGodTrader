class MEVDefense:
    """
    Defends against on-chain sandwich attacks and MEV.
    """
    def __init__(self, slippage_threshold=0.003):
        self.slippage_threshold = slippage_threshold

    def is_sandwich_risk(self, expected_slippage):
        return expected_slippage > self.slippage_threshold

    def protect_order(self, order, market_data):
        if self.is_sandwich_risk(order.get("slippage", 0)):
            order["max_slippage"] = self.slippage_threshold
            order["execution_mode"] = "anti-MEV"
        return order