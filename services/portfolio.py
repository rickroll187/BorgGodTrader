import os
import requests

class PortfolioService:
    """Real-world portfolio balances using Covalent API."""

    def __init__(self, wallet_address, rpc_url=None, api_key=None):
        self.wallet_address = wallet_address
        self.api_key = api_key or os.getenv("COVALENT_API_KEY")
        self.rpc_url = rpc_url

    def get_balances(self, chain_id=1):
        url = f"https://api.covalenthq.com/v1/{chain_id}/address/{self.wallet_address}/balances_v2/"
        params = {"key": self.api_key}
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            return {
                item['contract_ticker_symbol']: float(item['balance']) / 10 ** item['contract_decimals']
                for item in data['data']['items']
            }
        return {}

    def get_balance(self, asset, chain_id=1):
        return self.get_balances(chain_id).get(asset, 0)

    def get_portfolio_overview(self, tokeninfo_service):
        balances = self.get_balances()
        return balances
