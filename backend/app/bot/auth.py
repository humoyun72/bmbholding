"""
Bot uchun admin/investigator autentifikatsiya funksiyalari.

Telegram ID bo'yicha admin panel foydalanuvchisini aniqlash va
ruxsatlarni tekshirish.
"""
import logging
from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.models import User, UserRole

logger = logging.getLogger(__name__)


async def get_admin_user(telegram_id: int) -> User | None:
    """
    Telegram ID bo'yicha admin panel foydalanuvchisini qaytaradi.

    Args:
        telegram_id: Telegram user ID

    Returns:
        User obyekti yoki None (agar topilmasa yoki bog'lanmagan bo'lsa)
    """
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(User).where(
                    User.telegram_chat_id == telegram_id,
                    User.is_active == True,
                )
            )
            return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"get_admin_user xatosi (telegram_id={telegram_id}): {e}")
        return None


async def is_admin(telegram_id: int) -> bool:
    """
    Foydalanuvchi admin ekanligini tekshiradi.

    Args:
        telegram_id: Telegram user ID

    Returns:
        True agar foydalanuvchi admin bo'lsa
    """
    user = await get_admin_user(telegram_id)
    return user is not None and user.role == UserRole.ADMIN


async def is_investigator_or_above(telegram_id: int) -> bool:
    """
    Foydalanuvchi investigator yoki admin ekanligini tekshiradi.

    Args:
        telegram_id: Telegram user ID

    Returns:
        True agar foydalanuvchi investigator yoki admin bo'lsa
    """
    user = await get_admin_user(telegram_id)
    if user is None:
        return False
    return user.role in (UserRole.ADMIN, UserRole.INVESTIGATOR)


async def require_admin_permission(telegram_id: int) -> tuple[bool, User | None]:
    """
    Admin ruxsatini tekshiradi va foydalanuvchini qaytaradi.

    Args:
        telegram_id: Telegram user ID

    Returns:
        (has_permission: bool, user: User | None)
    """
    user = await get_admin_user(telegram_id)
    if user is None:
        return False, None
    if user.role not in (UserRole.ADMIN, UserRole.INVESTIGATOR):
        return False, None
    return True, user


async def require_admin_only(telegram_id: int) -> tuple[bool, User | None]:
    """
    Faqat admin ruxsatini tekshiradi.

    Args:
        telegram_id: Telegram user ID

    Returns:
        (has_permission: bool, user: User | None)
    """
    user = await get_admin_user(telegram_id)
    if user is None:
        return False, None
    if user.role != UserRole.ADMIN:
        return False, None
    return True, user

