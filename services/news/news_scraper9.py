import requests

class NewsScraper:
    """
    Real-world crypto news connector using CryptoPanic API.
    """
    def __init__(self, api_key=None):
        import os
        self.api_key = api_key or os.getenv("CRYPTOPANIC_API_KEY")

    def fetch_latest(self, symbols=None, kind="news"):
        url = "https://cryptopanic.com/api/v1/posts/"
        params = {
            "auth_token": self.api_key,
            "filter": kind,
            "currencies": ",".join(symbols) if symbols else None
        }
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            return resp.json().get("results", [])
        else:
            return []