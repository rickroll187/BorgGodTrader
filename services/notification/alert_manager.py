import requests
import os

class AlertManager:
    def __init__(self, telegram_token=None, telegram_chat_id=None, discord_webhook=None):
        self.telegram_token = telegram_token or os.getenv("TELEGRAM_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.discord_webhook = discord_webhook or os.getenv("DISCORD_WEBHOOK")

    def send_telegram(self, message):
        if not (self.telegram_token and self.telegram_chat_id): return
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        data = {"chat_id": self.telegram_chat_id, "text": message}
        requests.post(url, data=data, timeout=5)

    def send_discord(self, message):
        if not self.discord_webhook: return
        requests.post(self.discord_webhook, json={"content": message}, timeout=5)