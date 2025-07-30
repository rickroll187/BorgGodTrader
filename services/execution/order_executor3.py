class OrderExecutor:
    def __init__(self, logger=None):
        self.logger = logger

    def log_trade(self, trade):
        if self.logger:
            self.logger.log_trade(trade)