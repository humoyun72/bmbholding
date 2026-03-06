"""
Telegram Bot Rate Limiting — Redis yordamida.

Har bir foydalanuvchi uchun amal bo'yicha so'rovlar soni cheklanadi.
Limit oshganda foydalanuvchiga ogohlantirish xabari yuboriladi.

Tavsiya etilgan limitlar:
  - start       : 30 ta / 60 soniya
  - report      : 5 ta  / 300 soniya (5 daqiqa)
  - file_upload : 10 ta / 60 soniya
  - check_status: 20 ta / 60 soniya
  - followup    : 10 ta / 60 soniya
"""
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Limitlar jadvali: {action: (limit, window_seconds)} ──────────────────────
RATE_LIMITS: dict[str, tuple[int, int]] = {
    "start":        (30, 60),
    "report":       (5, 300),
    "file_upload":  (10, 60),
    "check_status": (20, 60),
    "followup":     (10, 60),
    "group_action": (5, 60),   # Bitta case ga 1 daqiqada 5 ta guruh amali
    "default":      (30, 60),
}

_redis_client = None


def _get_redis():
    global _redis_client
    if _redis_client is None:
        import redis.asyncio as aioredis
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


async def check_rate_limit(user_id: int, action: str) -> tuple[bool, int]:
    """
    Foydalanuvchi limitini tekshiradi.

    Returns:
        (allowed: bool, retry_after: int)
        - allowed=True  → so'rov qabul qilinadi
        - allowed=False → blok, retry_after soniyadan keyin urinib ko'rish
    """
    limit, window = RATE_LIMITS.get(action, RATE_LIMITS["default"])
    key = f"bot:rl:{user_id}:{action}"

    try:
        redis = _get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)

        if count > limit:
            ttl = await redis.ttl(key)
            logger.warning(
                f"Rate limit exceeded: user_id={user_id} action={action} "
                f"count={count} limit={limit}"
            )
            return False, max(ttl, 1)

        return True, 0

    except Exception as e:
        # Redis ishlamasa — bloklamaymiz (availability ustunligi)
        logger.error(f"Rate limit Redis xato: {e} — so'rov o'tkazib yuborildi")
        return True, 0


async def check_case_rate_limit(case_id: str) -> tuple[bool, int]:
    """
    Bitta case uchun guruh amallarini limitlaydi.
    1 daqiqada 5 tadan ko'p amal bo'lmasligi kerak.

    Returns:
        (allowed: bool, retry_after: int)
    """
    limit, window = RATE_LIMITS.get("group_action", (5, 60))
    key = f"bot:rl:case:{case_id}:group_action"

    try:
        redis = _get_redis()
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)

        if count > limit:
            ttl = await redis.ttl(key)
            logger.warning(
                f"Case rate limit exceeded: case_id={case_id} "
                f"count={count} limit={limit}"
            )
            return False, max(ttl, 1)

        return True, 0

    except Exception as e:
        logger.error(f"Case rate limit Redis xato: {e} — so'rov o'tkazib yuborildi")
        return True, 0


def rate_limited(action: str):
    """
    Decorator: handler funksiyani rate limiting bilan o'raydi.

    Ishlatish:
        @rate_limited("report")
        async def confirm_send(update, context):
            ...
    """
    def decorator(func):
        async def wrapper(update, context):
            user = update.effective_user
            if not user:
                return await func(update, context)

            allowed, retry_after = await check_rate_limit(user.id, action)
            if not allowed:
                minutes = retry_after // 60
                seconds = retry_after % 60

                if minutes > 0:
                    time_str = f"{minutes} daqiqa {seconds} soniya"
                else:
                    time_str = f"{seconds} soniya"

                msg = (
                    f"⏳ *Juda ko'p so'rov yuborildi.*\n\n"
                    f"{time_str}dan keyin urinib ko'ring."
                )

                if update.callback_query:
                    await update.callback_query.answer(
                        "⏳ Juda ko'p so'rov. Biroz kuting.", show_alert=True
                    )
                elif update.message:
                    from telegram.constants import ParseMode
                    await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
                return

            return await func(update, context)
        return wrapper
    return decorator

