from web3 import Web3
import pandas as pd

class PortfolioService:
    def __init__(self, wallet_address, rpc_url):
        self.wallet_address = Web3.to_checksum_address(wallet_address)
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))

    def get_portfolio_overview(self, tokeninfo_service):
        """Returns DataFrame with token, balance, and USD value."""
        tokens = tokeninfo_service.get_token_list()
        portfolio = []
        for t in tokens:
            try:
                contract = self.web3.eth.contract(address=Web3.to_checksum_address(t['address']), abi=tokeninfo_service.erc20_abi)
                bal = contract.functions.balanceOf(self.wallet_address).call()
                decimals = t.get('decimals', 18)
                normalized = bal / (10 ** decimals)
                price = tokeninfo_service.get_token_price_usd(t['address'])
                portfolio.append({
                    "Token": t['symbol'],
                    "Balance": normalized,
                    "USD Value": normalized * price
                })
            except Exception:
                continue
        return pd.DataFrame(portfolio)