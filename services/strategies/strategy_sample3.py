import random

class Strategy:
    def __init__(self, core):
        self.core = core
        self.enabled = True

    def run(self, context):
        # Example: randomly buy or sell on CEX
        if not self.enabled:
            return
        action = random.choice(["buy", "sell"])
        amount = 0.01
        if action == "buy":
            self.core.kraken_executor.buy("ETHUSD", amount)
        else:
            self.core.kraken_executor.sell("ETHUSD", amount)
        self.core.trade_logger.log_trade({
            "type": "SampleStrategy",
            "action": action,
            "amount": amount
        })