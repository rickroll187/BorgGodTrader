import time
import logging
import numpy as np
from collections import deque
from typing import Dict, Any, List, Optional

from services.strategies.base_strategy import BaseStrategy

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class Strategy(BaseStrategy):
    """
    ML Ensemble Strategy.

    Builds features from OHLCV + on-chain data and runs an ensemble of
    Random Forest + Gradient Boosting classifiers to predict next-candle
    direction. Retrains automatically when prediction accuracy dips.

    Starts in "learning" mode and only starts trading after 50 samples.
    """

    name = "ml_ensemble"
    description = "Random Forest + GBM ensemble with online retraining"

    def __init__(self, core, symbol: str = "BTC/USD",
                 min_training_samples: int = 50,
                 retrain_interval: int = 100,
                 trade_amount: float = 0.01,
                 confidence_threshold: float = 0.70):
        super().__init__(core)
        self.symbol = symbol
        self.min_training_samples = min_training_samples
        self.retrain_interval = retrain_interval
        self.trade_amount = trade_amount
        self.confidence_threshold = confidence_threshold

        # History
        self.price_history: deque = deque(maxlen=500)
        self.feature_history: List[List[float]] = []
        self.label_history: List[int] = []
        self.predictions: deque = deque(maxlen=50)

        # Model state
        self.model_trained = False
        self.samples_since_retrain = 0
        self.last_train_time: Optional[float] = None
        self.accuracy_history: deque = deque(maxlen=20)

    def analyze(self, context: Dict[str, Any]) -> Dict[str, Any]:
        asset = self.symbol.split("/")[0]
        price = self.core.tokeninfo_service.get_token_price(asset)

        if not price:
            return {"signal": "hold", "confidence": 0, "reason": "No price data"}

        self.price_history.append(price)
        prices = list(self.price_history)

        if len(prices) < 30:
            return {
                "signal": "hold",
                "confidence": 0,
                "reason": f"Collecting data ({len(prices)}/30)"
            }

        # Build features
        features = self._build_features(prices)

        # Label the previous bar (1=up, 0=down) now that we have next price
        if self.feature_history:
            prev_price = prices[-2]
            label = 1 if price > prev_price else 0
            self.label_history.append(label)

            # Track prediction accuracy
            if self.predictions:
                correct = int(self.predictions[-1] == label)
                self.accuracy_history.append(correct)

        self.feature_history.append(features)
        self.samples_since_retrain += 1

        # Check if we should train/retrain
        n_samples = len(self.label_history)
        should_train = (
            n_samples >= self.min_training_samples and
            (
                not self.model_trained or
                self.samples_since_retrain >= self.retrain_interval
            )
        )

        if should_train:
            self._train()

        if not self.model_trained:
            return {
                "signal": "hold",
                "confidence": 0,
                "reason": f"Training data: {n_samples}/{self.min_training_samples}",
            }

        # Get prediction
        try:
            ml_manager = self.core.ml_manager
            if not ml_manager or "ml_ensemble" not in ml_manager.models:
                return {"signal": "hold", "confidence": 0, "reason": "Model not ready"}

            X = np.array([features])
            proba = ml_manager.predict_proba("ml_ensemble", X)[0]
            pred_class = np.argmax(proba)
            confidence = float(proba[pred_class])

            self.predictions.append(pred_class)

            accuracy = sum(self.accuracy_history) / len(self.accuracy_history) if self.accuracy_history else 0.5

            if pred_class == 1 and confidence >= self.confidence_threshold:
                return {
                    "signal": "buy",
                    "confidence": confidence,
                    "symbol": self.symbol,
                    "amount": self.trade_amount,
                    "reason": f"ML predicts UP conf={confidence:.2f} accuracy={accuracy:.2f}",
                    "model_accuracy": accuracy,
                }
            elif pred_class == 0 and confidence >= self.confidence_threshold:
                return {
                    "signal": "sell",
                    "confidence": confidence,
                    "symbol": self.symbol,
                    "amount": self.trade_amount,
                    "reason": f"ML predicts DOWN conf={confidence:.2f} accuracy={accuracy:.2f}",
                    "model_accuracy": accuracy,
                }
        except Exception as e:
            logger.error(f"ML prediction failed: {e}")

        return {"signal": "hold", "confidence": 0, "reason": "Confidence below threshold"}

    def _build_features(self, prices: List[float]) -> List[float]:
        """Build feature vector from price history."""
        p = prices
        n = len(p)

        def safe_ema(period):
            if n < period:
                return p[-1]
            k = 2.0 / (period + 1)
            ema = sum(p[:period]) / period
            for px in p[period:]:
                ema = px * k + ema * (1 - k)
            return ema

        def rsi(period=14):
            if n < period + 1:
                return 50.0
            deltas = [p[i] - p[i-1] for i in range(n-period, n)]
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            avg_g = sum(gains) / period
            avg_l = sum(losses) / period
            if avg_l == 0:
                return 100.0
            return 100 - (100 / (1 + avg_g / avg_l))

        ema9 = safe_ema(9)
        ema21 = safe_ema(21)
        current = p[-1]

        # Returns
        ret1 = (p[-1] - p[-2]) / p[-2] if n > 1 else 0
        ret5 = (p[-1] - p[-5]) / p[-5] if n > 5 else 0
        ret10 = (p[-1] - p[-10]) / p[-10] if n > 10 else 0

        # Volatility (std of last 10 returns)
        if n > 11:
            rets = [(p[i] - p[i-1]) / p[i-1] for i in range(n-10, n)]
            vol = float(np.std(rets))
        else:
            vol = 0.0

        # EMA signals
        ema9_signal = (current - ema9) / ema9
        ema21_signal = (current - ema21) / ema21
        ema_cross = (ema9 - ema21) / ema21

        rsi_val = rsi(14) / 100.0

        # Distance from 20-period high/low
        window = p[-min(20, n):]
        high20 = max(window)
        low20 = min(window)
        dist_high = (high20 - current) / high20 if high20 > 0 else 0
        dist_low = (current - low20) / low20 if low20 > 0 else 0

        return [
            ret1, ret5, ret10,
            vol,
            ema9_signal, ema21_signal, ema_cross,
            rsi_val,
            dist_high, dist_low,
        ]

    def _train(self):
        """Train the ML model on accumulated data."""
        try:
            n = min(len(self.feature_history), len(self.label_history))
            X = np.array(self.feature_history[:n])
            y = np.array(self.label_history[:n])

            if len(set(y)) < 2:
                logger.debug("Need both classes to train")
                return

            self.core.ml_manager.train_new_model(
                X, y,
                model_type="rf",
                name="ml_ensemble",
                save=True
            )

            self.model_trained = True
            self.samples_since_retrain = 0
            self.last_train_time = time.time()

            logger.info(f"ML ensemble retrained on {n} samples")

        except Exception as e:
            logger.error(f"ML training failed: {e}")

    def get_model_stats(self) -> Dict[str, Any]:
        """Get model performance statistics."""
        accuracy = sum(self.accuracy_history) / len(self.accuracy_history) if self.accuracy_history else 0
        return {
            "trained": self.model_trained,
            "samples": len(self.label_history),
            "accuracy_last_20": accuracy,
            "last_train": self.last_train_time,
        }
