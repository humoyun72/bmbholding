from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, UploadFile, File, Form
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import logging

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.security import (
    decrypt_text, encrypt_text,
    decrypt_case_content, encrypt_case_content,
    decrypt_comment_content, encrypt_comment_content,
)
from app.models import (
    Case, CaseAttachment, CaseComment, AuditLog, AuditAction, CaseStatus,
    CasePriority, CaseCategory, User, UserRole
)
from app.schemas.cases import (
    CaseResponse, CaseListResponse, CaseDetailResponse,
    AssignCaseRequest, ChangeStatusRequest, AddCommentRequest,
    CaseCommentResponse
)
from app.api.v1.auth import get_current_user, require_investigator_or_above, require_admin
from app.services.notification import send_reporter_message
from app.services.storage import get_file_content, get_download_url, delete_file
from app.core.config import settings

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
        "jira_ticket_id": case.jira_ticket_id,
        "jira_ticket_url": case.jira_ticket_url,
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
    base["description"] = decrypt_case_content(case.description_encrypted)

    # reporter_ip SAQLANMAYDI — anonimlik kafolati (ISO 37001, O'zbekiston shaxsiy ma'lumotlar qonuni)
    # Audit log'dagi IP faqat ADMIN harakatlarini qayd etadi, reporter IP'si emas

    base["comments"] = []
    for c in sorted(case.comments, key=lambda x: x.created_at):
        base["comments"].append({
            "id": str(c.id),
            "content": decrypt_comment_content(c.content_encrypted),
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
    request: Request,
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
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()
    return {"message": "Case assigned"}


@router.post("/{case_id}/status")
async def change_status(
    case_id: str,
    body: ChangeStatusRequest,
    request: Request,
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
        payload={"old_status": old_status.value if hasattr(old_status, 'value') else str(old_status), "new_status": body.status.value if hasattr(body.status, 'value') else str(body.status)},
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()

    # Jira / Redmine tiketini yangilash (agar tiket ID saqlangan bo'lsa)
    jira_ticket_id = getattr(case, "jira_ticket_id", None)
    if jira_ticket_id:
        try:
            from app.services.jira_integration import ticket_service
            await ticket_service.update_ticket_on_case_status_change(
                ticket_id=jira_ticket_id,
                new_status=body.status.value if hasattr(body.status, "value") else str(body.status),
                case_id=case_id,
            )
        except Exception as e:
            logger.warning(f"Tiket yangilashda xato ({case_id}): {e}")

    return {"message": "Status updated"}


@router.post("/{case_id}/comment")
async def add_comment(
    case_id: str,
    body: AddCommentRequest,
    request: Request,
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
        content_encrypted=encrypt_comment_content(body.content),
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
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()
    return {"message": "Comment added"}


@router.get("/{case_id}/attachments/{attachment_id}")
async def download_attachment(
    case_id: str,
    attachment_id: str,
    request: Request,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Case).where(Case.external_id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    att_result = await db.execute(
        select(CaseAttachment).where(
            CaseAttachment.id == uuid.UUID(attachment_id),
            CaseAttachment.case_id == case.id,
        )
    )
    attachment = att_result.scalar_one_or_none()
    if not attachment:
        raise HTTPException(status_code=404, detail="Attachment not found")

    db.add(AuditLog(
        user_id=current_user.id,
        case_id=case.id,
        action=AuditAction.ATTACHMENT_DOWNLOAD,
        payload={"attachment_id": str(attachment.id), "filename": attachment.original_filename},
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()

    if settings.STORAGE_TYPE == "s3":
        presigned_url = await get_download_url(attachment.storage_path, expires_in=300)
        return RedirectResponse(url=presigned_url, status_code=302)

    try:
        content = await get_file_content(attachment.storage_path)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found on disk")

    mime = attachment.mime_type or "application/octet-stream"
    is_viewable = (
        mime.startswith("image/") or
        mime.startswith("video/") or
        mime.startswith("audio/") or
        mime == "application/pdf"
    )
    disposition = "inline" if is_viewable else f'attachment; filename="{attachment.original_filename}"'
    total_size = len(content)

    # Video/Audio uchun Range request (streaming) qo'llab-quvvatlash
    range_header = request.headers.get("range")
    if range_header and (mime.startswith("video/") or mime.startswith("audio/")):
        try:
            range_val = range_header.strip().replace("bytes=", "")
            start_str, end_str = range_val.split("-")
            start = int(start_str)
            end = int(end_str) if end_str else total_size - 1
            end = min(end, total_size - 1)
            chunk = content[start:end + 1]
            return Response(
                content=chunk,
                status_code=206,
                media_type=mime,
                headers={
                    "Content-Range": f"bytes {start}-{end}/{total_size}",
                    "Accept-Ranges": "bytes",
                    "Content-Length": str(len(chunk)),
                    "Content-Disposition": disposition,
                    "Cache-Control": "private, max-age=3600",
                },
            )
        except Exception:
            pass  # Range parse xatosi — oddiy response qaytaramiz

    return Response(
        content=content,
        status_code=200,
        media_type=mime,
        headers={
            "Content-Disposition": disposition,
            "Content-Length": str(total_size),
            "Accept-Ranges": "bytes",
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.post("/{case_id}/send-file")
async def send_file_to_reporter(
    case_id: str,
    request: Request,
    file: UploadFile = File(...),
    caption: str = Form(default=""),
    is_internal: bool = Form(default=False),
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    """Admin reporter ga fayl/rasm/video/audio yuboradi (Telegram orqali)"""
    from app.services.storage import (
        save_uploaded_file, ALLOWED_MIME_TYPES, BLOCKED_EXTENSIONS, MAX_FILE_SIZE_BYTES
    )
    from app.services.notification import send_reporter_file
    from app.services.storage import sanitize_filename
    import os
    import hashlib

    result = await db.execute(select(Case).where(Case.external_id == case_id))
    case = result.scalar_one_or_none()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Fayl validatsiya
    file_data = await file.read()
    if len(file_data) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(400, detail=f"Fayl hajmi {settings.MAX_FILE_SIZE_MB}MB dan oshmasligi kerak")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext in BLOCKED_EXTENSIONS:
        raise HTTPException(400, detail=f"'{ext}' kengaytmali fayllar yuklash taqiqlangan")

    # MIME aniqlash: brauzer noto'g'ri MIME yuborsa — kengaytmadan aniqlaymiz
    import mimetypes
    mime = file.content_type or "application/octet-stream"
    # Brauzer octet-stream yuborsa yoki video/quicktime ni mp4 sifatida yuborsa — kengaytmadan aniqlaymiz
    if mime in ("application/octet-stream", "application/x-www-form-urlencoded"):
        guessed, _ = mimetypes.guess_type(file.filename or "")
        if guessed:
            mime = guessed

    # Video kengaytmalarini qo'shimcha tekshirish (brauzer har xil MIME yuborishi mumkin)
    video_exts = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv"}
    audio_exts = {".mp3", ".wav", ".ogg", ".aac", ".flac", ".m4a", ".opus", ".oga"}
    image_exts = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}

    if ext in video_exts and not mime.startswith("video/"):
        mime = "video/mp4" if ext == ".mp4" else f"video/{ext.lstrip('.')}"
    elif ext in audio_exts and not mime.startswith("audio/"):
        mime = "audio/mpeg" if ext == ".mp3" else f"audio/{ext.lstrip('.')}"
    elif ext in image_exts and not mime.startswith("image/"):
        mime = f"image/{'jpeg' if ext in ('.jpg', '.jpeg') else ext.lstrip('.')}"

    # Hali ham ruxsat etilmagan MIME bo'lsa — rad etamiz (lekin video/audio/image uchun o'tkazamiz)
    if (mime not in ALLOWED_MIME_TYPES and
            not mime.startswith("video/") and
            not mime.startswith("audio/") and
            not mime.startswith("image/")):
        raise HTTPException(400, detail=f"Bu fayl turi ruxsat etilmagan: {mime}")

    # Faylni storage ga saqlash
    safe_filename = file.filename or f"file_{uuid.uuid4().hex[:8]}"
    storage_path = await save_uploaded_file(
        file_data=file_data,
        original_filename=safe_filename,
        mime_type=mime,
        case_id=str(case.id),
    )

    # DB ga attachment saqlaymiz
    safe_name = sanitize_filename(safe_filename)
    checksum = hashlib.sha256(file_data).hexdigest()
    attachment = CaseAttachment(
        case_id=case.id,
        storage_path=storage_path,
        filename=safe_name,
        original_filename=safe_filename,
        mime_type=mime,
        size_bytes=len(file_data),
        checksum=checksum,
    )
    db.add(attachment)
    await db.flush()  # attachment.id ni olish uchun

    # Comment yozamiz (chat ichida fayl ko'rinsin)
    comment_text = f"📎 Fayl yuborildi: {safe_filename}"
    if caption:
        comment_text += f"\n{caption}"
    comment = CaseComment(
        case_id=case.id,
        author_id=current_user.id,
        is_from_reporter=False,
        is_internal=is_internal,
        content_encrypted=encrypt_comment_content(comment_text),
    )
    db.add(comment)

    # Ichki eslatma bo'lmasa — reporter ga Telegram orqali fayl yuboramiz
    tg_sent = False
    if not is_internal and case.telegram_chat_id:
        try:
            from app.api.v1.telegram import get_bot_app
            bot_app = get_bot_app()
            await send_reporter_file(
                bot=bot_app.bot,
                telegram_chat_id=case.telegram_chat_id,
                case_id=case.external_id,
                file_data=file_data,
                filename=safe_filename,
                mime_type=mime,
                caption=caption,
            )
            tg_sent = True
        except Exception as e:
            logger.warning(f"Telegram file send failed for {case_id}: {e}")

    db.add(AuditLog(
        user_id=current_user.id,
        case_id=case.id,
        action=AuditAction.CASE_COMMENT,
        payload={
            "action": "admin_sent_file",
            "filename": safe_filename,
            "mime_type": mime,
            "is_internal": is_internal,
            "telegram_sent": tg_sent,
        },
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()

    return {
        "message": "Fayl yuborildi",
        "attachment_id": str(attachment.id),
        "telegram_sent": tg_sent,
        "filename": safe_filename,
    }


