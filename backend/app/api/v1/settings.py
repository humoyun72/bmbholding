"""
Tizim sozlamalari API
GET  /api/v1/settings          — barcha sozlamalarni olish
PUT  /api/v1/settings          — sozlamalarni yangilash (admin)
GET  /api/v1/settings/public   — public sozlamalar (login talab qilmaydi)
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from app.core.database import get_db
from app.models import SystemSettings, AuditLog, AuditAction, User
from app.api.v1.auth import get_current_user, require_admin

router = APIRouter(prefix="/settings", tags=["settings"])

# Default sozlamalar — DB bo'sh bo'lganda ishlatiladigan qiymatlar
DEFAULTS = {
    # Tizim
    "company_name": "Company",
    "system_language": "uz",
    "timezone": "Asia/Tashkent",
    # Bot
    "bot_admin_group_id": "",
    "bot_welcome_message": "Xush kelibsiz! Bu bot orqali anonim murojaat yuborishingiz mumkin.",
    "bot_working_hours_start": "08:00",
    "bot_working_hours_end": "18:00",
    "bot_working_days": "1,2,3,4,5",  # 1=Dushanba...7=Yakshanba
    "bot_languages": "uz,ru,en",
    "bot_outside_hours_message": "Ish vaqti 08:00-18:00. Murojaatingiz qabul qilindi va ko'rib chiqiladi.",
    # Bildirishnomalar
    "notify_daily_report": "true",
    "notify_daily_report_time": "18:00",
    "notify_weekly_report": "true",
    "notify_weekly_report_day": "1",
    "notify_weekly_report_time": "09:00",
}


async def get_all_settings(db: AsyncSession) -> dict:
    """DB dan barcha sozlamalarni o'qib, defaults bilan birlashtiradi."""
    result = await db.execute(select(SystemSettings))
    rows = {row.key: row.value for row in result.scalars().all()}
    # Default qiymatlar bilan birlashtirish
    merged = {**DEFAULTS, **{k: v for k, v in rows.items() if v is not None}}
    return merged


async def set_setting(db: AsyncSession, key: str, value: str):
    """Bir sozlamani DB ga yozadi yoki yangilaydi."""
    result = await db.execute(select(SystemSettings).where(SystemSettings.key == key))
    row = result.scalar_one_or_none()
    if row:
        row.value = value
    else:
        db.add(SystemSettings(key=key, value=value))


@router.get("")
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Barcha tizim sozlamalarini qaytaradi."""
    return await get_all_settings(db)


@router.get("/public")
async def get_public_settings(db: AsyncSession = Depends(get_db)):
    """Login talab qilmagan public sozlamalar (company_name, languages va h.k.)."""
    all_s = await get_all_settings(db)
    return {
        "company_name": all_s.get("company_name", "Company"),
        "system_language": all_s.get("system_language", "uz"),
        "bot_languages": all_s.get("bot_languages", "uz,ru,en"),
    }


@router.put("")
async def update_settings(
    body: dict,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Tizim sozlamalarini yangilaydi (faqat admin)."""
    allowed_keys = set(DEFAULTS.keys())
    updated = []

    for key, value in body.items():
        if key not in allowed_keys:
            continue
        if value is None:
            continue
        await set_setting(db, key, str(value))
        updated.append(key)

    if updated:
        db.add(AuditLog(
            user_id=current_user.id,
            action=AuditAction.USER_UPDATE,
            entity_type="system_settings",
            entity_id="system",
            payload={"updated_keys": updated},
        ))
        await db.commit()

    return {"message": f"{len(updated)} ta sozlama saqlandi", "updated": updated}


@router.post("/test-report")
async def send_test_report(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Darhol kunlik hisobot xabarini yuboradi (faqat admin).
    Test maqsadida ishlatiladi.
    """
    from app.bot.reports import send_daily_report
    from app.core.config import settings as app_settings

    chat_id = app_settings.ADMIN_CHAT_ID
    if not chat_id:
        raise HTTPException(
            status_code=400,
            detail="ADMIN_CHAT_ID sozlanmagan. .env faylida ADMIN_CHAT_ID ni o'rnating.",
        )

    try:
        await send_daily_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Xabar yuborishda xato: {str(e)}")

    # Audit log
    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.REPORT_SENT,
        entity_type="report",
        entity_id="test",
        payload={"triggered_by": str(current_user.id), "type": "test_daily"},
    ))
    await db.commit()

    return {"sent": True, "chat_id": str(chat_id)}



