from services.ml.model_registry import ModelRegistry
from services.ml.advanced_feature_engineering import AdvancedFeatureEngineer
import pandas as pd

class MLSignaler:
    def __init__(self, model_name="scalping_xgb", model_dir="models"):
        self.registry = ModelRegistry(model_dir)
        self.model = self.registry.get_model(model_name)
        self.fe = AdvancedFeatureEngineer()

    def produce_signal(self, raw_ohlcv: pd.DataFrame, **kwargs):
        features_df = self.fe.generate_features(raw_ohlcv)
        latest = features_df.iloc[-1]
        X = latest.values.reshape(1, -1)
        pred = self.model.predict(X)
        proba = self.model.predict_proba(X) if hasattr(self.model, "predict_proba") else None
        return {
            "signal": int(pred[0]),
            "proba": proba[0] if proba is not None else None,
            "features": latest,
        }