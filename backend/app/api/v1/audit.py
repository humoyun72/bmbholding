from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional
import logging

from app.core.database import get_db
from app.models import AuditLog, User
from app.api.v1.auth import require_admin

router = APIRouter(prefix="/audit", tags=["audit"])
logger = logging.getLogger(__name__)


@router.get("", response_model=dict)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    user_id: Optional[str] = None,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if user_id:
        import uuid
        filters.append(AuditLog.user_id == uuid.UUID(user_id))

    base_query = select(AuditLog).options(selectinload(AuditLog.user))
    if filters:
        base_query = base_query.where(and_(*filters))

    count_query = select(func.count(AuditLog.id))
    if filters:
        count_query = count_query.where(and_(*filters))

    total_result = await db.execute(count_query)
    total = total_result.scalar()

    offset = (page - 1) * per_page
    result = await db.execute(
        base_query.order_by(AuditLog.created_at.desc()).offset(offset).limit(per_page)
    )
    logs = result.scalars().all()

    return {
        "items": [
            {
                "id": str(log.id),
                "action": log.action.value if hasattr(log.action, "value") else str(log.action),
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "ip_address": log.ip_address,
                "payload": log.payload,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "user": {
                    "id": str(log.user.id),
                    "username": log.user.username,
                    "full_name": log.user.full_name,
                    "role": log.user.role.value if hasattr(log.user.role, "value") else str(log.user.role),
                } if log.user else None,
                "case_id": str(log.case_id) if log.case_id else None,
            }
            for log in logs
        ],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": max(1, -(-total // per_page)),
    }


@router.get("/actions", response_model=list[str])
async def list_audit_actions(
    current_user: User = Depends(require_admin),
):
    """Barcha mavjud audit action'lar ro'yxati"""
    from app.models import AuditAction
    return [a.value for a in AuditAction]


@router.get("/retention/stats")
async def get_retention_stats(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Data retention statistikasi — nechta yozuv muddati yaqinlashmoqda.
    Admin dashboard uchun.
    """
    from app.services.retention import get_retention_stats as _get_stats
    return await _get_stats(db)


@router.post("/retention/run")
async def run_retention_now(
    current_user: User = Depends(require_admin),
):
    """
    Data retention'ni qo'lda ishga tushirish (admin only).
    Odatda har kecha 02:00 UTC da avtomatik ishlaydi.
    """
    from app.services.retention import run_retention
    logger.info(f"Manual retention triggered by {current_user.username}")
    stats = await run_retention()
    return {
        "message": "Data retention muvaffaqiyatli bajarildi",
        "stats": stats,
    }

