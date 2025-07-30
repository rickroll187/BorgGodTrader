import json
import os
from web3 import Web3

class TokenInfoService:
    def __init__(self, rpc_url):
        self.web3 = Web3(Web3.HTTPProvider(rpc_url))
        abi_path = os.path.join(os.path.dirname(__file__), "../execution/erc20_abi.json")
        with open(abi_path) as f:
            self.erc20_abi = json.load(f)

    def get_token_list(self):
        # Example: Pull from list, on-chain, or config (for demo, hardcode major tokens)
        return [
            {"symbol": "USDC", "address": "0xA0b86991c6218b36c1d19d4a2e9eb0ce3606eb48", "decimals": 6},
            {"symbol": "WETH", "address": "0xC02aaa39b223FE8D0A0e5C4F27eAD9083C756Cc2", "decimals": 18},
            {"symbol": "DAI", "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F", "decimals": 18},
            # Add more tokens as needed
        ]

    def get_token_decimals(self, address):
        address = self.web3.to_checksum_address(address)
        contract = self.web3.eth.contract(address=address, abi=self.erc20_abi)
        return contract.functions.decimals().call()

    def get_token_price_usd(self, address):
        # You can plug in Coingecko, 1inch, oracles, etc. (stub: returns 1 for stablecoins)
        return 1