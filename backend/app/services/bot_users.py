"""
🤖 BotUser servis moduli
========================
Telegram bot foydalanuvchilarini DB da saqlash va boshqarish.

Funksiyalar:
  - get_or_create_bot_user(telegram_id) → BotUser
  - update_bot_user_lang(telegram_id, lang) → None
  - get_bot_user_lang(telegram_id) → str
"""
import logging
from datetime import datetime, timezone

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models import BotUser

logger = logging.getLogger(__name__)

DEFAULT_LANG = "uz"
SUPPORTED_LANGS = ("uz", "ru", "en")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def get_or_create_bot_user(telegram_id: int) -> BotUser:
    """
    Telegram foydalanuvchisini DB dan oladi yoki yangi yozuv yaratadi.
    Har chaqiruvda last_active yangilanadi.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = BotUser(
                telegram_id=telegram_id,
                lang=DEFAULT_LANG,
                first_seen=_utcnow(),
                last_active=_utcnow(),
            )
            db.add(user)
            logger.info(f"New BotUser created: telegram_id={telegram_id}")
        else:
            user.last_active = _utcnow()

        await db.commit()
        await db.refresh(user)
        return user


async def update_bot_user_lang(telegram_id: int, lang: str) -> None:
    """
    Foydalanuvchi tilini DB ga yozadi.
    Noto'g'ri til berilsa — DEFAULT_LANG ishlatiladi.
    """
    if lang not in SUPPORTED_LANGS:
        lang = DEFAULT_LANG

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(BotUser).where(BotUser.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()

        if user is None:
            user = BotUser(
                telegram_id=telegram_id,
                lang=lang,
                first_seen=_utcnow(),
                last_active=_utcnow(),
            )
            db.add(user)
            logger.info(f"BotUser created on lang update: telegram_id={telegram_id}, lang={lang}")
        else:
            user.lang = lang
            user.last_active = _utcnow()
            logger.info(f"BotUser lang updated: telegram_id={telegram_id}, lang={lang}")

        await db.commit()


async def get_bot_user_lang(telegram_id: int) -> str:
    """
    Foydalanuvchi tilini DB dan qaytaradi.
    Agar topilmasa — DEFAULT_LANG qaytaradi.
    """
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(BotUser.lang).where(BotUser.telegram_id == telegram_id)
        )
        lang = result.scalar_one_or_none()

    if lang and lang in SUPPORTED_LANGS:
        return lang
    return DEFAULT_LANG

