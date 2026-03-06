"""
Kunlik va haftalik hisobot funksiyalari.
APScheduler yoki to'g'ridan-to'g'ri chaqiriladi.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from telegram import Bot
from telegram.constants import ParseMode

from app.core.config import settings
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)

# O'zbekiston vaqti = UTC + 5
UZT_OFFSET = timedelta(hours=5)

CAT_LABELS = {
    "corruption":          "Korrupsiya / Pora",
    "conflict_of_interest":"Manfaatlar to'qnashuvi",
    "fraud":               "Firibgarlik",
    "safety":              "Xavfsizlik buzilishi",
    "discrimination":      "Kamsitish",
    "procurement":         "Tender buzilishi",
    "other":               "Boshqa",
}


def _get_bot() -> Optional[Bot]:
    """Telegram Bot ob'ektini qaytaradi."""
    try:
        from app.api.v1.telegram import get_bot_app
        return get_bot_app().bot
    except Exception as e:
        logger.warning(f"Bot olishda xato: {e}")
        return None


def _admin_chat_id() -> Optional[int]:
    cid = settings.ADMIN_CHAT_ID
    if not cid:
        logger.warning("ADMIN_CHAT_ID sozlanmagan — hisobot yuborilmaydi")
        return None
    return cid


async def _write_audit(detail: str):
    """Hisobot yuborilganini audit log ga yozadi."""
    try:
        from sqlalchemy import select
        from app.models import AuditLog, AuditAction

        async with AsyncSessionLocal() as db:
            db.add(AuditLog(
                action=AuditAction.REPORT_SENT,
                entity_type="report",
                entity_id="scheduled",
                payload={"detail": detail},
            ))
            await db.commit()
    except Exception as e:
        logger.warning(f"Audit log yozishda xato: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# KUNLIK HISOBOT
# ─────────────────────────────────────────────────────────────────────────────

async def send_daily_report(context=None):
    """
    Kunlik statistika hisobotini ADMIN_CHAT_ID ga yuboradi.
    APScheduler context yoki to'g'ridan-to'g'ri chaqiriladi.
    """
    chat_id = _admin_chat_id()
    if not chat_id:
        return

    bot: Optional[Bot] = None
    if context is not None:
        bot = context.bot
    else:
        bot = _get_bot()

    if bot is None:
        logger.error("Hisobot uchun bot ob'ekti topilmadi")
        return

    try:
        stats = await _collect_daily_stats()
    except Exception as e:
        logger.error(f"Kunlik statistika yig'ishda xato: {e}", exc_info=True)
        return

    now_uzt = datetime.now(timezone.utc) + UZT_OFFSET
    date_str = now_uzt.strftime("%d.%m.%Y")

    overdue_warn = "🚨 *DIQQAT!* Muddati o'tgan murojaatlar mavjud!\n\n" if stats["overdue"] > 0 else ""

    # Muddati o'tgan murojaatlar batafsil ro'yxati
    overdue_detail = ""
    if stats.get("overdue_list"):
        overdue_detail = "\n🚨 *Muddati o'tgan murojaatlar:*\n"
        shown = stats["overdue_list"][:5]
        for item in shown:
            overdue_detail += f"  • `{item['case_id']}` — {item['days_overdue']} kun — {item['assignee']}\n"
        remaining = stats["overdue"] - len(shown)
        if remaining > 0:
            overdue_detail += f"  _+{remaining} ta ko'proq_\n"

    text = (
        f"{overdue_warn}"
        f"📊 *Kunlik Hisobot — {date_str}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📥 Yangi:               *{stats['new']}*\n"
        f"🔄 Ko'rib chiqilmoqda:  *{stats['in_progress']}*\n"
        f"❓ Ma'lumot kutilmoqda: *{stats['needs_info']}*\n"
        f"✅ Hal qilindi (bugun): *{stats['completed_today']}*\n"
        f"❌ Rad etildi (bugun):  *{stats['rejected_today']}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏰ Deadline yaqin:      *{stats['deadline_near']}*\n"
        f"🚨 Muddati o'tgan:      *{stats['overdue']}*\n"
        f"{overdue_detail}"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 Batafsil: {_admin_url()}"
    )

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )
        logger.info(f"Kunlik hisobot yuborildi → chat_id={chat_id}")
        await _write_audit(f"Kunlik hisobot {date_str} yuborildi")
    except Exception as e:
        logger.error(f"Kunlik hisobot yuborishda xato: {e}", exc_info=True)


