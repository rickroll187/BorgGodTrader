import pandas as pd
from services.ml.signaler import MLSignaler

class Strategy:
    def __init__(self, core):
        self.core = core
        self.enabled = True
        self.ml_signaler = MLSignaler(model_name="scalping_xgb")

    def run(self, context):
        if not self.enabled:
            return
        # Example: live OHLCV fetch from an exchange
        ohlcv = context.get("ohlcv")
        if ohlcv is None:
            return
        result = self.ml_signaler.produce_signal(ohlcv)
        signal = result["signal"]
        proba = result["proba"]
        if signal == 1:
            self.core.kraken_executor.buy("ETHUSD", amount=0.01)
        elif signal == -1:
            self.core.kraken_executor.sell("ETHUSD", amount=0.01)
        self.core.trade_logger.log_trade({
            "type": "MLSignal",
            "features": result["features"].to_dict(),
            "signal": signal,
            "proba": proba.tolist() if proba is not None else None
        })