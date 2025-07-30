import pandas as pd
import numpy as np

class AdvancedFeatureEngineer:
    def __init__(self):
        pass

    def generate_features(
        self, 
        df: pd.DataFrame, 
        order_book=None, 
        sentiment=None, 
        onchain=None, 
        cross_cex=None, 
        funding=None, 
        macro=None
    ):
        df['return'] = df['close'].pct_change()
        df['volatility'] = df['close'].rolling(20).std()
        df['rsi'] = self.rsi(df['close'])

        # Cross-market
        if cross_cex:
            df['cross_price_spread'] = df['close'] - cross_cex.get('cross_cex_price', df['close'])

        # Funding
        if funding:
            df['funding_rate'] = funding.get('rate', 0)
            df['open_interest'] = funding.get('open_interest', 0)
            df['liquidations'] = funding.get('liquidations', 0)

        # On-chain
        if onchain:
            df['whale_alerts'] = onchain.get('whale_alerts', 0)

        # Sentiment
        if sentiment:
            df['dev_activity'] = sentiment.get('dev_activity', 0)
            df['google_trends'] = sentiment.get('google_trends', 0)
            df['twitter_trend_score'] = sentiment.get('twitter_trend_score', 0)

        # Macro
        if macro:
            df['macro_event_score'] = macro.get('macro_event_score', 0)

        df = df.fillna(0)
        return df

    @staticmethod
    def rsi(series, period=14):
        delta = series.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ma_up = up.rolling(period).mean()
        ma_down = down.rolling(period).mean()
        rs = ma_up / (ma_down + 1e-8)
        return 100 - (100 / (1 + rs))