async def _collect_daily_stats() -> dict:
    """DB dan kunlik statistika yig'adi — 4 ta query."""
    from sqlalchemy import select, func, and_
    from sqlalchemy.orm import selectinload
    from app.models import Case, CaseStatus

    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    deadline_threshold = now + timedelta(hours=24)

    async with AsyncSessionLocal() as db:
        # 1. Holat bo'yicha aktiv murojaatlar (GROUP BY)
        status_rows = await db.execute(
            select(Case.status, func.count(Case.id))
            .where(Case.status.notin_([CaseStatus.ARCHIVED]))
            .group_by(Case.status)
        )
        by_status = {row[0].value: row[1] for row in status_rows}

        # 2. Bugun hal qilingan / rad etilgan (closed_at yoki updated_at bugun)
        completed_today = await db.scalar(
            select(func.count(Case.id)).where(
                and_(Case.status == CaseStatus.COMPLETED,
                     Case.updated_at >= today_start,
                     Case.updated_at < tomorrow_start)
            )
        ) or 0

        rejected_today = await db.scalar(
            select(func.count(Case.id)).where(
                and_(Case.status == CaseStatus.REJECTED,
                     Case.updated_at >= today_start,
                     Case.updated_at < tomorrow_start)
            )
        ) or 0

        # 3. Deadline yaqin (24 soat ichida, hali yopilmagan)
        deadline_near = await db.scalar(
            select(func.count(Case.id)).where(
                and_(
                    Case.due_at.isnot(None),
                    Case.due_at <= deadline_threshold,
                    Case.due_at > now,
                    Case.status.notin_([
                        CaseStatus.COMPLETED, CaseStatus.REJECTED, CaseStatus.ARCHIVED
                    ])
                )
            )
        ) or 0

        # 4. Muddati o'tgan (due_at o'tib ketgan, hali ochiq)
        overdue = await db.scalar(
            select(func.count(Case.id)).where(
                and_(
                    Case.due_at.isnot(None),
                    Case.due_at < now,
                    Case.status.notin_([
                        CaseStatus.COMPLETED, CaseStatus.REJECTED, CaseStatus.ARCHIVED
                    ])
                )
            )
        ) or 0

        # 5. Muddati o'tgan murojaatlar batafsil ro'yxati (top 5 + assignee)
        overdue_rows = await db.execute(
            select(Case)
            .options(selectinload(Case.assignee))
            .where(
                and_(
                    Case.due_at.isnot(None),
                    Case.due_at < now,
                    Case.status.notin_([
                        CaseStatus.COMPLETED, CaseStatus.REJECTED, CaseStatus.ARCHIVED
                    ])
                )
            )
            .order_by(Case.due_at.asc())
            .limit(10)
        )
        overdue_list = []
        for case in overdue_rows.scalars():
            days_overdue = (now - case.due_at).days
            assignee_name = "Tayinlanmagan"
            if case.assignee:
                assignee_name = case.assignee.full_name or case.assignee.username
            overdue_list.append({
                "case_id": case.external_id,
                "days_overdue": days_overdue,
                "assignee": assignee_name,
            })

    return {
        "new":             by_status.get("new", 0),
        "in_progress":     by_status.get("in_progress", 0),
        "needs_info":      by_status.get("needs_info", 0),
        "completed_today": completed_today,
        "rejected_today":  rejected_today,
        "deadline_near":   deadline_near,
        "overdue":         overdue,
        "overdue_list":    overdue_list,
    }


# ─────────────────────────────────────────────────────────────────────────────
# DEADLINE ESLATMALAR
# ─────────────────────────────────────────────────────────────────────────────

