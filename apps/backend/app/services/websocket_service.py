from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.connections.discard(websocket)

    async def broadcast(self, payload: dict):
        for websocket in tuple(self.connections):
            try:
                await websocket.send_json(payload)
            except Exception:
                self.disconnect(websocket)
