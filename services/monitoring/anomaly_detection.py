import time
import logging
from typing import Dict, Any, List, Optional
from collections import deque
import statistics

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Detects anomalies in trading data using statistical methods.
    Monitors prices, volumes, and trading patterns.
    """

    def __init__(self, window_size: int = 100, z_threshold: float = 3.0):
        self.window_size = window_size
        self.z_threshold = z_threshold
        self.price_history: Dict[str, deque] = {}
        self.volume_history: Dict[str, deque] = {}
        self.anomalies: List[Dict] = []

    def update(self, symbol: str, price: float, volume: float = 0) -> Optional[Dict]:
        """Update with new data point and check for anomalies."""

        # Initialize history if needed
        if symbol not in self.price_history:
            self.price_history[symbol] = deque(maxlen=self.window_size)
            self.volume_history[symbol] = deque(maxlen=self.window_size)

        anomaly = None

        # Check for price anomaly
        if len(self.price_history[symbol]) >= 10:
            price_anomaly = self._check_anomaly(
                list(self.price_history[symbol]), price, "price"
            )
            if price_anomaly:
                anomaly = {
                    "type": "price",
                    "symbol": symbol,
                    "value": price,
                    "z_score": price_anomaly["z_score"],
                    "timestamp": time.time(),
                }
                self.anomalies.append(anomaly)
                logger.warning(f"Price anomaly detected for {symbol}: z={price_anomaly['z_score']:.2f}")

        # Check for volume anomaly
        if volume > 0 and len(self.volume_history[symbol]) >= 10:
            vol_anomaly = self._check_anomaly(
                list(self.volume_history[symbol]), volume, "volume"
            )
            if vol_anomaly:
                anomaly = {
                    "type": "volume",
                    "symbol": symbol,
                    "value": volume,
                    "z_score": vol_anomaly["z_score"],
                    "timestamp": time.time(),
                }
                self.anomalies.append(anomaly)
                logger.warning(f"Volume anomaly detected for {symbol}: z={vol_anomaly['z_score']:.2f}")

        # Update history
        self.price_history[symbol].append(price)
        if volume > 0:
            self.volume_history[symbol].append(volume)

        return anomaly

    def _check_anomaly(self, history: List[float], value: float,
                       metric_type: str) -> Optional[Dict]:
        """Check if value is anomalous using z-score."""
        if len(history) < 10:
            return None

        mean = statistics.mean(history)
        std = statistics.stdev(history)

        if std == 0:
            return None

        z_score = (value - mean) / std

        if abs(z_score) > self.z_threshold:
            return {
                "z_score": z_score,
                "mean": mean,
                "std": std,
                "type": metric_type,
            }

        return None

    def check_price_movement(self, symbol: str, pct_change: float,
                             threshold: float = 5.0) -> Optional[Dict]:
        """Check for sudden large price movements."""
        if abs(pct_change) > threshold:
            anomaly = {
                "type": "sudden_move",
                "symbol": symbol,
                "pct_change": pct_change,
                "timestamp": time.time(),
            }
            self.anomalies.append(anomaly)
            logger.warning(f"Sudden move detected for {symbol}: {pct_change:.2f}%")
            return anomaly
        return None

    def check_spread_anomaly(self, symbol: str, bid: float, ask: float,
                             normal_spread_pct: float = 0.1) -> Optional[Dict]:
        """Check for abnormal bid-ask spread."""
        if bid <= 0:
            return None

        spread_pct = ((ask - bid) / bid) * 100

        if spread_pct > normal_spread_pct * 5:  # 5x normal spread
            anomaly = {
                "type": "spread",
                "symbol": symbol,
                "spread_pct": spread_pct,
                "normal_spread_pct": normal_spread_pct,
                "timestamp": time.time(),
            }
            self.anomalies.append(anomaly)
            logger.warning(f"Spread anomaly for {symbol}: {spread_pct:.2f}%")
            return anomaly
        return None

    def get_recent_anomalies(self, hours: float = 24) -> List[Dict]:
        """Get anomalies from the last N hours."""
        cutoff = time.time() - (hours * 3600)
        return [a for a in self.anomalies if a.get("timestamp", 0) >= cutoff]

    def get_anomaly_summary(self) -> Dict[str, Any]:
        """Get summary of detected anomalies."""
        recent = self.get_recent_anomalies(24)

        by_type = {}
        by_symbol = {}

        for a in recent:
            a_type = a.get("type", "unknown")
            symbol = a.get("symbol", "unknown")

            by_type[a_type] = by_type.get(a_type, 0) + 1
            by_symbol[symbol] = by_symbol.get(symbol, 0) + 1

        return {
            "total_24h": len(recent),
            "by_type": by_type,
            "by_symbol": by_symbol,
            "latest": recent[-5:] if recent else [],
        }

    def clear_history(self, symbol: str = None):
        """Clear anomaly history."""
        if symbol:
            self.price_history.pop(symbol, None)
            self.volume_history.pop(symbol, None)
            self.anomalies = [a for a in self.anomalies if a.get("symbol") != symbol]
        else:
            self.price_history.clear()
            self.volume_history.clear()
            self.anomalies.clear()
