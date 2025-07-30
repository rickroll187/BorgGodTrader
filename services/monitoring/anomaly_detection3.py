import numpy as np

class AnomalyDetector:
    def __init__(self, model=None):
        self.model = model

    def detect(self, features):
        if self.model is None:
            return np.abs(features).max() > 5
        else:
            return self.model.predict([features])[0] == -1

    def detect_report(self):
        return {"anomaly_check": "stub"}