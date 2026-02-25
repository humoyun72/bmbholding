from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from typing import Optional
import uuid
import logging

from app.core.database import get_db
from app.core.security import decrypt_text, encrypt_text
from app.models import (
    Case, CaseComment, AuditLog, AuditAction, CaseStatus,
    CasePriority, CaseCategory, User, UserRole
)
from app.schemas.cases import (
    CaseResponse, CaseListResponse, CaseDetailResponse,
    AssignCaseRequest, ChangeStatusRequest, AddCommentRequest,
    CaseCommentResponse
)
from app.api.v1.auth import get_current_user, require_investigator_or_above, require_admin
from app.services.notification import send_reporter_message

router = APIRouter(prefix="/cases", tags=["cases"])
logger = logging.getLogger(__name__)


def decrypt_case(case: Case) -> dict:
    base = {
        "id": str(case.id),
        "external_id": case.external_id,
        "category": case.category,
        "priority": case.priority,
        "status": case.status,
        "title": case.title,
        "is_anonymous": case.is_anonymous,
        "created_at": case.created_at,
        "updated_at": case.updated_at,
        "closed_at": case.closed_at,
        "due_at": case.due_at,
        "assigned_to": str(case.assigned_to) if case.assigned_to else None,
        "attachments_count": len(case.attachments) if case.attachments else 0,
    }
    return base


@router.get("", response_model=dict)
async def list_cases(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[CaseStatus] = None,
    category: Optional[CaseCategory] = None,
    priority: Optional[CasePriority] = None,
    assigned_to: Optional[str] = None,
    search: Optional[str] = None,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    filters = []
    if status:
        filters.append(Case.status == status)
    if category:
        filters.append(Case.category == category)
    if priority:
        filters.append(Case.priority == priority)
    if assigned_to:
        filters.append(Case.assigned_to == uuid.UUID(assigned_to))

    query = select(Case).options(selectinload(Case.attachments))
    if filters:
        query = query.where(and_(*filters))
    query = query.order_by(Case.created_at.desc())

    total_result = await db.execute(select(func.count(Case.id)).where(and_(*filters) if filters else True))
    total = total_result.scalar()

    offset = (page - 1) * per_page
    result = await db.execute(query.offset(offset).limit(per_page))
    cases = result.scalars().all()

    return {
        "items": [decrypt_case(c) for c in cases],
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    # Count by status
    status_counts = {}
    for s in CaseStatus:
        r = await db.execute(select(func.count(Case.id)).where(Case.status == s))
        status_counts[s.value] = r.scalar()

    # Count by category
    cat_counts = {}
    for c in CaseCategory:
        r = await db.execute(select(func.count(Case.id)).where(Case.category == c))
        cat_counts[c.value] = r.scalar()

    # Count by priority
    pri_counts = {}
    for p in CasePriority:
        r = await db.execute(select(func.count(Case.id)).where(Case.priority == p))
        pri_counts[p.value] = r.scalar()

    # Monthly trend (last 6 months)
    from sqlalchemy import extract
    monthly = []
    now = datetime.now(timezone.utc)
    for i in range(5, -1, -1):
        month = (now.month - i - 1) % 12 + 1
        year = now.year - ((now.month - i - 1) // 12)
        r = await db.execute(
            select(func.count(Case.id)).where(
                and_(
                    extract("month", Case.created_at) == month,
                    extract("year", Case.created_at) == year,
                )
            )
        )
        monthly.append({"month": f"{year}-{month:02d}", "count": r.scalar()})

    total = await db.execute(select(func.count(Case.id)))

    return {
        "total": total.scalar(),
        "by_status": status_counts,
        "by_category": cat_counts,
        "by_priority": pri_counts,
        "monthly_trend": monthly,
    }


@router.get("/{case_id}")
async def get_case(
    case_id: str,
    request: Request,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Case)
        .options(
            selectinload(Case.attachments),
            selectinload(Case.comments).selectinload(CaseComment.author),
            selectinload(Case.assignee),
        )
        .where(Case.external_id == case_id)
    )
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Audit log
    db.add(AuditLog(
        user_id=current_user.id,
        case_id=case.id,
        action=AuditAction.CASE_VIEW,
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()

    base = decrypt_case(case)
    base["description"] = decrypt_text(case.description_encrypted)
    base["comments"] = []
    for c in sorted(case.comments, key=lambda x: x.created_at):
        base["comments"].append({
            "id": str(c.id),
            "content": decrypt_text(c.content_encrypted),
            "is_from_reporter": c.is_from_reporter,
            "is_internal": c.is_internal,
            "author": c.author.full_name if c.author else ("Reporter" if c.is_from_reporter else "System"),
            "created_at": c.created_at,
        })
    base["attachments"] = [
        {
            "id": str(a.id),
            "filename": a.original_filename,
            "mime_type": a.mime_type,
            "size_bytes": a.size_bytes,
            "uploaded_at": a.uploaded_at,
        }
        for a in case.attachments
    ]
    if case.assignee:
        base["assignee_name"] = case.assignee.full_name or case.assignee.username

    return base


@router.post("/{case_id}/assign")
async def assign_case(
    case_id: str,
    body: AssignCaseRequest,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Case).where(Case.external_id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    case.assigned_to = uuid.UUID(body.user_id) if body.user_id else None
    db.add(AuditLog(
        user_id=current_user.id,
        case_id=case.id,
        action=AuditAction.CASE_ASSIGN,
        payload={"assigned_to": body.user_id},
    ))
    await db.commit()
    return {"message": "Case assigned"}


@router.post("/{case_id}/status")
async def change_status(
    case_id: str,
    body: ChangeStatusRequest,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Case).where(Case.external_id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    old_status = case.status
    case.status = body.status
    if body.status in (CaseStatus.COMPLETED, CaseStatus.REJECTED):
        case.closed_at = datetime.now(timezone.utc)

    db.add(AuditLog(
        user_id=current_user.id,
        case_id=case.id,
        action=AuditAction.CASE_UPDATE,
        payload={"old_status": old_status, "new_status": body.status},
    ))
    await db.commit()
    return {"message": "Status updated"}


@router.post("/{case_id}/comment")
async def add_comment(
    case_id: str,
    body: AddCommentRequest,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Case).where(Case.external_id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    comment = CaseComment(
        case_id=case.id,
        author_id=current_user.id,
        is_from_reporter=False,
        is_internal=body.is_internal,
        content_encrypted=encrypt_text(body.content),
    )
    db.add(comment)

    # Ichki eslatma bo'lmasa — har doim reporterga Telegram orqali yuboramiz
    # (anonim bo'lsa ham chat_id saqlanadi, shaxsiy ma'lumot emas)
    if not body.is_internal and case.telegram_chat_id:
        try:
            from app.api.v1.telegram import get_bot_app
            bot_app = get_bot_app()
            await send_reporter_message(bot_app.bot, case.telegram_chat_id, case.external_id, body.content)
        except Exception as e:
            logger.warning(f"Could not send Telegram reply for {case.external_id}: {e}")

    db.add(AuditLog(
        user_id=current_user.id,
        case_id=case.id,
        action=AuditAction.CASE_COMMENT,
        payload={"is_internal": body.is_internal},
    ))
    await db.commit()
    return {"message": "Comment added"}
