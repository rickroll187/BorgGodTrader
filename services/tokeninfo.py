import json
import os
import requests
from web3 import Web3

class TokenInfoService:
    """Token metadata and pricing helper."""

    def __init__(self, rpc_url=None):
        self.rpc_url = rpc_url
        self.web3 = Web3(Web3.HTTPProvider(rpc_url)) if rpc_url else None
        abi_path = os.path.join(os.path.dirname(__file__), "execution", "erc20_abi.json")
        if not os.path.exists(abi_path):
            abi_path = os.path.join(os.path.dirname(__file__), "execution", "ERC20 ABI.json")
        self.erc20_abi = None
        if os.path.exists(abi_path):
            with open(abi_path) as f:
                self.erc20_abi = json.load(f)

    def get_token_price(self, symbol):
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": symbol.lower(), "vs_currencies": "usd"}
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get(symbol.lower(), {}).get("usd", None)
        return None

    def get_token_metadata(self, symbol):
        url = f"https://api.coingecko.com/api/v3/coins/{symbol.lower()}"
        resp = requests.get(url)
        if resp.status_code == 200:
            return resp.json()
        return {}

    def get_token_decimals(self, address):
        if not self.web3 or not self.erc20_abi:
            return None
        address = self.web3.to_checksum_address(address)
        contract = self.web3.eth.contract(address=address, abi=self.erc20_abi)
        return contract.functions.decimals().call()

    def get_gas_and_slippage_report(self):
        return "Gas and slippage metrics are not implemented in the stub."
