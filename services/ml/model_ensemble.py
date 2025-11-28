import numpy as np

class ModelEnsembler:
    def __init__(self, model_dict, weights=None):
        self.model_dict = model_dict
        if weights is None:
            self.weights = {k: 1.0 for k in model_dict}
        else:
            self.weights = weights

    def predict(self, X):
        preds = []
        for name, model in self.model_dict.items():
            preds.append(self.weights[name] * model.predict(X))
        return np.sign(np.sum(preds, axis=0))

    def predict_proba(self, X):
        probas = []
        for name, model in self.model_dict.items():
            if hasattr(model, "predict_proba"):
                probas.append(self.weights[name] * model.predict_proba(X))
        return np.mean(probas, axis=0) if probas else None
