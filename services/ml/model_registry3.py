import joblib
import os

class ModelRegistry:
    def __init__(self, model_dir="models"):
        self.model_dir = model_dir
        self.models = {}

    def load_model(self, name):
        path = os.path.join(self.model_dir, f"{name}.pkl")
        if os.path.exists(path):
            self.models[name] = joblib.load(path)
            return self.models[name]
        else:
            raise FileNotFoundError(f"Model {name} not found in {self.model_dir}")

    def get_model(self, name):
        if name not in self.models:
            return self.load_model(name)
        return self.models[name]