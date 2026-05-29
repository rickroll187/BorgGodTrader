import os
import logging
from typing import Dict, Any, List, Optional
import numpy as np

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not installed - ML features limited")


class AdvancedMLManager:
    """
    Orchestrates model ensembles, drift detection, and auto-retraining.
    """

    def __init__(self, model_dir: str = "ml_models"):
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
        self.models: Dict[str, Any] = {}
        self.scalers: Dict[str, Any] = {}
        self.training_stats: Dict[str, Dict] = {}

        if SKLEARN_AVAILABLE:
            self.load_models()

    def load_models(self):
        """Load all saved models from disk."""
        if not SKLEARN_AVAILABLE:
            return

        for fname in os.listdir(self.model_dir):
            if fname.endswith(".pkl"):
                try:
                    model_name = fname[:-4]
                    self.models[model_name] = joblib.load(os.path.join(self.model_dir, fname))
                    logger.info(f"Loaded model: {model_name}")
                except Exception as e:
                    logger.error(f"Failed to load model {fname}: {e}")

        logger.info(f"Loaded {len(self.models)} models")

    def train_new_model(self, X, y, model_type: str = "rf", name: str = None,
                        save: bool = True) -> Optional[Any]:
        """Train a new model and optionally save it."""
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn not available")
            return None

        # Convert to numpy if DataFrame
        if hasattr(X, 'values'):
            X = X.values
        if hasattr(y, 'values'):
            y = y.values

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Create model
        if model_type == "rf":
            model = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
        elif model_type == "gb":
            model = GradientBoostingClassifier(n_estimators=100, random_state=42)
        elif model_type == "logreg":
            model = LogisticRegression(max_iter=1000, random_state=42)
        else:
            raise ValueError(f"Unknown model type: {model_type}")

        # Fit model
        model.fit(X_scaled, y)

        # Generate name
        model_name = name or f"{model_type}_model"

        # Save
        if save:
            model_path = os.path.join(self.model_dir, f"{model_name}.pkl")
            scaler_path = os.path.join(self.model_dir, f"{model_name}_scaler.pkl")
            joblib.dump(model, model_path)
            joblib.dump(scaler, scaler_path)

        self.models[model_name] = model
        self.scalers[model_name] = scaler

        # Store training stats
        self.training_stats[model_name] = {
            "n_samples": len(y),
            "n_features": X.shape[1],
            "class_distribution": dict(zip(*np.unique(y, return_counts=True))),
        }

        logger.info(f"Trained model: {model_name}")
        return model

    def predict(self, model_name: str, X) -> np.ndarray:
        """Get predictions from a specific model."""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")

        if hasattr(X, 'values'):
            X = X.values

        # Scale if scaler exists
        if model_name in self.scalers:
            X = self.scalers[model_name].transform(X)

        return self.models[model_name].predict(X)

    def predict_proba(self, model_name: str, X) -> np.ndarray:
        """Get probability predictions from a specific model."""
        if model_name not in self.models:
            raise ValueError(f"Model {model_name} not found")

        if hasattr(X, 'values'):
            X = X.values

        if model_name in self.scalers:
            X = self.scalers[model_name].transform(X)

        return self.models[model_name].predict_proba(X)

    def ensemble_predict(self, X, weights: Dict[str, float] = None) -> np.ndarray:
        """Get weighted ensemble predictions from all models."""
        if not self.models:
            raise ValueError("No models loaded")

        if hasattr(X, 'values'):
            X = X.values

        predictions = []
        model_weights = []

        for name, model in self.models.items():
            try:
                X_scaled = X
                if name in self.scalers:
                    X_scaled = self.scalers[name].transform(X)

                proba = model.predict_proba(X_scaled)
                predictions.append(proba)

                weight = weights.get(name, 1.0) if weights else 1.0
                model_weights.append(weight)

            except Exception as e:
                logger.warning(f"Model {name} prediction failed: {e}")

        if not predictions:
            raise ValueError("All model predictions failed")

        # Weighted average
        total_weight = sum(model_weights)
        weighted_proba = sum(p * w for p, w in zip(predictions, model_weights)) / total_weight

        return weighted_proba

    def feature_drift(self, X_live, X_train) -> Dict[str, float]:
        """Detect feature drift between training and live data."""
        if hasattr(X_live, 'columns'):
            columns = X_live.columns
            X_live = X_live.values
            X_train = X_train.values
        else:
            columns = [f"feature_{i}" for i in range(X_live.shape[1])]

        drift = {}
        for i, col in enumerate(columns):
            live_mean = np.mean(X_live[:, i])
            train_mean = np.mean(X_train[:, i])
            live_std = np.std(X_live[:, i])
            train_std = np.std(X_train[:, i])

            # Normalized drift score
            if train_std > 0:
                drift[col] = abs(live_mean - train_mean) / train_std
            else:
                drift[col] = abs(live_mean - train_mean)

        return drift

    def retrain_on_drift(self, X_live, y_live, X_train,
                         threshold: float = 2.0) -> bool:
        """Retrain if significant drift detected."""
        drift = self.feature_drift(X_live, X_train)
        max_drift = max(drift.values()) if drift else 0

        if max_drift > threshold:
            logger.warning(f"Drift detected (max={max_drift:.2f}), retraining...")
            self.train_new_model(X_live, y_live, model_type="rf", name="rf_drift")
            return True

        return False

    def get_model_info(self) -> List[Dict[str, Any]]:
        """Get information about all loaded models."""
        info = []
        for name, model in self.models.items():
            info.append({
                "name": name,
                "type": type(model).__name__,
                "training_stats": self.training_stats.get(name, {}),
            })
        return info

    def delete_model(self, name: str):
        """Delete a model."""
        if name in self.models:
            del self.models[name]
            self.scalers.pop(name, None)
            self.training_stats.pop(name, None)

            # Remove files
            model_path = os.path.join(self.model_dir, f"{name}.pkl")
            scaler_path = os.path.join(self.model_dir, f"{name}_scaler.pkl")
            if os.path.exists(model_path):
                os.remove(model_path)
            if os.path.exists(scaler_path):
                os.remove(scaler_path)

            logger.info(f"Deleted model: {name}")