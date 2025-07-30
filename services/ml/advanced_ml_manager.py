import pandas as pd
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
import joblib
import os

class AdvancedMLManager:
    """
    Orchestrates model ensembles, drift detection, and auto-retraining.
    """
    def __init__(self, model_dir="ml_models"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self.models = self.load_models()

    def load_models(self):
        models = {}
        for fname in os.listdir(self.model_dir):
            if fname.endswith(".pkl"):
                models[fname[:-4]] = joblib.load(os.path.join(self.model_dir, fname))
        return models

    def train_new_model(self, X, y, model_type="rf", name=None):
        if model_type == "rf":
            model = RandomForestClassifier(n_estimators=100)
        elif model_type == "logreg":
            model = LogisticRegression()
        else:
            raise ValueError("Unknown model type")
        model.fit(X, y)
        fname = name or f"{model_type}_model"
        joblib.dump(model, os.path.join(self.model_dir, f"{fname}.pkl"))
        self.models[fname] = model

    def ensemble_predict(self, X):
        if not self.models:
            raise Exception('No models loaded')
        ensemble = VotingClassifier(
            estimators=[(k, v) for k, v in self.models.items()],
            voting="soft"
        )
        ensemble.fit(X, [0]*len(X))  # Dummy fit for sklearn API
        return ensemble.predict_proba(X)

    def feature_drift(self, X_live, X_train):
        drift = {}
        for col in X_live.columns:
            live_mean = X_live[col].mean()
            train_mean = X_train[col].mean()
            drift[col] = abs(live_mean - train_mean)
        return drift

    def retrain_on_drift(self, X_live, y_live, threshold=0.1, X_train=None):
        if X_train is None:
            return False
        drift = self.feature_drift(X_live, X_train)
        if any(d > threshold for d in drift.values()):
            self.train_new_model(X_live, y_live, model_type="rf", name="rf_drift")
            return True
        return False