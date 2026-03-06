"""
Avtomatik deadline hisoblash xizmati.
Priority asosida due_at sanasini aniqlaydi.
DB dan sozlamalarni o'qiydi, Redis kesh (5 daqiqa).
"""
import json
import logging
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

# Default qiymatlar — DB bo'sh bo'lganda ishlatiladi
DEADLINE_HOURS: dict[str, int] = {
    "critical": 24,      # 1 kun
    "high":     72,      # 3 kun
    "medium":   168,     # 7 kun
    "low":      720,     # 30 kun
}

_REDIS_KEY = "deadline_hours_cache"
_CACHE_TTL = 300  # 5 daqiqa


async def _get_deadline_hours_from_db() -> dict[str, int]:
    """DB dan deadline sozlamalarini o'qiydi, Redis kesh bilan."""
    # 1. Redis keshdan o'qishga urinish
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        cached = await r.get(_REDIS_KEY)
        if cached:
            await r.aclose()
            return json.loads(cached)
    except Exception:
        r = None

    # 2. DB dan o'qish
    try:
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select
        from app.models import SystemSettings

        hours = dict(DEADLINE_HOURS)  # default nusxa
        async with AsyncSessionLocal() as db:
            for pri in ("critical", "high", "medium", "low"):
                key = f"deadline_{pri}_hours"
                result = await db.execute(
                    select(SystemSettings.value).where(SystemSettings.key == key)
                )
                val = result.scalar_one_or_none()
                if val is not None:
                    try:
                        hours[pri] = int(val)
                    except (ValueError, TypeError):
                        pass

        # 3. Redis ga keshla
        try:
            if r is None:
                import redis.asyncio as aioredis
                from app.core.config import settings
                r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
            await r.set(_REDIS_KEY, json.dumps(hours), ex=_CACHE_TTL)
            await r.aclose()
        except Exception:
            pass

        return hours
    except Exception as e:
        logger.warning(f"DB dan deadline o'qishda xato, default ishlatiladi: {e}")
        return dict(DEADLINE_HOURS)


async def invalidate_deadline_cache():
    """Redis keshdagi deadline sozlamalarini o'chiradi."""
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await r.delete(_REDIS_KEY)
        await r.aclose()
    except Exception:
        pass


async def calculate_due_at(priority, created_at: datetime | None = None) -> datetime:
    """
    Priority asosida deadline sanasini hisoblaydi.
    DB dan sozlamalar o'qiladi (Redis kesh).
    """
    if created_at is None:
        created_at = datetime.now(timezone.utc)

    pri_value = priority.value if hasattr(priority, "value") else str(priority)

    hours_map = await _get_deadline_hours_from_db()
    hours = hours_map.get(pri_value, hours_map.get("medium", 168))
    return created_at + timedelta(hours=hours)


def calculate_due_at_sync(priority, created_at: datetime | None = None) -> datetime:
    """
    Sinxron versiya — DB dan o'qimaydi, faqat default DEADLINE_HOURS ishlatadi.
    Bot handler'larda async variant ishlatilishi kerak.
    """
    if created_at is None:
        created_at = datetime.now(timezone.utc)

    pri_value = priority.value if hasattr(priority, "value") else str(priority)
    hours = DEADLINE_HOURS.get(pri_value, DEADLINE_HOURS["medium"])
    return created_at + timedelta(hours=hours)
