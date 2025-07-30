import time
import random
import pandas as pd
from services.data.data_sources import DataSources
from services.data.realtime_fetchers import RealTimeFetchers
from services.ml.advanced_feature_engineering import AdvancedFeatureEngineer

class DataPipeline:
    """
    Modular pipeline to fetch, cache, and feature-engineer market, DeFi, on-chain, and sentiment data.
    Designed to respect API rate limits, cache heavy calls, and provide batch/real-time data for your strategies and GUI.
    """
    def __init__(self, config, erc20_abi):
        self.config = config
        self.erc20_abi = erc20_abi
        self.ds = DataSources()
        self.rtf = RealTimeFetchers()
        self.fe = AdvancedFeatureEngineer()
        self._cache = {}
        self._last_fetch = {}

    def fetch_market_data(self, symbol="ETHUSDT"):
        # Example: fetch OHLCV from Binance
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=20"
        try:
            resp = self._safe_api_call(url, cache_ttl=60)  # cache for 1 min
            if resp:
                df = pd.DataFrame(resp, columns=[
                    "open_time", "open", "high", "low", "close", "volume",
                    "close_time", "quote_asset_volume", "num_trades",
                    "taker_buy_base", "taker_buy_quote", "ignore"
                ])
                df["close"] = df["close"].astype(float)
                return df[["close", "open", "high", "low", "volume"]]
        except Exception:
            pass
        return pd.DataFrame()

    def fetch_defi_data(self, token0, token1):
        # Use cached results if called within 2 mins
        key = f"defi_{token0}_{token1}"
        if self._in_cache(key, ttl=120):
            return self._cache[key]
        stats = self.rtf.fetch_all_defi_stats(
            token0_address=token0,
            token1_address=token1,
            rpc_url=self.config["ETH_RPC_URL"],
            erc20_abi=self.erc20_abi,
            dune_query_id=self.config.get("DUNE_QUERY_ID"),
            dune_api_key=self.config.get("DUNE_API_KEY"),
        )
        self._update_cache(key, stats)
        return stats

    def fetch_sentiment_and_macro(self, symbol="ETHUSDT"):
        # Use DataSources with internal rate limiting
        key = f"sentiment_macro_{symbol}"
        if self._in_cache(key, ttl=300):
            return self._cache[key]
        data = self.ds.fetch_all(
            symbol=symbol,
            github_repo=self.config.get("GITHUB_REPO", "ethereum/ethereum-org-website"),
            keyword=symbol.replace("USDT", "")
        )
        self._update_cache(key, data)
        return data

    def fetch_onchain_balances(self, address, tokens):
        # Avoid spamming RPC (cache for 2 min per token)
        result = {}
        for token in tokens:
            key = f"bal_{address}_{token}"
            if self._in_cache(key, ttl=120):
                result[token] = self._cache[key]
            else:
                balance = self.rtf.get_erc20_balance(
                    address=address,
                    token_address=token,
                    rpc_url=self.config["ETH_RPC_URL"],
                    erc20_abi=self.erc20_abi,
                )
                self._update_cache(key, balance)
                result[token] = balance
        return result

    def run_feature_engineering(self, ohlcv, defi=None, sentiment=None, macro=None):
        # Compose features from all available sources
        if ohlcv.empty:
            return pd.DataFrame()
        # Use most recent row for cross-market and funding
        cross_cex = {"cross_cex_price": sentiment.get("cross_cex_price", 0)} if sentiment else None
        funding = sentiment.get("funding") if sentiment else None
        onchain = {"whale_alerts": sentiment.get("whale_alerts", 0)} if sentiment else None
        gui_sentiment = {
            "dev_activity": sentiment.get("dev_activity", 0),
            "google_trends": sentiment.get("google_trends", 0),
            "twitter_trend_score": sentiment.get("twitter_trend_score", 0)
        } if sentiment else None
        macro_score = {"macro_event_score": sentiment.get("macro_event_score", 0)} if sentiment else None
        feats = self.fe.generate_features(
            ohlcv,
            cross_cex=cross_cex,
            funding=funding,
            onchain=onchain,
            sentiment=gui_sentiment,
            macro=macro_score
        )
        return feats

    # --------------- API Backoff and Caching Utilities ---------------

    def _safe_api_call(self, url, cache_ttl=30):
        # Cache and backoff for GET requests
        now = time.time()
        key = f"url_{url}"
        if key in self._cache and now - self._last_fetch[key] < cache_ttl:
            return self._cache[key]
        for attempt in range(3):
            try:
                resp = requests.get(url, timeout=10)
                if resp.status_code == 200:
                    result = resp.json()
                    self._update_cache(key, result)
                    return result
                elif resp.status_code in [429, 500, 502, 503, 504]:
                    time.sleep((2 ** attempt) + random.random())
            except Exception:
                time.sleep((2 ** attempt) + random.random())
        return None

    def _in_cache(self, key, ttl):
        now = time.time()
        return key in self._cache and (now - self._last_fetch[key]) < ttl

    def _update_cache(self, key, val):
        self._cache[key] = val
        self._last_fetch[key] = time.time()