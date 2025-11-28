class KrakenExecutor:
    def __init__(self, api_key, api_secret, logger=None):
        self.api_key = api_key
        self.api_secret = api_secret
        self.logger = logger

    def buy(self, symbol, amount):
        if self.logger:
            self.logger.log_trade({"type": "kraken", "side": "buy", "symbol": symbol, "amount": amount})
        return {"status": "submitted", "side": "buy", "symbol": symbol, "amount": amount}

    def sell(self, symbol, amount):
        if self.logger:
            self.logger.log_trade({"type": "kraken", "side": "sell", "symbol": symbol, "amount": amount})
        return {"status": "submitted", "side": "sell", "symbol": symbol, "amount": amount}
