import os
import time
import logging
import requests
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class DataSources:
    """
    Aggregates real-time data from multiple sources for feature engineering.
    Uses free-tier APIs with caching to respect rate limits.
    """

    def __init__(self):
        self._cache: Dict[str, Dict] = {}
        self._default_ttl = 120  # 2 minute cache by default

    def _get_cached(self, key: str, ttl: int = None) -> Optional[Any]:
        """Get cached value if still valid."""
        ttl = ttl or self._default_ttl
        if key in self._cache:
            cached = self._cache[key]
            if time.time() - cached['timestamp'] < ttl:
                return cached['data']
        return None

    def _set_cache(self, key: str, data: Any):
        """Set cache value."""
        self._cache[key] = {'data': data, 'timestamp': time.time()}

    def get_cross_cex_price(self, symbol: str = "ETHUSDT") -> float:
        """Get price from Binance (free, no API key needed)."""
        cache_key = f"binance_price_{symbol}"
        cached = self._get_cached(cache_key, ttl=30)
        if cached is not None:
            return cached

        try:
            url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                price = float(resp.json().get("price", 0))
                self._set_cache(cache_key, price)
                return price
        except Exception as e:
            logger.debug(f"Binance price fetch failed: {e}")

        return 0.0

    def get_futures_data(self, symbol: str = "ETHUSDT") -> Dict[str, Any]:
        """
        Get futures market data from Binance Futures (free, no API key).
        Returns funding rate, open interest, and estimated liquidations.
        """
        cache_key = f"futures_{symbol}"
        cached = self._get_cached(cache_key, ttl=60)
        if cached is not None:
            return cached

        data = {"rate": 0, "open_interest": 0, "liquidations": 0}

        try:
            # Funding Rate
            funding_url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
            resp = requests.get(funding_url, timeout=5)
            if resp.status_code == 200:
                data["rate"] = float(resp.json().get("lastFundingRate", 0))

            # Open Interest
            oi_url = f"https://fapi.binance.com/fapi/v1/openInterest?symbol={symbol}"
            resp = requests.get(oi_url, timeout=5)
            if resp.status_code == 200:
                data["open_interest"] = float(resp.json().get("openInterest", 0))

            # Long/Short Ratio (proxy for liquidation pressure)
            ls_url = f"https://fapi.binance.com/futures/data/globalLongShortAccountRatio?symbol={symbol}&period=5m&limit=1"
            resp = requests.get(ls_url, timeout=5)
            if resp.status_code == 200:
                ls_data = resp.json()
                if ls_data:
                    data["long_short_ratio"] = float(ls_data[0].get("longShortRatio", 1))

        except Exception as e:
            logger.debug(f"Futures data fetch failed: {e}")

        self._set_cache(cache_key, data)
        return data

    def get_fear_greed_index(self) -> Dict[str, Any]:
        """
        Get Crypto Fear & Greed Index (free API).
        Returns value (0-100) and classification.
        """
        cache_key = "fear_greed"
        cached = self._get_cached(cache_key, ttl=3600)  # 1 hour cache
        if cached is not None:
            return cached

        try:
            url = "https://api.alternative.me/fng/"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("data", [{}])[0]
                result = {
                    "value": int(data.get("value", 50)),
                    "classification": data.get("value_classification", "Neutral"),
                    "timestamp": data.get("timestamp"),
                }
                self._set_cache(cache_key, result)
                return result
        except Exception as e:
            logger.debug(f"Fear & Greed fetch failed: {e}")

        return {"value": 50, "classification": "Neutral"}

    def get_gas_prices(self) -> Dict[str, float]:
        """Get Ethereum gas prices in gwei (free Etherscan API)."""
        cache_key = "gas_prices"
        cached = self._get_cached(cache_key, ttl=30)
        if cached is not None:
            return cached

        try:
            url = "https://api.etherscan.io/api?module=gastracker&action=gasoracle"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("result", {})
                result = {
                    "low": float(data.get("SafeGasPrice", 0)),
                    "standard": float(data.get("ProposeGasPrice", 0)),
                    "fast": float(data.get("FastGasPrice", 0)),
                }
                self._set_cache(cache_key, result)
                return result
        except Exception as e:
            logger.debug(f"Gas price fetch failed: {e}")

        return {"low": 0, "standard": 0, "fast": 0}

    def get_defi_tvl(self) -> Dict[str, Any]:
        """Get DeFi TVL data from DeFiLlama (free, no API key)."""
        cache_key = "defi_tvl"
        cached = self._get_cached(cache_key, ttl=300)  # 5 min cache
        if cached is not None:
            return cached

        try:
            url = "https://api.llama.fi/v2/protocols"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                protocols = resp.json()
                total_tvl = sum(p.get("tvl", 0) for p in protocols if p.get("tvl"))
                top_10 = sorted(protocols, key=lambda x: x.get("tvl", 0), reverse=True)[:10]

                result = {
                    "total_tvl": total_tvl,
                    "top_protocols": [
                        {"name": p.get("name"), "tvl": p.get("tvl")}
                        for p in top_10
                    ],
                }
                self._set_cache(cache_key, result)
                return result
        except Exception as e:
            logger.debug(f"DeFi TVL fetch failed: {e}")

        return {"total_tvl": 0, "top_protocols": []}

    def get_stablecoin_flows(self) -> Dict[str, float]:
        """Get stablecoin supply data from DeFiLlama."""
        cache_key = "stablecoin_flows"
        cached = self._get_cached(cache_key, ttl=3600)
        if cached is not None:
            return cached

        try:
            url = "https://stablecoins.llama.fi/stablecoins?includePrices=true"
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                data = resp.json().get("peggedAssets", [])
                result = {}
                for stable in data[:5]:  # Top 5 stablecoins
                    result[stable.get("symbol", "UNKNOWN")] = stable.get("circulating", {}).get("peggedUSD", 0)
                self._set_cache(cache_key, result)
                return result
        except Exception as e:
            logger.debug(f"Stablecoin data fetch failed: {e}")

        return {}

    def get_dev_activity(self, github_repo: str = "ethereum/go-ethereum") -> int:
        """
        Get GitHub commit activity for a repo (limited free calls).
        Returns commit count in last 7 days.
        """
        cache_key = f"github_{github_repo}"
        cached = self._get_cached(cache_key, ttl=600)  # 10 min cache
        if cached is not None:
            return cached

        try:
            # Use commit activity endpoint (doesn't count against rate limit as much)
            url = f"https://api.github.com/repos/{github_repo}/stats/commit_activity"
            headers = {"Accept": "application/vnd.github.v3+json"}
            resp = requests.get(url, headers=headers, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                if data:
                    # Last week's commits
                    last_week = data[-1] if data else {}
                    commits = last_week.get("total", 0)
                    self._set_cache(cache_key, commits)
                    return commits
        except Exception as e:
            logger.debug(f"GitHub activity fetch failed: {e}")

        return 0

    def get_exchange_flows(self, exchange: str = "binance") -> Dict[str, float]:
        """
        Get exchange inflow/outflow data.
        Note: Real data requires premium APIs; this uses CryptoQuant free tier if available.
        """
        # CryptoQuant requires API key for exchange flows
        # Return estimated data based on public metrics
        cache_key = f"exchange_flows_{exchange}"
        cached = self._get_cached(cache_key, ttl=300)
        if cached is not None:
            return cached

        # Use Binance reserves as proxy
        result = {"net_flow": 0, "inflow": 0, "outflow": 0}

        try:
            # Get open interest change as proxy for flow direction
            futures = self.get_futures_data("BTCUSDT")
            oi = futures.get("open_interest", 0)

            # Positive OI trend often correlates with exchange inflows
            result["estimated_sentiment"] = "inflow" if futures.get("rate", 0) > 0 else "outflow"

        except Exception as e:
            logger.debug(f"Exchange flow estimate failed: {e}")

        self._set_cache(cache_key, result)
        return result

    def get_orderbook_imbalance(self, symbol: str = "BTCUSDT") -> float:
        """
        Calculate orderbook imbalance from Binance (bid vs ask volume).
        Returns ratio: >1 = buy pressure, <1 = sell pressure.
        """
        cache_key = f"ob_imbalance_{symbol}"
        cached = self._get_cached(cache_key, ttl=30)
        if cached is not None:
            return cached

        try:
            url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=100"
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                bid_vol = sum(float(b[1]) for b in data.get("bids", []))
                ask_vol = sum(float(a[1]) for a in data.get("asks", []))

                if ask_vol > 0:
                    imbalance = bid_vol / ask_vol
                    self._set_cache(cache_key, imbalance)
                    return imbalance
        except Exception as e:
            logger.debug(f"Orderbook fetch failed: {e}")

        return 1.0

    def get_social_metrics(self, coin: str = "bitcoin") -> Dict[str, Any]:
        """Get social metrics from CoinGecko (free tier)."""
        cache_key = f"social_{coin}"
        cached = self._get_cached(cache_key, ttl=3600)
        if cached is not None:
            return cached

        try:
            url = f"https://api.coingecko.com/api/v3/coins/{coin}"
            params = {"localization": "false", "tickers": "false",
                      "market_data": "false", "community_data": "true",
                      "developer_data": "true"}
            resp = requests.get(url, params=params, timeout=10)

            if resp.status_code == 200:
                data = resp.json()
                community = data.get("community_data", {})
                developer = data.get("developer_data", {})

                result = {
                    "twitter_followers": community.get("twitter_followers", 0),
                    "reddit_subscribers": community.get("reddit_subscribers", 0),
                    "github_stars": developer.get("stars", 0),
                    "github_forks": developer.get("forks", 0),
                    "commit_count_4_weeks": developer.get("commit_count_4_weeks", 0),
                }
                self._set_cache(cache_key, result)
                return result
        except Exception as e:
            logger.debug(f"Social metrics fetch failed: {e}")

        return {}

    def fetch_all(self, symbol: str = "ETHUSDT", coin: str = "ethereum") -> Dict[str, Any]:
        """Fetch all available data points for comprehensive analysis."""
        return {
            "price": self.get_cross_cex_price(symbol),
            "futures": self.get_futures_data(symbol),
            "fear_greed": self.get_fear_greed_index(),
            "gas": self.get_gas_prices(),
            "orderbook_imbalance": self.get_orderbook_imbalance(symbol),
            "defi_tvl": self.get_defi_tvl(),
            "stablecoin_supply": self.get_stablecoin_flows(),
            "social": self.get_social_metrics(coin),
            "dev_activity": self.get_dev_activity(),
            "timestamp": time.time(),
        }
