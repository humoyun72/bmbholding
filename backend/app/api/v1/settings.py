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


# ═══════════════════════════════════════════════════════════════════
# DEADLINE SOZLAMALARI
# ═══════════════════════════════════════════════════════════════════

DEADLINE_KEYS = {
    "critical_hours": "deadline_critical_hours",
    "high_hours":     "deadline_high_hours",
    "medium_hours":   "deadline_medium_hours",
    "low_hours":      "deadline_low_hours",
}
DEADLINE_DEFAULTS = {
    "critical_hours": 24,
    "high_hours":     72,
    "medium_hours":   168,
    "low_hours":      720,
}


@router.get("/deadlines")
async def get_deadline_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Hozirgi deadline sozlamalarini qaytaradi."""
    result = {}
    for api_key, db_key in DEADLINE_KEYS.items():
        row = await db.execute(select(SystemSettings).where(SystemSettings.key == db_key))
        setting = row.scalar_one_or_none()
        if setting and setting.value is not None:
            try:
                result[api_key] = int(setting.value)
            except (ValueError, TypeError):
                result[api_key] = DEADLINE_DEFAULTS[api_key]
        else:
            result[api_key] = DEADLINE_DEFAULTS[api_key]
    return result


@router.put("/deadlines")
async def update_deadline_settings(
    body: dict,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Deadline sozlamalarini yangilaydi (faqat admin)."""
    # Validatsiya
    vals = {}
    for api_key in DEADLINE_KEYS:
        if api_key not in body:
            raise HTTPException(status_code=422, detail=f"'{api_key}' maydoni kerak")
        try:
            v = int(body[api_key])
        except (ValueError, TypeError):
            raise HTTPException(status_code=422, detail=f"'{api_key}' butun son bo'lishi kerak")
        if v < 1:
            raise HTTPException(status_code=422, detail=f"'{api_key}' kamida 1 soat bo'lishi kerak")
        vals[api_key] = v

    # critical < high < medium < low
    if not (vals["critical_hours"] < vals["high_hours"] < vals["medium_hours"] < vals["low_hours"]):
        raise HTTPException(
            status_code=422,
            detail="Tartib: Kritik < Yuqori < O'rta < Past soatlar soni bo'lishi shart",
        )

    for api_key, db_key in DEADLINE_KEYS.items():
        await set_setting(db, db_key, str(vals[api_key]))

    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.USER_UPDATE,
        entity_type="deadline_settings",
        entity_id="system",
        payload=vals,
    ))
    await db.commit()

    # Redis keshni tozalash
    from app.services.deadline import invalidate_deadline_cache
    await invalidate_deadline_cache()

    return {"message": "Deadline sozlamalari saqlandi", "values": vals}


# ═══════════════════════════════════════════════════════════════════
# BILDIRISHNOMA SOZLAMALARI
# ═══════════════════════════════════════════════════════════════════

NOTIFICATION_KEYS = {
    "notify_24h_before":     {"default": "true",     "type": "bool"},
    "notify_2h_before":      {"default": "false",    "type": "bool"},
    "notify_on_overdue":     {"default": "true",     "type": "bool"},
    "notify_overdue_daily":  {"default": "true",     "type": "bool"},
    "notify_channel":        {"default": "telegram", "type": "str"},
    "daily_report_enabled":  {"default": "true",     "type": "bool"},
    "daily_report_time":     {"default": "18:00",    "type": "time"},
    "weekly_report_enabled": {"default": "true",     "type": "bool"},
    "weekly_report_day":     {"default": "0",        "type": "int"},
    "weekly_report_time":    {"default": "09:00",    "type": "time"},
}


def _parse_notif_value(key: str, raw):
    """Bildirishnoma qiymatini parse qiladi."""
    meta = NOTIFICATION_KEYS.get(key)
    if not meta:
        return None
    t = meta["type"]
    if t == "bool":
        if isinstance(raw, bool):
            return raw
        return str(raw).lower() in ("true", "1", "yes")
    if t == "int":
        return int(raw)
    if t == "time":
        s = str(raw).strip()
        if len(s) == 5 and s[2] == ":":
            h, m = s.split(":")
            if 0 <= int(h) <= 23 and 0 <= int(m) <= 59:
                return s
        raise ValueError(f"'{key}' — noto'g'ri vaqt formati (HH:MM kerak)")
    if t == "str":
        s = str(raw)
        if key == "notify_channel" and s not in ("telegram", "both"):
            raise ValueError("'notify_channel' faqat 'telegram' yoki 'both' bo'lishi mumkin")
        return s
    return str(raw)


@router.get("/notifications")
async def get_notification_settings(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bildirishnoma sozlamalarini qaytaradi."""
    all_s = await get_all_settings(db)
    result = {}
    for key, meta in NOTIFICATION_KEYS.items():
        db_key = f"notif_{key}"
        raw = all_s.get(db_key, meta["default"])
        try:
            result[key] = _parse_notif_value(key, raw)
        except Exception:
            result[key] = _parse_notif_value(key, meta["default"])
    return result


@router.put("/notifications")
async def update_notification_settings(
    body: dict,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Bildirishnoma sozlamalarini yangilaydi (faqat admin)."""
    parsed = {}
    for key, meta in NOTIFICATION_KEYS.items():
        if key not in body:
            continue
        try:
            parsed[key] = _parse_notif_value(key, body[key])
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    if "weekly_report_day" in parsed:
        d = parsed["weekly_report_day"]
        if d < 0 or d > 6:
            raise HTTPException(status_code=422, detail="'weekly_report_day' 0-6 oralig'ida bo'lishi kerak")

    for key, value in parsed.items():
        db_key = f"notif_{key}"
        db_val = str(value).lower() if isinstance(value, bool) else str(value)
        await set_setting(db, db_key, db_val)

    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.USER_UPDATE,
        entity_type="notification_settings",
        entity_id="system",
        payload={k: str(v) for k, v in parsed.items()},
    ))
    await db.commit()

    return {"message": "Bildirishnoma sozlamalari saqlandi"}


@router.post("/notifications/apply")
async def apply_notification_settings(
    current_user: User = Depends(require_admin),
):
    """
    Scheduler sozlamalarini qayta yuklash (restart).
    Sozlamalar o'zgarganidan keyin chaqiriladi.
    """
    # Hozircha bu endpoint faqat "qo'llanildi" belgisini qaytaradi.
    # Report scheduler keyingi iteratsiyada avtomatik yangi sozlamalarni o'qiydi.
    return {"message": "Sozlamalar qo'llanildi — scheduler keyingi siklda yangilanadi"}


@router.post("/test-weekly-report")
async def send_test_weekly_report(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Darhol haftalik hisobot yuboradi (faqat admin)."""
    from app.bot.reports import send_weekly_report
    from app.core.config import settings as app_settings

    chat_id = app_settings.ADMIN_CHAT_ID
    if not chat_id:
        raise HTTPException(status_code=400, detail="ADMIN_CHAT_ID sozlanmagan")

    try:
        await send_weekly_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Xabar yuborishda xato: {str(e)}")

    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.REPORT_SENT,
        entity_type="report",
        entity_id="test",
        payload={"triggered_by": str(current_user.id), "type": "test_weekly"},
    ))
    await db.commit()

    return {"sent": True, "chat_id": str(chat_id)}
