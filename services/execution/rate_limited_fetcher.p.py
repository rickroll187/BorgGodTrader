import time
import requests

class RateLimitedFetcher:
    def __init__(self, max_calls_per_minute=30):
        self.max_calls = max_calls_per_minute
        self.call_times = []

    def _throttle(self):
        now = time.time()
        self.call_times = [t for t in self.call_times if now - t < 60]
        if len(self.call_times) >= self.max_calls:
            sleep_time = 60 - (now - self.call_times[0])
            if sleep_time > 0:
                print(f"Rate limit hit. Sleeping for {sleep_time:.1f} seconds...")
                time.sleep(sleep_time)
            now = time.time()
            self.call_times = [t for t in self.call_times if now - t < 60]

    def get(self, url, params=None, headers=None):
        self._throttle()
        self.call_times.append(time.time())
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None

def fetch_coingecko_price(symbol, vs_currency="usd", fetcher=None):
    if fetcher is None:
        fetcher = RateLimitedFetcher(max_calls_per_minute=10)
    url = f"https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": symbol, "vs_currencies": vs_currency}
    data = fetcher.get(url, params=params)
    if data and symbol in data:
        return data[symbol][vs_currency]
    return None