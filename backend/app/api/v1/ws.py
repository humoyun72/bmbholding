"""
WebSocket endpoint for real-time admin notifications.
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.core.security import decode_token
from app.services.websocket_manager import manager

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    token: str = Query(...),
):
    """
    Connect with: ws://host/api/ws/notifications?token=<jwt>
    Only admin and investigator roles are allowed.
    """
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = payload.get("sub")
    role = payload.get("role")
    if not user_id or role not in ("admin", "investigator"):
        await websocket.close(code=4003, reason="Forbidden")
        return

    await manager.connect(websocket, user_id)
    try:
        # Keep connection alive — wait for client pings or disconnect
        while True:
            data = await websocket.receive_text()
            # client can send {"type":"ping"} — we reply pong
            if data == '{"type":"ping"}':
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(user_id)

