"""
app/services/ws_manager.py
---------------------------
In-process WebSocket connection manager.

Stores one or more active WebSocket connections per user UUID.
The notification router calls broadcast_to_user() after creating
a notification so clients receive push updates instantly.
"""

import asyncio
import json
import uuid
from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket

from app.core.logging import get_logger

logger = get_logger("ws_manager")


class ConnectionManager:
    """Thread-safe (asyncio-safe) registry of active WebSocket connections."""

    def __init__(self) -> None:
        # user_id -> list of active WebSocket objects
        self._connections: Dict[uuid.UUID, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, user_id: uuid.UUID) -> None:
        await websocket.accept()
        self._connections[user_id].append(websocket)
        logger.debug("WS connected | user=%s | total=%d", user_id, len(self._connections[user_id]))

    def disconnect(self, websocket: WebSocket, user_id: uuid.UUID) -> None:
        conns = self._connections.get(user_id, [])
        if websocket in conns:
            conns.remove(websocket)
        if not conns:
            self._connections.pop(user_id, None)
        logger.debug("WS disconnected | user=%s", user_id)

    async def broadcast_to_user(self, user_id: uuid.UUID, payload: dict) -> None:
        """Send a JSON payload to all connections for this user."""
        conns = list(self._connections.get(user_id, []))
        if not conns:
            return
        dead: List[WebSocket] = []
        message = json.dumps(payload, default=str)
        for ws in conns:
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, user_id)

    async def keep_alive(self, websocket: WebSocket) -> None:
        """Send periodic pings to keep the connection alive."""
        try:
            while True:
                await asyncio.sleep(30)
                await websocket.send_text(json.dumps({"type": "ping"}))
        except Exception:
            pass  # caller handles disconnect


# Singleton instance shared across the application
manager = ConnectionManager()
