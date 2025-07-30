class AutoHedger:
    """
    Monitors portfolio risk and triggers hedging if needed.
    """
    def __init__(self, risk_engine, hedge_executor):
        self.risk_engine = risk_engine
        self.hedge_executor = hedge_executor

    def hedge(self):
        risk = self.risk_engine.risk_overlay()
        if abs(risk["delta"]) > 1.0 and self.hedge_executor:
            self.hedge_executor.hedge_delta(risk["delta"])
        # Add gamma/vega hedging as needed