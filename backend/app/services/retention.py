"""
Data Retention Service — Eskirgan ma'lumotlarni avtomatik arxivlash va o'chirish.

Qoidalar:
- Yopilgan murojaatlar (completed/rejected)  → 3 yildan keyin ARCHIVED ga o'tkaziladi
- Arxivlangan murojaatlar                    → 5 yildan keyin to'liq o'chiriladi
- Audit loglari                              → 3 yildan keyin o'chiriladi (GDPR/compliance)
- Bildirishnomalar                           → 1 yildan keyin o'chiriladi

Ishlatish:
  - main.py lifespan'da APScheduler orqali har kech 02:00 da ishga tushadi
  - Qo'lda: POST /api/v1/admin/retention/run (faqat admin)
"""
import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, and_, func

from app.models import Case, CaseStatus, AuditLog, Notification
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# ── Retention muddatlari ──────────────────────────────────────────────────────
COMPLETED_TO_ARCHIVED_DAYS = 3 * 365   # 3 yil → ARCHIVED
ARCHIVED_DELETE_DAYS       = 5 * 365   # 5 yil → o'chirish
AUDIT_LOG_DELETE_DAYS      = 3 * 365   # 3 yil → audit log o'chirish
NOTIFICATION_DELETE_DAYS   = 365       # 1 yil → notification o'chirish


async def run_retention(db: AsyncSession | None = None) -> dict:
    """
    Data retention qoidalarini bajaradi.
    db=None bo'lsa — yangi session yaratadi.
    Natija: har bir amal nechta yozuvga ta'sir qilgani.
    """
    own_session = db is None
    if own_session:
        db = AsyncSessionLocal()

    stats = {
        "archived": 0,
        "deleted_cases": 0,
        "deleted_audit_logs": 0,
        "deleted_notifications": 0,
        "errors": [],
    }

    try:
        now = datetime.now(timezone.utc)

        # ── 1. Yopilgan murojaatlarni ARCHIVED ga o'tkazish ──────────────
        archived_cutoff = now - timedelta(days=COMPLETED_TO_ARCHIVED_DAYS)
        result = await db.execute(
            update(Case)
            .where(
                and_(
                    Case.status.in_([CaseStatus.COMPLETED, CaseStatus.REJECTED]),
                    Case.closed_at <= archived_cutoff,
                )
            )
            .values(status=CaseStatus.ARCHIVED, updated_at=now)
        )
        stats["archived"] = result.rowcount
        if stats["archived"]:
            logger.info(f"Retention: {stats['archived']} ta murojaat ARCHIVED ga o'tkazildi")

        # ── 2. Arxivlangan eski murojaatlarni to'liq o'chirish ────────────
        delete_cutoff = now - timedelta(days=ARCHIVED_DELETE_DAYS)
        # Avval bog'liq audit loglarni o'chirish
        old_cases_q = await db.execute(
            select(Case.id).where(
                and_(
                    Case.status == CaseStatus.ARCHIVED,
                    Case.updated_at <= delete_cutoff,
                )
            )
        )
        old_case_ids = [row[0] for row in old_cases_q.fetchall()]

        if old_case_ids:
            await db.execute(
                delete(AuditLog).where(AuditLog.case_id.in_(old_case_ids))
            )
            await db.execute(
                delete(Notification).where(Notification.case_id.in_(old_case_ids))
            )
            del_result = await db.execute(
                delete(Case).where(Case.id.in_(old_case_ids))
            )
            stats["deleted_cases"] = del_result.rowcount
            logger.warning(
                f"Retention: {stats['deleted_cases']} ta eski arxivlangan murojaat o'chirildi "
                f"({ARCHIVED_DELETE_DAYS // 365} yildan eski)"
            )

        # ── 3. Eski audit loglarni o'chirish ──────────────────────────────
        audit_cutoff = now - timedelta(days=AUDIT_LOG_DELETE_DAYS)
        audit_del = await db.execute(
            delete(AuditLog).where(
                and_(
                    AuditLog.case_id.is_(None),   # Case bilan bog'liq bo'lmaganlar
                    AuditLog.created_at <= audit_cutoff,
                )
            )
        )
        stats["deleted_audit_logs"] = audit_del.rowcount
        if stats["deleted_audit_logs"]:
            logger.info(f"Retention: {stats['deleted_audit_logs']} ta eski audit log o'chirildi")

        # ── 4. Eski bildirishnomalarni o'chirish ──────────────────────────
        notif_cutoff = now - timedelta(days=NOTIFICATION_DELETE_DAYS)
        notif_del = await db.execute(
            delete(Notification).where(Notification.sent_at <= notif_cutoff)
        )
        stats["deleted_notifications"] = notif_del.rowcount
        if stats["deleted_notifications"]:
            logger.info(f"Retention: {stats['deleted_notifications']} ta eski bildirishnoma o'chirildi")

        await db.commit()
        logger.info(f"Data retention muvaffaqiyatli yakunlandi: {stats}")

    except Exception as e:
        await db.rollback()
        stats["errors"].append(str(e))
        logger.error(f"Data retention xato: {e}", exc_info=True)
    finally:
        if own_session:
            await db.close()

    return stats


async def get_retention_stats(db: AsyncSession) -> dict:
    """
    Retention statistikasini qaytaradi — nechta yozuv muddati yaqinlashmoqda.
    Admin dashboard uchun.
    """
    now = datetime.now(timezone.utc)
    archive_soon_cutoff = now - timedelta(days=COMPLETED_TO_ARCHIVED_DAYS - 30)  # 30 kun qolgan
    archive_cutoff      = now - timedelta(days=COMPLETED_TO_ARCHIVED_DAYS)
    delete_cutoff       = now - timedelta(days=ARCHIVED_DELETE_DAYS)

    # Yaqin orada arxivlanishi kerak bo'lgan murojaatlar
    soon_archive_q = await db.execute(
        select(func.count(Case.id)).where(
            and_(
                Case.status.in_([CaseStatus.COMPLETED, CaseStatus.REJECTED]),
                Case.closed_at.between(archive_soon_cutoff, archive_cutoff),
            )
        )
    )
    # Arxivlanishi kerak bo'lgan murojaatlar (muddati o'tgan)
    overdue_archive_q = await db.execute(
        select(func.count(Case.id)).where(
            and_(
                Case.status.in_([CaseStatus.COMPLETED, CaseStatus.REJECTED]),
                Case.closed_at <= archive_cutoff,
            )
        )
    )
    # O'chirilishi kerak bo'lgan arxivlangan murojaatlar
    overdue_delete_q = await db.execute(
        select(func.count(Case.id)).where(
            and_(
                Case.status == CaseStatus.ARCHIVED,
                Case.updated_at <= delete_cutoff,
            )
        )
    )

    return {
        "archive_soon_count": soon_archive_q.scalar() or 0,
        "overdue_archive_count": overdue_archive_q.scalar() or 0,
        "overdue_delete_count": overdue_delete_q.scalar() or 0,
        "policy": {
            "completed_to_archived_days": COMPLETED_TO_ARCHIVED_DAYS,
            "archived_delete_days": ARCHIVED_DELETE_DAYS,
            "audit_log_delete_days": AUDIT_LOG_DELETE_DAYS,
            "notification_delete_days": NOTIFICATION_DELETE_DAYS,
        },
    }

