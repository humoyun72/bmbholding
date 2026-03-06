"""
WebSocket endpoint for real-time admin notifications.
"""
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.security import decode_token
from app.services.websocket_manager import manager

router = APIRouter(tags=["websocket"])
logger = logging.getLogger(__name__)


@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """
    Connect with: ws://host/api/ws/notifications?token=<jwt>
    Only admin and investigator roles are allowed.
    """
    # WebSocket'da Query() ishlamaydi — query_params dan qo'lda olamiz
    token = websocket.query_params.get("token", "")

    if not token:
        await websocket.accept()
        await websocket.close(code=4001, reason="Token ko'rsatilmagan")
        return

    payload = decode_token(token)
    if not payload:
        logger.warning(f"WS invalid token: {token[:40]}...")
        await websocket.accept()
        await websocket.close(code=4001, reason="Noto'g'ri token")
        return

    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or role not in ("admin", "investigator"):
        await websocket.accept()
        await websocket.close(code=4003, reason="Ruxsat berilmagan")
        return

    logger.info(f"WS auth OK: user_id={user_id}, role={role}")
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            if data == '{"type":"ping"}':
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(user_id)

