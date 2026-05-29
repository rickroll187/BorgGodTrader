import os
import time
import requests
import logging
from typing import Dict, Optional, List, Any

logger = logging.getLogger(__name__)


class TokenInfoService:
    """
    Token information service using CoinGecko API.
    Includes caching to respect rate limits.
    """

    COINGECKO_BASE = "https://api.coingecko.com/api/v3"

    # Common symbol to CoinGecko ID mappings
    SYMBOL_TO_ID = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "USDT": "tether",
        "USDC": "usd-coin",
        "BNB": "binancecoin",
        "XRP": "ripple",
        "ADA": "cardano",
        "DOGE": "dogecoin",
        "SOL": "solana",
        "DOT": "polkadot",
        "MATIC": "matic-network",
        "LTC": "litecoin",
        "AVAX": "avalanche-2",
        "LINK": "chainlink",
        "UNI": "uniswap",
        "ATOM": "cosmos",
        "XLM": "stellar",
        "ALGO": "algorand",
        "NEAR": "near",
        "FTM": "fantom",
        "AAVE": "aave",
        "MKR": "maker",
        "CRV": "curve-dao-token",
        "COMP": "compound-governance-token",
        "SNX": "synthetix-network-token",
        "SUSHI": "sushi",
        "YFI": "yearn-finance",
        "1INCH": "1inch",
        "BAL": "balancer",
        "WETH": "weth",
        "WBTC": "wrapped-bitcoin",
        "DAI": "dai",
        "FRAX": "frax",
        "LUSD": "liquity-usd",
    }

    # Standard ERC20 ABI for balance checks
    ERC20_ABI = [
        {"constant": True, "inputs": [{"name": "_owner", "type": "address"}],
         "name": "balanceOf", "outputs": [{"name": "balance", "type": "uint256"}],
         "type": "function"},
        {"constant": True, "inputs": [], "name": "decimals",
         "outputs": [{"name": "", "type": "uint8"}], "type": "function"},
        {"constant": True, "inputs": [], "name": "symbol",
         "outputs": [{"name": "", "type": "string"}], "type": "function"},
    ]

    def __init__(self, rpc_url: Optional[str] = None):
        self.rpc_url = rpc_url
        self.api_key = os.getenv("COINGECKO_API_KEY", "")
        self._price_cache: Dict[str, dict] = {}
        self._cache_ttl = 60  # 1 minute cache
        self.erc20_abi = self.ERC20_ABI

    def _get_headers(self) -> dict:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["x-cg-pro-api-key"] = self.api_key
        return headers

    def _symbol_to_id(self, symbol: str) -> str:
        """Convert trading symbol to CoinGecko ID."""
        symbol = symbol.upper().replace("USD", "").replace("USDT", "").replace("USDC", "")
        return self.SYMBOL_TO_ID.get(symbol, symbol.lower())

    def get_token_price(self, symbol: str) -> Optional[float]:
        """Get current USD price for a token."""
        coin_id = self._symbol_to_id(symbol)

        # Check cache
        now = time.time()
        if coin_id in self._price_cache:
            cached = self._price_cache[coin_id]
            if now - cached['timestamp'] < self._cache_ttl:
                return cached['price']

        url = f"{self.COINGECKO_BASE}/simple/price"
        params = {"ids": coin_id, "vs_currencies": "usd"}

        try:
            resp = requests.get(url, params=params, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                price = data.get(coin_id, {}).get("usd")
                if price is not None:
                    self._price_cache[coin_id] = {'price': price, 'timestamp': now}
                    return price
            elif resp.status_code == 429:
                logger.warning("CoinGecko rate limit hit")
                # Return cached value if available
                if coin_id in self._price_cache:
                    return self._price_cache[coin_id]['price']
        except Exception as e:
            logger.error(f"Failed to fetch price for {symbol}: {e}")

        return None

    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, float]:
        """Get prices for multiple tokens in one call."""
        coin_ids = [self._symbol_to_id(s) for s in symbols]
        ids_str = ",".join(coin_ids)

        url = f"{self.COINGECKO_BASE}/simple/price"
        params = {"ids": ids_str, "vs_currencies": "usd"}

        try:
            resp = requests.get(url, params=params, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                result = {}
                for symbol in symbols:
                    coin_id = self._symbol_to_id(symbol)
                    price = data.get(coin_id, {}).get("usd")
                    if price is not None:
                        result[symbol] = price
                        self._price_cache[coin_id] = {'price': price, 'timestamp': time.time()}
                return result
        except Exception as e:
            logger.error(f"Failed to fetch multiple prices: {e}")

        return {}

    def get_token_metadata(self, symbol: str) -> Dict[str, Any]:
        """Get detailed token metadata."""
        coin_id = self._symbol_to_id(symbol)
        url = f"{self.COINGECKO_BASE}/coins/{coin_id}"

        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch metadata for {symbol}: {e}")

        return {}

    def get_market_data(self, symbol: str) -> Dict[str, Any]:
        """Get market data including volume, market cap, etc."""
        coin_id = self._symbol_to_id(symbol)
        url = f"{self.COINGECKO_BASE}/coins/{coin_id}"
        params = {"localization": "false", "tickers": "false", "community_data": "false", "developer_data": "false"}

        try:
            resp = requests.get(url, params=params, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                market = data.get("market_data", {})
                return {
                    "price": market.get("current_price", {}).get("usd"),
                    "market_cap": market.get("market_cap", {}).get("usd"),
                    "volume_24h": market.get("total_volume", {}).get("usd"),
                    "price_change_24h": market.get("price_change_percentage_24h"),
                    "price_change_7d": market.get("price_change_percentage_7d"),
                    "ath": market.get("ath", {}).get("usd"),
                    "atl": market.get("atl", {}).get("usd"),
                    "circulating_supply": market.get("circulating_supply"),
                    "total_supply": market.get("total_supply"),
                }
        except Exception as e:
            logger.error(f"Failed to fetch market data for {symbol}: {e}")

        return {}

    def get_ohlc(self, symbol: str, days: int = 7) -> List[List[float]]:
        """Get OHLC data for charting."""
        coin_id = self._symbol_to_id(symbol)
        url = f"{self.COINGECKO_BASE}/coins/{coin_id}/ohlc"
        params = {"vs_currency": "usd", "days": days}

        try:
            resp = requests.get(url, params=params, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            logger.error(f"Failed to fetch OHLC for {symbol}: {e}")

        return []

    def get_gas_and_slippage_report(self) -> str:
        """Get current gas prices and estimated slippage info."""
        try:
            # Fetch ETH gas from Etherscan or similar
            gas_url = "https://api.etherscan.io/api?module=gastracker&action=gasoracle"
            resp = requests.get(gas_url, timeout=5)
            if resp.status_code == 200:
                data = resp.json().get("result", {})
                return f"""
Gas Report:
- Safe Low: {data.get('SafeGasPrice', 'N/A')} gwei
- Standard: {data.get('ProposeGasPrice', 'N/A')} gwei
- Fast: {data.get('FastGasPrice', 'N/A')} gwei
"""
        except Exception as e:
            logger.error(f"Failed to fetch gas: {e}")

        return "Gas data unavailable"

    def get_trending(self) -> List[Dict[str, Any]]:
        """Get trending coins."""
        url = f"{self.COINGECKO_BASE}/search/trending"

        try:
            resp = requests.get(url, headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return [item['item'] for item in data.get('coins', [])]
        except Exception as e:
            logger.error(f"Failed to fetch trending: {e}")

        return []
