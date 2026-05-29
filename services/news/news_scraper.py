import os
import time
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class NewsScraper:
    """
    Crypto news aggregator using multiple free sources.
    Supports CryptoPanic, CoinGecko news, and fallback RSS feeds.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("CRYPTOPANIC_API_KEY")
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 300  # 5 minutes

    def fetch_latest(self, symbols: List[str] = None, kind: str = "news",
                     limit: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch latest crypto news.

        Args:
            symbols: Filter by symbols (e.g., ["BTC", "ETH"])
            kind: Type of content ("news", "media", "all")
            limit: Max number of items

        Returns:
            List of news items with title, url, source, published_at, sentiment
        """
        cache_key = f"{symbols}_{kind}"

        # Check cache
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached['timestamp'] < self._cache_ttl:
                return cached['data'][:limit]

        # Try CryptoPanic first
        news = self._fetch_cryptopanic(symbols, kind)

        # Fallback to CoinGecko status updates
        if not news:
            news = self._fetch_coingecko_news(symbols)

        # Last resort: mock/sample data for testing
        if not news:
            news = self._get_sample_news()

        # Cache results
        self._cache[cache_key] = {'data': news, 'timestamp': time.time()}

        return news[:limit]

    def _fetch_cryptopanic(self, symbols: List[str] = None,
                           kind: str = "news") -> List[Dict[str, Any]]:
        """Fetch from CryptoPanic API."""
        if not self.api_key:
            logger.debug("No CryptoPanic API key configured")
            return []

        url = "https://cryptopanic.com/api/v1/posts/"
        params = {
            "auth_token": self.api_key,
            "filter": kind if kind != "all" else None,
            "currencies": ",".join(symbols) if symbols else None,
            "public": "true"
        }
        params = {k: v for k, v in params.items() if v}

        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for item in data.get("results", []):
                    results.append({
                        "title": item.get("title"),
                        "url": item.get("url"),
                        "source": item.get("source", {}).get("title", "Unknown"),
                        "published_at": item.get("published_at"),
                        "sentiment": self._parse_sentiment(item.get("votes", {})),
                        "currencies": [c.get("code") for c in item.get("currencies", [])],
                        "kind": item.get("kind"),
                    })
                return results
            else:
                logger.warning(f"CryptoPanic API returned {resp.status_code}")
        except Exception as e:
            logger.error(f"CryptoPanic fetch failed: {e}")

        return []

    def _fetch_coingecko_news(self, symbols: List[str] = None) -> List[Dict[str, Any]]:
        """Fetch status updates from CoinGecko (free, no API key needed)."""
        # CoinGecko doesn't have a dedicated news endpoint in free tier
        # But we can get status updates for coins
        if not symbols:
            symbols = ["bitcoin", "ethereum"]

        results = []
        for symbol in symbols[:3]:  # Limit to avoid rate limits
            coin_id = symbol.lower()
            if coin_id in ["btc", "bitcoin"]:
                coin_id = "bitcoin"
            elif coin_id in ["eth", "ethereum"]:
                coin_id = "ethereum"

            url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
            params = {"localization": "false", "tickers": "false",
                      "market_data": "false", "community_data": "true"}

            try:
                resp = requests.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    # Get community data as pseudo-news
                    desc = data.get("description", {}).get("en", "")
                    if desc:
                        results.append({
                            "title": f"{data.get('name', symbol)} Update",
                            "url": data.get("links", {}).get("homepage", [""])[0],
                            "source": "CoinGecko",
                            "published_at": None,
                            "sentiment": "neutral",
                            "currencies": [symbol.upper()],
                            "kind": "info",
                        })
            except Exception as e:
                logger.debug(f"CoinGecko fetch failed for {symbol}: {e}")

        return results

    def _parse_sentiment(self, votes: Dict[str, int]) -> str:
        """Parse sentiment from vote counts."""
        positive = votes.get("positive", 0) + votes.get("liked", 0)
        negative = votes.get("negative", 0) + votes.get("disliked", 0)

        if positive > negative * 2:
            return "bullish"
        elif negative > positive * 2:
            return "bearish"
        return "neutral"

    def _get_sample_news(self) -> List[Dict[str, Any]]:
        """Return sample news for testing when APIs are unavailable."""
        return [
            {
                "title": "Bitcoin Shows Strength Above Key Support Level",
                "url": "https://example.com/btc-support",
                "source": "Sample News",
                "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sentiment": "bullish",
                "currencies": ["BTC"],
                "kind": "news",
            },
            {
                "title": "Ethereum Layer 2 Solutions See Record Activity",
                "url": "https://example.com/eth-l2",
                "source": "Sample News",
                "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sentiment": "bullish",
                "currencies": ["ETH"],
                "kind": "news",
            },
            {
                "title": "Market Analysis: Crypto Consolidation Phase Continues",
                "url": "https://example.com/market-analysis",
                "source": "Sample News",
                "published_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "sentiment": "neutral",
                "currencies": ["BTC", "ETH"],
                "kind": "analysis",
            },
        ]

    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for news by keyword."""
        # CryptoPanic doesn't support search in free tier
        # Return filtered cached results
        all_news = self.fetch_latest(limit=100)
        query_lower = query.lower()

        return [
            n for n in all_news
            if query_lower in n.get('title', '').lower()
        ][:limit]

    def get_sentiment_summary(self, symbols: List[str] = None) -> Dict[str, Any]:
        """Get overall sentiment summary for given symbols."""
        news = self.fetch_latest(symbols, limit=50)

        bullish = sum(1 for n in news if n.get('sentiment') == 'bullish')
        bearish = sum(1 for n in news if n.get('sentiment') == 'bearish')
        neutral = sum(1 for n in news if n.get('sentiment') == 'neutral')
        total = len(news)

        if total == 0:
            return {"overall": "neutral", "score": 0}

        score = (bullish - bearish) / total

        if score > 0.3:
            overall = "bullish"
        elif score < -0.3:
            overall = "bearish"
        else:
            overall = "neutral"

        return {
            "overall": overall,
            "score": score,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "total": total,
        }
