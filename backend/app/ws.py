import asyncio
import json
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._clients: set[WebSocket] = set()
        self.queue: asyncio.Queue = asyncio.Queue()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self._clients.add(ws)

    def disconnect(self, ws: WebSocket):
        self._clients.discard(ws)

    async def broadcast(self, payload: dict):
        dead = set()
        message = json.dumps(payload, default=str)
        for ws in self._clients:
            try:
                await ws.send_text(message)
            except Exception:
                dead.add(ws)
        for ws in dead:
            self._clients.discard(ws)

    async def run_broadcaster(self):
        """Drain the internal queue and fan out to all connected clients."""
        while True:
            payload = await self.queue.get()
            await self.broadcast(payload)


manager = ConnectionManager()
