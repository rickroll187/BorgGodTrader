import threading
import time

class LiquidationMonitor(threading.Thread):
    """
    Monitors margin ratios and triggers alerts/actions if liquidation is near.
    Can call auto-liquidation or send events to a dashboard.
    """
    def __init__(
        self,
        margin_manager,
        portfolio_service,
        threshold=1.15,
        poll_interval=30,
        on_liquidation_risk=None,
        dashboard_callback=None
    ):
        super().__init__()
        self.margin_manager = margin_manager
        self.portfolio_service = portfolio_service
        self.threshold = threshold
        self.poll_interval = poll_interval
        self.running = True
        self.on_liquidation_risk = on_liquidation_risk  # callback(symbol, margin_ratio)
        self.dashboard_callback = dashboard_callback    # e.g., push warning to GUI

    def run(self):
        while self.running:
            positions = self.margin_manager.get_all_positions()
            for symbol, status in positions.items():
                margin_ratio = status['margin_ratio']
                if margin_ratio is not None and margin_ratio < self.threshold:
                    msg = f"[LIQUIDATION WARNING] {symbol} margin ratio {margin_ratio:.2f} < {self.threshold}"
                    print(msg)
                    if self.dashboard_callback:
                        self.dashboard_callback(symbol, margin_ratio, msg)
                    if self.on_liquidation_risk:
                        self.on_liquidation_risk(symbol, margin_ratio)
                    else:
                        # Default: auto-liquidate if no custom handler
                        self.margin_manager.auto_liquidate(symbol)
            time.sleep(self.poll_interval)

    def stop(self):
        self.running = False