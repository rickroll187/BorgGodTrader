class SmartOrderRouter:
    def __init__(self, executors):
        self.executors = executors

    def route_order(self, symbol, side, amount, max_slippage=0.005, venues=None):
        results = []
        if venues is None:
            venues = list(self.executors.keys())
        split_amount = amount / len(venues)
        for venue in venues:
            exec = self.executors[venue]
            if hasattr(exec, side):
                func = getattr(exec, side)
                results.append(func(symbol, split_amount))
        return results