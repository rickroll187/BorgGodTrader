import asyncio
import websockets
import json

class WebSocketClient:
    """
    Async WebSocket client for real-time feeds.
    """
    def __init__(self, url, on_message):
        self.url = url
        self.on_message = on_message
        self.running = False

    async def listen(self):
        self.running = True
        async with websockets.connect(self.url) as ws:
            while self.running:
                try:
                    msg = await ws.recv()
                    self.on_message(json.loads(msg))
                except Exception:
                    continue

    def start(self):
        asyncio.get_event_loop().run_until_complete(self.listen())

    def stop(self):
        self.running = False