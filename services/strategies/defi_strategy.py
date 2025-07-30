import pandas as pd

class DeFiStrategy:
    def __init__(self, defi_token="UNI", param=1.0):
        self.defi_token = defi_token
        self.param = param

    def generate_signal(self, price_df: pd.DataFrame, news_df: pd.DataFrame):
        if len(price_df) < 20:
            return None
        last_price = price_df["close"].iloc[-1]
        ma = price_df["close"].iloc[-20:].mean()
        latest_news = news_df[news_df["published"] >= price_df.index[-5:][0]]
        if (last_price > ma) and (not latest_news.empty) and (latest_news["sentiment"].mean() > 0.5):
            return "Buy"
        elif (last_price < ma) and (not latest_news.empty) and (latest_news["sentiment"].mean() < -0.5):
            return "Sell"
        return None