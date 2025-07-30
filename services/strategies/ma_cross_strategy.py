import pandas as pd

class MovingAverageCrossStrategy:
    def __init__(self, fast_window=10, slow_window=50):
        self.fast_window = fast_window
        self.slow_window = slow_window

    def generate_signal(self, price_df: pd.DataFrame, news_df: pd.DataFrame):
        if len(price_df) < self.slow_window:
            return None
        ma_fast = price_df["close"].rolling(self.fast_window).mean().iloc[-1]
        ma_slow = price_df["close"].rolling(self.slow_window).mean().iloc[-1]
        if ma_fast > ma_slow:
            return "Buy"
        elif ma_fast < ma_slow:
            return "Sell"
        return None