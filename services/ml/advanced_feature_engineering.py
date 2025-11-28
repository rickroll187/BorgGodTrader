import pandas as pd
import numpy as np

class AdvancedFeatureEngineer:
    def __init__(self):
        pass

    def rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def generate_features(
        self,
        df: pd.DataFrame,
        order_book=None,
        sentiment=None,
        onchain=None,
        cross_cex=None,
        funding=None,
        macro=None,
    ):
        df['return'] = df['close'].pct_change()
        df['volatility'] = df['close'].rolling(20).std()
        df['rsi'] = self.rsi(df['close'])

        if cross_cex:
            df['cross_price_spread'] = df['close'] - cross_cex.get('cross_cex_price', df['close'])

        if funding:
            df['funding_rate'] = funding.get('rate', 0)
            df['open_interest'] = funding.get('open_interest', 0)
            df['liquidations'] = funding.get('liquidations', 0)

        if onchain:
            df['whale_alerts'] = onchain.get('whale_alerts', 0)

        if sentiment:
            df['dev_activity'] = sentiment.get('dev_activity', 0)
            df['google_trends'] = sentiment.get('google_trends', 0)
            df['twitter_trend_score'] = sentiment.get('twitter_trend_score', 0)

        if macro:
            df['macro_trend'] = macro.get('macro_trend', 0)

        df = df.replace([np.inf, -np.inf], np.nan).ffill().bfill()
        return df
