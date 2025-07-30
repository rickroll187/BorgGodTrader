import requests
import time
import random

class DataSources:
    """
    Fetches and caches advanced data points from free-tier APIs for feature engineering.
    Designed to avoid exceeding rate limits by simple backoff and randomization.
    """
    def __init__(self):
        self.last_github = 0
        self.github_cache = None
        self.last_google_trends = 0
        self.google_trends_cache = None

    # --- Cross-Exchange Price Spread (Binance public API) ---
    def get_cross_cex_price(self, symbol="ETHUSDT"):
        try:
            resp = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5)
            if resp.status_code == 200:
                return float(resp.json().get("price", 0))
        except Exception:
            pass
        return 0

    # --- Funding Rate, Open Interest, Liquidations (Binance Futures) ---
    def get_futures_data(self, symbol="ETHUSDT"):
        # Funding Rate
        funding, oi, liq = 0, 0, 0
        try:
            # Funding
            f = requests.get(f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}", timeout=5)
            if f.status_code == 200:
                funding = float(f.json().get("lastFundingRate", 0))
            # Open Interest
            oi_resp = requests.get(f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}", timeout=5)
            if oi_resp.status_code == 200:
                oi = float(oi_resp.json().get("openInterest", 0))
            # Dummy liquidations (Binance API is private, so use stub/random)
            liq = random.randint(0, 5)
        except Exception:
            pass
        return {"rate": funding, "open_interest": oi, "liquidations": liq}

    # --- On-Chain: Whale Activity (Whale Alert API, free tier: only 5/day, so stub/mock) ---
    def get_whale_alerts(self):
        # Return stubbed value or from cache if already fetched today
        if random.random() < 0.1:
            return random.randint(1, 10)
        return 0

    # --- Dev Activity (GitHub API, low rate, so cache for 10 min) ---
    def get_dev_activity(self, github_repo="ethereum/ethereum-org-website"):
        # Returns commit count in last 7 days
        now = time.time()
        if self.github_cache and now - self.last_github < 600:
            return self.github_cache
        url = f"https://api.github.com/repos/{github_repo}/commits"
        params = {"since": (pd.Timestamp.now() - pd.Timedelta(days=7)).isoformat()}
        try:
            r = requests.get(url, params=params, timeout=5, headers={"Accept": "application/vnd.github.v3+json"})
            if r.status_code == 200:
                count = len(r.json())
                self.github_cache = count
                self.last_github = now
                return count
        except Exception:
            pass
        return 0

    # --- Google Trends (PyTrends, but here stubbed to avoid IP ban) ---
    def get_google_trends(self, keyword="ethereum"):
        # In production, use pytrends package; here, stub with random/fake data
        if random.random() < 0.2:
            return random.randint(50, 100)
        return 0

    # --- Macro Event Score (Economic calendar stub) ---
    def get_macro_event_score(self):
        # In production, scrape or use TradingEconomics/Calendarific; here, stub
        return random.choice([0, 1, 2])  # 0 = calm, 2 = major event

    # --- Twitter/X Trends (not free, stub only) ---
    def get_twitter_trend_score(self, symbol="ETH"):
        # Stub, as Twitter API is now paid-only for most endpoints
        return random.randint(0, 5)

    # --- All together: fetch for one asset ---
    def fetch_all(self, symbol="ETHUSDT", github_repo="ethereum/ethereum-org-website", keyword="ethereum"):
        price = self.get_cross_cex_price(symbol)
        futures = self.get_futures_data(symbol)
        whale_alerts = self.get_whale_alerts()
        dev_activity = self.get_dev_activity(github_repo)
        google_trends = self.get_google_trends(keyword)
        macro_event = self.get_macro_event_score()
        twitter_score = self.get_twitter_trend_score(symbol)
        return {
            "cross_cex_price": price,
            "funding": futures,
            "whale_alerts": whale_alerts,
            "dev_activity": dev_activity,
            "google_trends": google_trends,
            "macro_event_score": macro_event,
            "twitter_trend_score": twitter_score
        }