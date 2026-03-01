"""
🎫 Jira / Redmine Tiket Boshqaruv API
======================================

Endpointlar:
  GET  /api/v1/tickets/status          — Jira/Redmine ulanish holati
  POST /api/v1/tickets/{case_id}/create — Murojaat uchun qo'lda tiket yaratish
  GET  /api/v1/tickets/{case_id}        — Murojaat tiket ma'lumotlari
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models import Case, AuditLog, AuditAction
from app.api.v1.auth import require_investigator_or_above, get_current_user
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["tickets"])


@router.get("/status")
async def ticket_service_status(
    current_user: User = Depends(require_investigator_or_above),
):
    """
    Jira / Redmine ulanish holatini tekshiradi.
    Admin paneldagi "Tiket tizimi" widget uchun.
    """
    from app.services.jira_integration import ticket_service
    health = await ticket_service.health_check()
    return health


@router.post("/{case_id}/create")
async def create_ticket_for_case(
    case_id: str,
    request: Request,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    Murojaat uchun qo'lda Jira/Redmine tiket yaratadi.
    Agar tiket allaqachon yaratilgan bo'lsa — mavjud tiket ma'lumotini qaytaradi.
    """
    result = await db.execute(select(Case).where(Case.external_id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Murojaat topilmadi")

    # Agar tiket allaqachon yaratilgan bo'lsa
    if case.jira_ticket_id:
        return {
            "already_exists": True,
            "ticket_id": case.jira_ticket_id,
            "ticket_url": case.jira_ticket_url,
            "message": f"Bu murojaat uchun tiket allaqachon mavjud: {case.jira_ticket_id}",
        }

    from app.services.jira_integration import ticket_service
    from app.core.security import decrypt_case_content

    if not ticket_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Tiket tizimi sozlanmagan. .env faylida JIRA_URL va JIRA_TOKEN ni o'rnating.",
        )

    # Tavsifni shifrlashdan chiqarish
    description = decrypt_case_content(case.description_encrypted) if case.description_encrypted else ""

    ticket_result = await ticket_service.create_ticket_for_case(
        case_id=case.external_id,
        category=case.category.value if hasattr(case.category, "value") else str(case.category),
        priority=case.priority.value if hasattr(case.priority, "value") else str(case.priority),
        description=description,
        is_anonymous=case.is_anonymous,
    )

    if ticket_result.skipped:
        return {
            "created": False,
            "skipped": True,
            "reason": ticket_result.skip_reason,
            "message": f"Tiket yaratilmadi: {ticket_result.skip_reason}",
        }

    if not ticket_result.created:
        raise HTTPException(
            status_code=502,
            detail=f"Tiket yaratishda xato: {ticket_result.error}",
        )

    # Tiket ID ni case ga saqlash
    case.jira_ticket_id = ticket_result.ticket_id
    case.jira_ticket_url = ticket_result.url

    # Audit log
    db.add(AuditLog(
        user_id=current_user.id,
        case_id=case.id,
        action=AuditAction.CASE_UPDATE,
        payload={
            "action": "ticket_created",
            "ticket_id": ticket_result.ticket_id,
            "ticket_url": ticket_result.url,
            "system": ticket_result.system,
        },
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()

    logger.info(
        f"Qo'lda tiket yaratildi [{ticket_result.system}]: "
        f"{ticket_result.ticket_id} → {case_id} (by {current_user.username})"
    )

    return {
        "created": True,
        "ticket_id": ticket_result.ticket_id,
        "ticket_url": ticket_result.url,
        "system": ticket_result.system,
        "message": f"Tiket muvaffaqiyatli yaratildi: {ticket_result.ticket_id}",
    }


@router.get("/{case_id}")
async def get_ticket_info(
    case_id: str,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    """
    Murojaat uchun tiket ma'lumotlarini qaytaradi.
    """
    result = await db.execute(select(Case).where(Case.external_id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Murojaat topilmadi")

    if not case.jira_ticket_id:
        return {
            "has_ticket": False,
            "case_id": case_id,
            "message": "Bu murojaat uchun tiket mavjud emas",
        }

    return {
        "has_ticket": True,
        "case_id": case_id,
        "ticket_id": case.jira_ticket_id,
        "ticket_url": case.jira_ticket_url,
    }

