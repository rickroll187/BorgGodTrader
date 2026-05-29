import os
import requests
import logging
from typing import Dict, Optional, List
from decimal import Decimal

logger = logging.getLogger(__name__)


class PortfolioService:
    """
    Real-world portfolio tracking with multiple data sources.
    Supports Covalent API for on-chain balances and manual CEX balance tracking.
    """

    def __init__(self, wallet_address: str, rpc_url: Optional[str] = None, api_key: Optional[str] = None):
        self.wallet_address = wallet_address
        self.api_key = api_key or os.getenv("COVALENT_API_KEY")
        self.rpc_url = rpc_url
        self.cex_balances: Dict[str, Dict[str, float]] = {}
        self._balance_cache: Dict[str, Dict] = {}
        self._cache_ttl = 60
        self._last_fetch = 0

    def get_balances(self, chain_id: int = 1) -> Dict[str, float]:
        """Fetch on-chain balances from Covalent API."""
        if not self.api_key:
            logger.warning("No Covalent API key - returning empty balances")
            return {}

        url = f"https://api.covalenthq.com/v1/{chain_id}/address/{self.wallet_address}/balances_v2/"
        params = {"key": self.api_key}

        try:
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                balances = {}
                for item in data.get('data', {}).get('items', []):
                    symbol = item.get('contract_ticker_symbol')
                    if symbol and item.get('balance'):
                        decimals = item.get('contract_decimals', 18)
                        balance = float(item['balance']) / (10 ** decimals)
                        if balance > 0:
                            balances[symbol] = balance
                return balances
            else:
                logger.error(f"Covalent API error: {resp.status_code}")
        except Exception as e:
            logger.error(f"Failed to fetch balances: {e}")

        return {}

    def get_multichain_balances(self, chain_ids: List[int] = None) -> Dict[str, Dict[str, float]]:
        """Fetch balances across multiple chains."""
        if chain_ids is None:
            chain_ids = [1, 137, 42161, 10]  # ETH, Polygon, Arbitrum, Optimism

        all_balances = {}
        for chain_id in chain_ids:
            chain_name = self._chain_id_to_name(chain_id)
            all_balances[chain_name] = self.get_balances(chain_id)

        return all_balances

    def _chain_id_to_name(self, chain_id: int) -> str:
        chains = {
            1: "ethereum",
            137: "polygon",
            42161: "arbitrum",
            10: "optimism",
            56: "bsc",
            43114: "avalanche"
        }
        return chains.get(chain_id, f"chain_{chain_id}")

    def update_cex_balance(self, exchange: str, balances: Dict[str, float]):
        """Update cached CEX balances (called by exchange executors)."""
        self.cex_balances[exchange] = balances

    def get_cex_balances(self) -> Dict[str, Dict[str, float]]:
        """Get all tracked CEX balances."""
        return self.cex_balances.copy()

    def get_total_portfolio_value(self, prices: Dict[str, float]) -> float:
        """Calculate total portfolio value in USD."""
        total = 0.0

        # On-chain balances
        on_chain = self.get_balances()
        for symbol, balance in on_chain.items():
            if symbol in prices:
                total += balance * prices[symbol]

        # CEX balances
        for exchange, balances in self.cex_balances.items():
            for symbol, balance in balances.items():
                if symbol in prices:
                    total += balance * prices[symbol]

        return total

    def get_portfolio_overview(self, tokeninfo_service) -> dict:
        """Get a structured portfolio overview with prices."""
        overview = {
            "on_chain": {},
            "cex": {},
            "total_usd": 0.0
        }

        # Fetch on-chain
        on_chain = self.get_balances()
        for symbol, balance in on_chain.items():
            price = tokeninfo_service.get_token_price(symbol) or 0
            value = balance * price
            overview["on_chain"][symbol] = {
                "balance": balance,
                "price": price,
                "value_usd": value
            }
            overview["total_usd"] += value

        # CEX balances
        for exchange, balances in self.cex_balances.items():
            overview["cex"][exchange] = {}
            for symbol, balance in balances.items():
                price = tokeninfo_service.get_token_price(symbol) or 0
                value = balance * price
                overview["cex"][exchange][symbol] = {
                    "balance": balance,
                    "price": price,
                    "value_usd": value
                }
                overview["total_usd"] += value

        return overview

    def get_allocation(self) -> Dict[str, float]:
        """Get portfolio allocation percentages by asset."""
        # This would need prices to calculate properly
        # For now return raw balances as proxy
        all_balances = {}

        on_chain = self.get_balances()
        all_balances.update(on_chain)

        for exchange, balances in self.cex_balances.items():
            for symbol, balance in balances.items():
                all_balances[symbol] = all_balances.get(symbol, 0) + balance

        total = sum(all_balances.values())
        if total == 0:
            return {}

        return {symbol: balance / total for symbol, balance in all_balances.items()}