async def send_deadline_reminders(context=None):
    """
    Deadline yaqinlashgan va muddati o'tgan murojaatlar haqida eslatma yuboradi.
    Har 4 soatda bir marta chaqiriladi (SystemSettings dan o'qiladi).
    Dublikat oldini olish: Notification jadvalida notification_type orqali tekshiriladi.
    """
    bot: Optional[Bot] = None
    if context is not None:
        bot = context.bot
    else:
        bot = _get_bot()

    if bot is None:
        logger.warning("Deadline reminder uchun bot topilmadi")
        return

    chat_id = _admin_chat_id()

    from sqlalchemy import select, and_
    from sqlalchemy.orm import selectinload
    from app.models import Case, CaseStatus, Notification, NotificationType, User

    now = datetime.now(timezone.utc)
    deadline_threshold = now + timedelta(hours=24)

    sent_count = 0

    async with AsyncSessionLocal() as db:
        # ── 1. 24 soatdan kamroq qolgan, ochiq murojaatlar ──────────────
        near_result = await db.execute(
            select(Case)
            .options(selectinload(Case.assignee))
            .where(
                and_(
                    Case.due_at.isnot(None),
                    Case.due_at <= deadline_threshold,
                    Case.due_at > now,
                    Case.status.notin_([
                        CaseStatus.COMPLETED, CaseStatus.REJECTED, CaseStatus.ARCHIVED
                    ])
                )
            )
        )
        near_cases = near_result.scalars().all()

        for case in near_cases:
            notif_type = "deadline_warning"

            # Dublikat tekshirish
            existing = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.case_id == case.id,
                        Notification.notification_type == notif_type,
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue  # allaqachon yuborilgan

            # Assignee ga xabar yuborish
            if case.assignee and case.assignee.telegram_chat_id:
                cat_label = CAT_LABELS.get(
                    case.category.value if hasattr(case.category, "value") else str(case.category),
                    "Boshqa"
                )
                due_str = case.due_at.strftime("%d.%m.%Y %H:%M")
                text = (
                    f"⏰ *Deadline yaqinlashmoqda!*\n"
                    f"📋 `{case.external_id}`\n"
                    f"📂 {cat_label}\n"
                    f"Deadline: {due_str} (24 soat qoldi)"
                )
                try:
                    await bot.send_message(
                        chat_id=case.assignee.telegram_chat_id,
                        text=text,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"Deadline reminder yuborishda xato (case={case.external_id}): {e}")

            # Notification jadvaliga yozish (dublikat oldini olish)
            db.add(Notification(
                case_id=case.id,
                type=NotificationType.TELEGRAM,
                notification_type=notif_type,
                sent_to=str(case.assignee.telegram_chat_id) if case.assignee and case.assignee.telegram_chat_id else "none",
            ))

        # ── 2. Muddati o'tgan, ochiq murojaatlar ────────────────────────
        overdue_result = await db.execute(
            select(Case)
            .options(selectinload(Case.assignee))
            .where(
                and_(
                    Case.due_at.isnot(None),
                    Case.due_at < now,
                    Case.status.notin_([
                        CaseStatus.COMPLETED, CaseStatus.REJECTED, CaseStatus.ARCHIVED
                    ])
                )
            )
        )
        overdue_cases = overdue_result.scalars().all()

        for case in overdue_cases:
            notif_type = "overdue_alert"

            # Dublikat tekshirish
            existing = await db.execute(
                select(Notification).where(
                    and_(
                        Notification.case_id == case.id,
                        Notification.notification_type == notif_type,
                    )
                )
            )
            if existing.scalar_one_or_none():
                continue  # allaqachon yuborilgan

            days_overdue = (now - case.due_at).days
            assignee_name = "Tayinlanmagan"
            due_str = case.due_at.strftime("%d.%m.%Y %H:%M")

            if case.assignee:
                assignee_name = case.assignee.full_name or case.assignee.username

            text = (
                f"🚨 *MUROJAAT MUDDATI O'TDI!*\n"
                f"📋 `{case.external_id}`\n"
                f"Muddat: {due_str} ({days_overdue} kun o'tdi)\n"
                f"Tayinlangan: {assignee_name}"
            )

            # Assignee ga xabar
            if case.assignee and case.assignee.telegram_chat_id:
                try:
                    await bot.send_message(
                        chat_id=case.assignee.telegram_chat_id,
                        text=text,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                    sent_count += 1
                except Exception as e:
                    logger.warning(f"Overdue alert yuborishda xato (case={case.external_id}): {e}")

            # Admin guruhga ham xabar
            if chat_id:
                try:
                    await bot.send_message(
                        chat_id=chat_id,
                        text=text,
                        parse_mode=ParseMode.MARKDOWN,
                    )
                except Exception as e:
                    logger.warning(f"Overdue admin alert xato: {e}")

            # Notification jadvaliga yozish
            db.add(Notification(
                case_id=case.id,
                type=NotificationType.TELEGRAM,
                notification_type=notif_type,
                sent_to=str(case.assignee.telegram_chat_id) if case.assignee and case.assignee.telegram_chat_id else "admin",
            ))

        await db.commit()

    logger.info(f"Deadline reminders: {sent_count} ta xabar yuborildi")
    return sent_count


# ─────────────────────────────────────────────────────────────────────────────
# HAFTALIK HISOBOT
# ─────────────────────────────────────────────────────────────────────────────

async def send_weekly_report(context=None):
    """
    Haftalik tahlil hisobotini ADMIN_CHAT_ID ga yuboradi.
    """
    chat_id = _admin_chat_id()
    if not chat_id:
        return

    bot: Optional[Bot] = None
    if context is not None:
        bot = context.bot
    else:
        bot = _get_bot()

    if bot is None:
        logger.error("Haftalik hisobot uchun bot topilmadi")
        return

    try:
        stats = await _collect_weekly_stats()
    except Exception as e:
        logger.error(f"Haftalik statistika yig'ishda xato: {e}", exc_info=True)
        return

    now_uzt = datetime.now(timezone.utc) + UZT_OFFSET
    # Joriy haftaning dushanba-yakshanba
    monday = now_uzt - timedelta(days=now_uzt.weekday())
    sunday = monday + timedelta(days=6)
    week_str = f"{monday.strftime('%d.%m')}–{sunday.strftime('%d.%m.%Y')}"

    # O'tgan hafta bilan taqqoslash
    diff = stats["this_week"] - stats["last_week"]
    if diff > 0:
        trend = f"+{diff} ↑"
    elif diff < 0:
        trend = f"{diff} ↓"
    else:
        trend = "0 →"

    # Top-3 kategoriya
    top3_lines = ""
    for i, (cat, cnt, pct) in enumerate(stats["top_categories"][:3], 1):
        label = CAT_LABELS.get(cat, cat)
        top3_lines += f"  {i}. {label}: {cnt} ta ({pct}%)\n"
    if not top3_lines:
        top3_lines = "  Ma'lumot yo'q\n"

    # O'rtacha ko'rib chiqish vaqti
    avg_hours = stats.get("avg_resolution_hours")
    avg_str = f"{avg_hours:.1f} soat" if avg_hours is not None else "—"

    # Hal qilinganlik darajasi
    resolution = stats.get("resolution_rate", 0)

    text = (
        f"📈 *Haftalik Hisobot — {week_str}*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📥 Bu hafta kelgan:    *{stats['this_week']}* ta ({trend})\n"
        f"✅ Hal qilindi:        *{stats['resolved']}* ta\n"
        f"❌ Rad etildi:         *{stats['rejected']}* ta\n"
        f"🔄 Hali ochiq:         *{stats['still_open']}* ta\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Top-3 kategoriya (bu hafta):*\n"
        f"{top3_lines}"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ O'rtacha ko'rib chiqish: *{avg_str}*\n"
        f"✔️ Hal qilinganlik:         *{resolution}%*\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📋 Batafsil: {_admin_url()}"
    )

    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
        )
        logger.info(f"Haftalik hisobot yuborildi → chat_id={chat_id}")
        await _write_audit(f"Haftalik hisobot {week_str} yuborildi")
    except Exception as e:
        logger.error(f"Haftalik hisobot yuborishda xato: {e}", exc_info=True)


