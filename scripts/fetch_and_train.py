import pandas as pd
from services.data.data_sources import DataSources
from services.ml.advanced_feature_engineering import AdvancedFeatureEngineer
from sklearn.ensemble import RandomForestClassifier
import joblib

def fetch_data(symbol="ETHUSDT"):
    ds = DataSources()
    # Simulate OHLCV (replace with real fetch)
    ohlcv = pd.DataFrame({
        "close": [1800, 1820, 1810, 1830, 1840, 1850, 1860, 1855, 1870, 1880],
        "open": [1790, 1800, 1820, 1810, 1830, 1840, 1850, 1860, 1855, 1870],
        "high": [1805, 1825, 1825, 1835, 1845, 1855, 1865, 1860, 1875, 1885],
        "low": [1785, 1795, 1805, 1805, 1825, 1835, 1845, 1850, 1850, 1865],
        "volume": [100, 120, 110, 130, 140, 120, 110, 115, 125, 150],
    })
    ext_data = ds.fetch_all(symbol=symbol, github_repo="ethereum/ethereum-org-website", keyword="ethereum")
    # For all rows (simulate by repeating)
    extra = {k: [v]*len(ohlcv) if not isinstance(v, list) else v for k,v in ext_data.items()}
    ext_df = pd.DataFrame(extra)
    df = pd.concat([ohlcv, ext_df], axis=1)
    return df

def train_model(df):
    fe = AdvancedFeatureEngineer()
    feats = fe.generate_features(
        df,
        cross_cex={"cross_cex_price": df["cross_cex_price"]},
        funding=df.iloc[0].to_dict(),  # crude example
        onchain={"whale_alerts": df["whale_alerts"]},
        sentiment={
            "dev_activity": df["dev_activity"],
            "google_trends": df["google_trends"],
            "twitter_trend_score": df["twitter_trend_score"]
        },
        macro={"macro_event_score": df["macro_event_score"]}
    )

    # Simulate labels (random up/down)
    feats["y"] = (feats["close"].shift(-1) > feats["close"]).astype(int)
    feats = feats.dropna()
    X = feats.drop(columns=["y"])
    y = feats["y"]

    clf = RandomForestClassifier(n_estimators=20)
    clf.fit(X, y)
    joblib.dump(clf, "models/robust_model.pkl")
    print("Model trained and saved as models/robust_model.pkl")

if __name__ == "__main__":
    df = fetch_data()
    train_model(df)