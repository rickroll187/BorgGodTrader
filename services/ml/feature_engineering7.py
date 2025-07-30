import pandas as pd
import numpy as np

class FeatureEngineer:
    """Transforms raw data (OHLCV, order book, social, etc.) into ML-ready features."""
    def __init__(self):
        pass

    def ohlcv_features(self, df: pd.DataFrame):
        # df: ['open', 'high', 'low', 'close', 'volume', ...]
        df = df.copy()
        df['return'] = df['close'].pct_change()
        df['volatility'] = df['close'].rolling(20).std()
        df['rolling_mean'] = df['close'].rolling(20).mean()
        df['rsi'] = self.rsi(df['close'])
        df['macd'] = self.macd(df['close'])
        df = df.fillna(0)
        return df

    @staticmethod
    def rsi(series, period=14):
        delta = series.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ma_up = up.rolling(period).mean()
        ma_down = down.rolling(period).mean()
        rs = ma_up / ma_down
        return 100 - (100 / (1 + rs))

    @staticmethod
    def macd(series, fast=12, slow=26):
        ema_fast = series.ewm(span=fast, min_periods=fast).mean()
        ema_slow = series.ewm(span=slow, min_periods=slow).mean()
        return ema_fast - ema_slow