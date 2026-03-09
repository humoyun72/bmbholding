"""
WebSocket Connection Manager + Redis Pub/Sub broadcast
"""
import json
import logging
import asyncio
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Channel name in Redis
WS_CHANNEL = "integrity:notifications"


class ConnectionManager:
    """Manages active WebSocket connections per user role."""

    def __init__(self):
        # { user_id: WebSocket }
        self._connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self._connections[user_id] = websocket
        logger.info(f"WS connected: user={user_id}, total={len(self._connections)}")

    def disconnect(self, user_id: str):
        self._connections.pop(user_id, None)
        logger.info(f"WS disconnected: user={user_id}, total={len(self._connections)}")

    async def send_to(self, user_id: str, data: dict):
        ws = self._connections.get(user_id)
        if ws:
            try:
                await ws.send_json(data)
            except Exception as e:
                logger.warning(f"WS send failed for {user_id}: {e}")
                self.disconnect(user_id)

    async def broadcast(self, data: dict):
        """Send to all connected clients."""
        dead = []
        for user_id, ws in list(self._connections.items()):
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(user_id)
        for uid in dead:
            self.disconnect(uid)

    @property
    def connected_count(self) -> int:
        return len(self._connections)


# Singleton
manager = ConnectionManager()


async def publish_notification(redis_client, event_type: str, payload: dict):
    """Publish a notification to Redis channel for broadcast."""
    message = json.dumps({"type": event_type, **payload})
    try:
        await redis_client.publish(WS_CHANNEL, message)
    except Exception as e:
        logger.error(f"Redis publish failed: {e}")


async def notify_ws(event_type: str, payload: dict):
    """
    WebSocket notification yuborish.
    Redis sozlangan bo'lsa — pub/sub orqali (multi-worker).
    Bo'lmasa — xotirada to'g'ridan broadcast (shared hosting, bitta worker).
    """
    from app.core.config import settings

    data = {"type": event_type, **payload}

    if settings.REDIS_URL:
        try:
            import redis.asyncio as aioredis
            r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await r.publish(WS_CHANNEL, json.dumps(data))
            await r.aclose()
            return
        except Exception as e:
            logger.warning(f"Redis notify xatosi, to'g'ridan broadcast: {e}")

    # Redis yo'q yoki xato — bitta jarayon ichida broadcast
    try:
        await manager.broadcast(data)
    except Exception as e:
        logger.error(f"Direct WS broadcast xatosi: {e}")


async def redis_subscriber(redis_url: str):
    """
    Background task: subscribe to Redis channel and broadcast
    incoming messages to all WebSocket clients.
    """
    import redis.asyncio as aioredis

    while True:
        try:
            r = aioredis.from_url(redis_url, decode_responses=True)
            pubsub = r.pubsub()
            await pubsub.subscribe(WS_CHANNEL)
            logger.info(f"Redis subscriber started on channel: {WS_CHANNEL}")

            async for message in pubsub.listen():
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        await manager.broadcast(data)
                    except Exception as e:
                        logger.error(f"WS broadcast error: {e}")
        except asyncio.CancelledError:
            logger.info("Redis subscriber cancelled")
            break
        except Exception as e:
            logger.error(f"Redis subscriber error: {e}. Reconnecting in 3s...")
            await asyncio.sleep(3)

