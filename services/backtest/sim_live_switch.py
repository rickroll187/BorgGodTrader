class SimLiveBroker:
    """
    Switch between simulation and live trading.
    """
    def __init__(self, mode="sim"):
        self.mode = mode  # "sim" or "live"
        self.sim_orders = []
        self.live_executor = None

    def send_order(self, order):
        if self.mode == "sim":
            self.sim_orders.append(order)
            return {"status": "simulated", "order": order}
        elif self.mode == "live" and self.live_executor:
            return self.live_executor.send_order(order)
        else:
            raise Exception("No live executor configured")