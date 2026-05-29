import time
import logging
import requests
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


class BacktestDataFetcher:
    """
    Fetches historical OHLCV data for backtesting.
    Uses Binance public API (free, no auth needed) and CoinGecko.
    """

    BINANCE_BASE = "https://api.binance.com/api/v3"

    # Binance interval mappings
    INTERVALS = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w",
    }

    def __init__(self):
        self._cache: Dict[str, Any] = {}

    def fetch_ohlcv(self, symbol: str, interval: str = "1d",
                    limit: int = 365, start_time: int = None,
                    end_time: int = None) -> List[Dict]:
        """
        Fetch OHLCV bars from Binance.

        Args:
            symbol: Trading pair (e.g., "BTC/USD" or "BTCUSDT")
            interval: Bar interval ("1m", "5m", "15m", "30m", "1h", "4h", "1d", "1w")
            limit: Number of bars (max 1000 per request)
            start_time: Start timestamp in ms (optional)
            end_time: End timestamp in ms (optional)

        Returns:
            List of OHLCV dicts with open, high, low, close, volume, timestamp
        """
        binance_sym = self._normalize_symbol(symbol)
        interval = self.INTERVALS.get(interval, interval)

        cache_key = f"{binance_sym}_{interval}_{limit}"
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if time.time() - cached["fetched_at"] < 300:  # 5 min cache
                return cached["data"]

        bars = []
        remaining = limit

        # Binance max is 1000 per request, paginate if needed
        current_end = end_time

        while remaining > 0:
            params = {
                "symbol": binance_sym,
                "interval": interval,
                "limit": min(remaining, 1000),
            }

            if start_time:
                params["startTime"] = start_time
            if current_end:
                params["endTime"] = current_end

            try:
                resp = requests.get(
                    f"{self.BINANCE_BASE}/klines",
                    params=params,
                    timeout=10
                )

                if resp.status_code == 200:
                    klines = resp.json()
                    if not klines:
                        break

                    batch = [self._parse_kline(k) for k in klines]
                    bars = batch + bars  # Prepend (going backwards in time)
                    remaining -= len(batch)

                    # Update end time for next page
                    if batch:
                        current_end = int(batch[0]["timestamp"]) - 1

                    # If we got less than requested, we're at the beginning
                    if len(batch) < min(remaining + len(batch), 1000):
                        break
                else:
                    logger.error(f"Binance API error: {resp.status_code} {resp.text[:200]}")
                    break

            except Exception as e:
                logger.error(f"OHLCV fetch failed: {e}")
                break

        # Limit to requested amount and sort chronologically
        bars = sorted(bars, key=lambda x: x["timestamp"])[-limit:]

        if bars:
            self._cache[cache_key] = {"data": bars, "fetched_at": time.time()}

        logger.info(f"Fetched {len(bars)} bars for {symbol} @ {interval}")
        return bars

    def fetch_multiple_symbols(self, symbols: List[str], interval: str = "1d",
                               limit: int = 365) -> Dict[str, List[Dict]]:
        """Fetch OHLCV for multiple symbols."""
        results = {}
        for symbol in symbols:
            try:
                results[symbol] = self.fetch_ohlcv(symbol, interval, limit)
                time.sleep(0.1)  # Small delay between requests
            except Exception as e:
                logger.error(f"Failed to fetch {symbol}: {e}")
                results[symbol] = []
        return results

    def _parse_kline(self, k: List) -> Dict:
        """Parse Binance kline format to OHLCV dict."""
        return {
            "timestamp": k[0],
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "close_time": k[6],
            "quote_volume": float(k[7]),
            "trades": int(k[8]),
        }

    def _normalize_symbol(self, symbol: str) -> str:
        """Convert to Binance format (e.g., BTC/USD -> BTCUSDT)."""
        symbol = symbol.upper().replace("/", "").replace("-", "")
        if symbol.endswith("USD"):
            symbol += "T"  # BTCUSD -> BTCUSDT
        return symbol

    def fetch_coingecko_history(self, coin_id: str = "bitcoin",
                                days: int = 365) -> List[Dict]:
        """
        Fetch daily price history from CoinGecko (free, no API key).
        Returns daily OHLCV dicts.
        """
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/ohlc"
        params = {"vs_currency": "usd", "days": min(days, 365)}

        try:
            resp = requests.get(url, params=params, timeout=15)
            if resp.status_code == 200:
                ohlc = resp.json()
                return [
                    {
                        "timestamp": bar[0],
                        "open": bar[1],
                        "high": bar[2],
                        "low": bar[3],
                        "close": bar[4],
                        "volume": 0,
                    }
                    for bar in ohlc
                ]
            else:
                logger.error(f"CoinGecko history error: {resp.status_code}")
        except Exception as e:
            logger.error(f"CoinGecko history fetch failed: {e}")

        return []

    def to_dataframe(self, bars: List[Dict]):
        """Convert bars list to pandas DataFrame."""
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for DataFrame output")

        df = pd.DataFrame(bars)
        if "timestamp" in df.columns:
            df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms")
            df = df.set_index("datetime")

        return df

    def get_available_symbols(self) -> List[str]:
        """Get list of available trading pairs on Binance."""
        try:
            resp = requests.get(f"{self.BINANCE_BASE}/exchangeInfo", timeout=10)
            if resp.status_code == 200:
                symbols = resp.json().get("symbols", [])
                return [s["symbol"] for s in symbols if s.get("status") == "TRADING"]
        except Exception as e:
            logger.error(f"Failed to fetch symbols: {e}")
        return []