async def _collect_weekly_stats() -> dict:
    """DB dan haftalik statistika yig'adi."""
    from sqlalchemy import select, func, and_
    from app.models import Case, CaseStatus

    now = datetime.now(timezone.utc)
    # Joriy haftaning boshi (dushanba 00:00 UTC)
    this_monday = (now - timedelta(days=now.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    last_monday = this_monday - timedelta(weeks=1)

    async with AsyncSessionLocal() as db:
        # Bu hafta kelgan
        this_week = await db.scalar(
            select(func.count(Case.id)).where(
                and_(Case.created_at >= this_monday, Case.created_at <= now)
            )
        ) or 0

        # O'tgan hafta kelgan
        last_week = await db.scalar(
            select(func.count(Case.id)).where(
                and_(Case.created_at >= last_monday, Case.created_at < this_monday)
            )
        ) or 0

        # Bu hafta hal qilingan / rad etilgan
        resolved = await db.scalar(
            select(func.count(Case.id)).where(
                and_(Case.status == CaseStatus.COMPLETED,
                     Case.updated_at >= this_monday, Case.updated_at <= now)
            )
        ) or 0

        rejected = await db.scalar(
            select(func.count(Case.id)).where(
                and_(Case.status == CaseStatus.REJECTED,
                     Case.updated_at >= this_monday, Case.updated_at <= now)
            )
        ) or 0

        # Hali ochiq (new + in_progress + needs_info)
        still_open = await db.scalar(
            select(func.count(Case.id)).where(
                Case.status.in_([
                    CaseStatus.NEW, CaseStatus.IN_PROGRESS, CaseStatus.NEEDS_INFO
                ])
            )
        ) or 0

        # Top kategoriyalar (bu hafta)
        cat_rows = await db.execute(
            select(Case.category, func.count(Case.id).label("cnt"))
            .where(and_(Case.created_at >= this_monday, Case.created_at <= now))
            .group_by(Case.category)
            .order_by(func.count(Case.id).desc())
            .limit(3)
        )
        cat_list = [(r[0].value if hasattr(r[0], "value") else str(r[0]), r[1])
                    for r in cat_rows]
        total_week = sum(c for _, c in cat_list) or 1
        top_categories = [
            (cat, cnt, round(cnt / total_week * 100))
            for cat, cnt in cat_list
        ]

        # O'rtacha ko'rib chiqish vaqti (completed cases, bu hafta)
        # closed_at - created_at (soatda)
        avg_result = await db.execute(
            select(
                func.avg(
                    func.extract("epoch", Case.closed_at) -
                    func.extract("epoch", Case.created_at)
                )
            ).where(
                and_(
                    Case.status == CaseStatus.COMPLETED,
                    Case.closed_at.isnot(None),
                    Case.updated_at >= this_monday,
                    Case.updated_at <= now,
                )
            )
        )
        avg_seconds = avg_result.scalar()
        avg_resolution_hours = round(avg_seconds / 3600, 1) if avg_seconds else None

        # Hal qilinganlik darajasi
        denominator = resolved + rejected + still_open
        resolution_rate = round(resolved / denominator * 100) if denominator else 0

    return {
        "this_week":            this_week,
        "last_week":            last_week,
        "resolved":             resolved,
        "rejected":             rejected,
        "still_open":           still_open,
        "top_categories":       top_categories,
        "avg_resolution_hours": avg_resolution_hours,
        "resolution_rate":      resolution_rate,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _admin_url() -> str:
    """Frontend admin panel URL ni qaytaradi."""
    base = getattr(settings, "FRONTEND_URL", None) or "http://localhost:5173"
    return f"{base}/cases"

