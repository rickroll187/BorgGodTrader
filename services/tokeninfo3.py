import requests

class TokenInfoService:
    """
    Real token info using CoinGecko API.
    """
    def __init__(self, rpc_url=None):
        self.rpc_url = rpc_url

    def get_token_price(self, symbol):
        url = f"https://api.coingecko.com/api/v3/simple/price"
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