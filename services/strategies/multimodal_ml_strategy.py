import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import joblib
import os
from datetime import datetime

class MultimodalMLStrategy:
    """
    Multimodal ML Strategy:
    - Learns from its own trades and new market data (price, indicators, news, DeFi metrics).
    - Supports manual and auto-retraining if win rate drops below threshold.
    """

    def __init__(self, model_path="services/strategy/ml_model.joblib"):
        self.model_path = model_path
        self.model = None
        self.last_trained = None
        self.training_history = []
        if os.path.exists(model_path):
            self.model = joblib.load(model_path)
            self.last_trained = datetime.fromtimestamp(os.path.getmtime(model_path))

    def make_features(self, price_df, news_df, defi_df=None):
        feats = {}
        feats['return_1h'] = price_df["close"].pct_change(1).iloc[-1]
        feats['ma_10'] = price_df['ma_10'].iloc[-1]
        feats['ma_50'] = price_df['ma_50'].iloc[-1]
        feats['ma_diff'] = feats['ma_10'] - feats['ma_50']
        recent_news = news_df[news_df["published"] >= price_df.index[-5]]
        feats['news_sentiment'] = recent_news["sentiment"].mean() if not recent_news.empty else 0.0
        if defi_df is not None and "tvl" in defi_df.columns:
            feats['defi_tvl'] = defi_df["tvl"].iloc[-1]
            feats['defi_tvl_change'] = defi_df["tvl"].pct_change().iloc[-1]
        else:
            feats['defi_tvl'] = 0.0
            feats['defi_tvl_change'] = 0.0
        return pd.DataFrame([feats])

    def accumulate_training_data(self, trade_history, price_df, news_df, defi_df=None):
        """
        Builds training dataset from the bot's own historical trades.
        Each feature is associated with the realized trade outcome (profit/loss).
        """
        X = []
        y = []
        for trade in trade_history:
            # Find the row in price_df closest to trade['time']
            try:
                idx = price_df.index.get_loc(trade['time'], method="nearest")
            except Exception:
                continue
            # Look back for features before the trade
            if idx < 50:
                continue
            price_slice = price_df.iloc[:idx+1]
            news_slice = news_df[news_df["published"] <= price_df.index[idx]]
            if defi_df is not None:
                defi_slice = defi_df.iloc[:idx+1]
            else:
                defi_slice = None
            feats = self.make_features(price_slice, news_slice, defi_slice)
            X.append(feats)
            if trade["type"] == "Buy":
                # Find the corresponding Sell
                sell = next((t for t in trade_history if t["type"] == "Sell" and t["time"] > trade["time"]), None)
                if sell is not None and "pnl" in sell:
                    y.append(1 if sell["pnl"] > 0 else 0)
        if X:
            X_df = pd.concat(X).reset_index(drop=True)
            return X_df, np.array(y)
        return None, None

    def train(self, trade_history, price_df, news_df, defi_df=None):
        """
        Trains the model on its own trade history (self-learning).
        """
        X, y = self.accumulate_training_data(trade_history, price_df, news_df, defi_df)
        if X is not None and len(y) > 5:
            clf = RandomForestClassifier(n_estimators=100, random_state=42)
            clf.fit(X, y)
            joblib.dump(clf, self.model_path)
            self.model = clf
            self.last_trained = datetime.now()
            self.training_history.append(self.last_trained)
            return True
        return False

    def generate_signal(self, price_df, news_df, defi_df=None):
        if self.model is None or len(price_df) < 50:
            return None
        X = self.make_features(price_df, news_df, defi_df)
        pred = self.model.predict(X)[0]
        return "Buy" if pred == 1 else "Sell"

    def should_retrain(self, win_rate, win_threshold):
        """Returns True if the current win rate is below the retrain threshold."""
        return win_rate < win_threshold

    def get_training_status(self):
        """Returns last trained time and how many times retrained."""
        return self.last_trained, len(self.training_history)