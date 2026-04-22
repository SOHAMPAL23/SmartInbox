"""
app/routers/ws.py
------------------
WebSocket endpoint for real-time notification push.

Connect:  ws://host/api/v1/ws/notifications?token=<access_token>

Protocol:
  Server → Client: JSON notification objects (same schema as REST /notifications)
  Server → Client: {"type": "ping"} every 30 s (keep-alive)
  Client disconnect: handled gracefully
"""

import asyncio
import uuid
from typing import Annotated

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, status

from app.auth.jwt_handler import decode_access_token
from app.core.logging import get_logger
from app.services.ws_manager import manager

router = APIRouter(tags=["WebSocket"])
logger = get_logger("router.ws")


@router.websocket("/ws/notifications")
async def ws_notifications(
    websocket: WebSocket,
    token: str = Query(..., description="Valid JWT access token"),
) -> None:
    """
    Real-time notification stream for the authenticated user.
    Authenticate via ?token= query param (browsers can't send Authorization headers on WS).
    """
    # ── Authenticate ─────────────────────────────────────────────────────────
    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        logger.warning("WS auth failed — closing connection")
        return

    await manager.connect(websocket, user_id)
    logger.info("WS open | user=%s", user_id)

    # ── Keep alive + listen for disconnect ────────────────────────────────────
    ping_task = asyncio.create_task(manager.keep_alive(websocket))
    try:
        while True:
            # We don't expect messages from the client, but we must await to
            # detect disconnect (raises WebSocketDisconnect)
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ping_task.cancel()
        manager.disconnect(websocket, user_id)
        logger.info("WS closed | user=%s", user_id)
