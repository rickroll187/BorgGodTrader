class SmartOrderRouter:
    def __init__(self, executors):
        self.executors = executors

    def route_order(self, symbol, side, amount, max_slippage=0.005, venues=None):
        results = []
        venues = venues or list(self.executors.keys())
        split_amount = amount / len(venues)
        for venue in venues:
            executor = self.executors[venue]
            if hasattr(executor, side):
                func = getattr(executor, side)
                results.append(func(symbol, split_amount))
        return results
