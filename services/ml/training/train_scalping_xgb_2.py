import pandas as pd
from services.ml.feature_engineering import FeatureEngineer
from sklearn.ensemble import GradientBoostingClassifier
import joblib

# Load historical OHLCV data
data = pd.read_csv("your_historical_ohlcv.csv")
fe = FeatureEngineer()
features = fe.ohlcv_features(data)

# Example target: 1 for up, -1 for down, 0 for flat
features['target'] = (features['close'].shift(-5) > features['close']).astype(int) - (features['close'].shift(-5) < features['close']).astype(int)
X = features.drop(columns=['target', 'timestamp', 'open', 'high', 'low', 'close', 'volume'], errors='ignore')
y = features['target']

# Train/test split
train_idx = int(0.8 * len(X))
X_train, X_test = X.iloc[:train_idx], X.iloc[train_idx:]
y_train, y_test = y.iloc[:train_idx], y.iloc[train_idx:]

# Train model
model = GradientBoostingClassifier()
model.fit(X_train, y_train)
print("Train score:", model.score(X_train, y_train))
print("Test score:", model.score(X_test, y_test))

# Save model
joblib.dump(model, "models/scalping_xgb.pkl")