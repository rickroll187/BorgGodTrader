import time
from threading import Thread
from sklearn.metrics import accuracy_score
import numpy as np

class ModelMonitor(Thread):
    """
    Monitors a model's accuracy and triggers retrain if drift detected.
    """
    def __init__(self, model, X_val, y_val, drift_threshold=0.05, retrain_callback=None, poll_interval=600):
        super().__init__()
        self.model = model
        self.X_val = X_val
        self.y_val = y_val
        self.drift_threshold = drift_threshold
        self.retrain_callback = retrain_callback
        self.poll_interval = poll_interval
        self.running = True

    def run(self):
        last_acc = accuracy_score(self.y_val, self.model.predict(self.X_val))
        while self.running:
            time.sleep(self.poll_interval)
            acc = accuracy_score(self.y_val, self.model.predict(self.X_val))
            if np.abs(acc - last_acc) > self.drift_threshold:
                if self.retrain_callback:
                    self.retrain_callback()
            last_acc = acc

    def stop(self):
        self.running = False