import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Message
from telegram.constants import ParseMode
from telegram.error import BadRequest
from app.core.config import settings
from app.models import CaseCategory, CaseStatus, CasePriority

logger = logging.getLogger(__name__)

# ─── Status holat mashinasi (handlers.py bilan sinxronlash uchun) ─────────────
ALLOWED_TRANSITIONS: dict[CaseStatus, list[CaseStatus]] = {
    CaseStatus.NEW:         [CaseStatus.IN_PROGRESS, CaseStatus.REJECTED, CaseStatus.NEEDS_INFO],
    CaseStatus.IN_PROGRESS: [CaseStatus.COMPLETED, CaseStatus.REJECTED, CaseStatus.NEEDS_INFO],
    CaseStatus.NEEDS_INFO:  [CaseStatus.IN_PROGRESS, CaseStatus.REJECTED],
    CaseStatus.COMPLETED:   [],
    CaseStatus.REJECTED:    [],
    CaseStatus.ARCHIVED:    [],
}

STATUS_LABELS = {
    CaseStatus.NEW: "🆕 Yangi",
    CaseStatus.IN_PROGRESS: "🔄 Ko'rib chiqilmoqda",
    CaseStatus.NEEDS_INFO: "❓ Ma'lumot kerak",
    CaseStatus.COMPLETED: "✅ Yakunlandi",
    CaseStatus.REJECTED: "❌ Rad etildi",
    CaseStatus.ARCHIVED: "📦 Arxivlandi",
}

CATEGORY_LABELS = {
    CaseCategory.CORRUPTION: "🔴 Korrupsiya / Pora",
    CaseCategory.CONFLICT_OF_INTEREST: "⚖️ Manfaatlar to'qnashuvi",
    CaseCategory.FRAUD: "💸 Firibgarlik / O'g'irlik",
    CaseCategory.SAFETY: "⚠️ Xavfsizlik buzilishi",
    CaseCategory.DISCRIMINATION: "🚫 Kamsitish / Bezovtalik",
    CaseCategory.PROCUREMENT: "📋 Tender buzilishi",
    CaseCategory.OTHER: "❓ Boshqa",
}


PRIORITY_LABELS = {
    "critical": "🔴 Kritik",
    "high":     "🟠 Yuqori",
    "medium":   "🟡 O'rta",
    "low":      "🟢 Past",
}


def build_status_keyboard(case_external_id: str, current_status: CaseStatus) -> InlineKeyboardMarkup:
    """
    Hozirgi status va ALLOWED_TRANSITIONS ga qarab inline keyboard yaratadi.
    """
    allowed_statuses = ALLOWED_TRANSITIONS.get(current_status, [])

    # Status → tugma label va callback
    status_buttons = {
        CaseStatus.IN_PROGRESS: ("▶️ Boshlash", f"status_{case_external_id}_in_progress"),
        CaseStatus.NEEDS_INFO: ("❓ Ma'lumot so'rash", f"status_{case_external_id}_needs_info"),
        CaseStatus.COMPLETED: ("✅ Yakunlash", f"status_{case_external_id}_completed"),
        CaseStatus.REJECTED: ("❌ Rad etish", f"status_{case_external_id}_rejected"),
        CaseStatus.NEW: ("🔄 Qayta ochish", f"status_{case_external_id}_new"),
    }

    buttons = []
    row = []
    for status in allowed_statuses:
        if status in status_buttons:
            label, callback = status_buttons[status]
            row.append(InlineKeyboardButton(label, callback_data=callback))
            if len(row) == 2:
                buttons.append(row)
                row = []
    if row:
        buttons.append(row)

    # Har doim admin panel va tayinlash tugmalari
    buttons.append([
        InlineKeyboardButton("👤 Tayinlash", callback_data=f"assign_{case_external_id}"),
        InlineKeyboardButton("🔍 Admin panelda ko'r", callback_data=f"view_{case_external_id}"),
    ])

    return InlineKeyboardMarkup(buttons)


def format_group_message(case) -> str:
    """
    Guruh uchun murojaat xabarini formatlash.

    Args:
        case: Case modeli (id, external_id, category, priority, status, assigned_to,
              created_at, due_at, assignee attributelari)

    Returns:
        Formatlangan Markdown xabar matni
    """
    cat_label = CATEGORY_LABELS.get(case.category, str(case.category.value if hasattr(case.category, "value") else case.category))
    pri_label = PRIORITY_LABELS.get(
        case.priority.value if hasattr(case.priority, "value") else str(case.priority),
        str(case.priority)
    )
    status_label = STATUS_LABELS.get(case.status, str(case.status.value if hasattr(case.status, "value") else case.status))

    # Asosiy ma'lumotlar
    text = (
        f"📋 *Murojaat: `{case.external_id}`*\n\n"
        f"📂 *Kategoriya:* {cat_label}\n"
        f"⚠️ *Ustuvorlik:* {pri_label}\n"
        f"📊 *Holat:* {status_label}\n"
    )

    # Tayinlangan ijrochi (agar bo'lsa)
    if case.assignee:
        assignee_name = case.assignee.full_name or case.assignee.username
        text += f"👤 *Ijrochi:* {assignee_name}\n"
    elif case.assigned_to:
        text += f"👤 *Ijrochi:* _Tayinlangan (ID: {str(case.assigned_to)[:8]}...)_\n"
    else:
        text += f"👤 *Ijrochi:* _Tayinlanmagan_\n"

    # Sanalar
    created_str = case.created_at.strftime("%d.%m.%Y %H:%M") if case.created_at else "—"
    text += f"📅 *Yaratilgan:* {created_str}\n"

    if case.due_at:
        due_str = case.due_at.strftime("%d.%m.%Y")
        text += f"⏰ *Deadline:* {due_str}\n"

    text += f"\n👉 [Admin panelda ko'ring]({settings.WEBHOOK_URL.replace('/api/telegram/webhook', '')}/admin/cases/{case.external_id})"

    return text


async def update_group_message(bot: Bot, case, chat_id: int = None) -> "Message | None":
    """
    Guruh xabarini yangi holat bilan tahrirlash.
    Agar xabar ID DB da yo'q bo'lsa — yangi xabar yuboriladi.

    Args:
        bot: Telegram Bot instance
        case: Case modeli (group_message_id, external_id, ...)
        chat_id: Admin guruh ID (default: settings.ADMIN_CHAT_ID)

    Returns:
        Message object yoki None
    """
    if chat_id is None:
        chat_id = settings.ADMIN_CHAT_ID

    text = format_group_message(case)
    keyboard = build_status_keyboard(case.external_id, case.status)

    message_id = getattr(case, "group_message_id", None)

    if message_id:
        # Mavjud xabarni tahrirlash
        try:
            edited = await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard,
            )
            return edited
        except BadRequest as e:
            error_msg = str(e).lower()
            if "message is not modified" in error_msg:
                # Xabar o'zgartirilmagan — xato emas
                logger.debug(f"Message not modified for case {case.external_id}")
                return None
            elif "message to edit not found" in error_msg:
                # Xabar o'chirilgan — yangi yuborish
                logger.warning(f"Message not found for case {case.external_id}, sending new")
            else:
                logger.error(f"update_group_message edit failed: {e}")
                return None
        except Exception as e:
            logger.error(f"update_group_message edit failed: {e}")
            return None

    # Yangi xabar yuborish
    try:
        sent = await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
        return sent
    except Exception as e:
        logger.error(f"update_group_message send failed: {e}")
        return None


async def notify_assignee(
    bot: Bot,
    case_id: str,
    category,
    priority,
    due_date: str,
    assignee_telegram_id: int,
):
    """Tayinlangan ijrochiga Telegram orqali xabarnoma yuborish"""
    cat_label = CATEGORY_LABELS.get(category, str(category))
    pri_label = PRIORITY_LABELS.get(
        priority.value if hasattr(priority, "value") else str(priority),
        str(priority)
    )
    message = (
        f"📋 *Sizga yangi murojaat tayinlandi!*\n\n"
        f"🔖 *Raqam:* `{case_id}`\n"
        f"📂 *Kategoriya:* {cat_label}\n"
        f"⚠️ *Ustuvorlik:* {pri_label}\n"
        f"⏰ *Deadline:* {due_date}\n\n"
        f"👉 Admin panelda ko'ring"
    )
    try:
        await bot.send_message(
            chat_id=assignee_telegram_id,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.warning(f"notify_assignee failed (chat_id={assignee_telegram_id}): {e}")


async def notify_admins(
    bot: Bot,
    case_id: str,
    category: CaseCategory,
    description: str,
    is_anonymous: bool,
) -> "Message | None":
    """Send notification to admin Telegram group and email.
    Returns the sent Telegram Message object (needed to store message_id for later editing).
    """
    cat_label = CATEGORY_LABELS.get(category, str(category))
    short_desc = description[:300] + ("..." if len(description) > 300 else "")
    anon_text = "✅ Anonim" if is_anonymous else "❌ Anonim emas"

    text = (
        f"🔔 *Yangi murojaat keldi!*\n\n"
        f"📋 *Raqam:* `{case_id}`\n"
        f"📂 *Kategoriya:* {cat_label}\n"
        f"🔒 *Anonimlik:* {anon_text}\n\n"
        f"📝 *Tavsif:*\n_{short_desc}_\n\n"
        f"👉 [Admin panelga o'ting]({settings.WEBHOOK_URL.replace('/api/telegram/webhook', '')}/admin)"
    )

    # Inline keyboard
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👤 Tayinlash",           callback_data=f"assign_{case_id}"),
            InlineKeyboardButton("🔍 Admin panelda ko'r",  callback_data=f"view_{case_id}"),
        ],
        [
            InlineKeyboardButton("▶️ Boshlash",  callback_data=f"start_{case_id}"),
            InlineKeyboardButton("❌ Rad etish", callback_data=f"reject_{case_id}"),
        ],
    ])

    sent_message: "Message | None" = None

    # Telegram notification
    try:
        sent_message = await bot.send_message(
            chat_id=settings.ADMIN_CHAT_ID,
            text=text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
        )
    except Exception as e:
        logger.error(f"Telegram notify failed: {e}")

    # Email notification
    try:
        await send_email_notification(case_id, cat_label, short_desc, is_anonymous)
    except Exception as e:
        logger.error(f"Email notify failed: {e}")

    return sent_message


async def send_email_notification(
    case_id: str, category: str, description: str, is_anonymous: bool
):
    if not settings.SMTP_USER:
        return

    html = f"""
    <html><body>
    <h2>🔔 Yangi murojaat: {case_id}</h2>
    <table border="1" cellpadding="8" style="border-collapse:collapse">
        <tr><td><b>Raqam</b></td><td>{case_id}</td></tr>
        <tr><td><b>Kategoriya</b></td><td>{category}</td></tr>
        <tr><td><b>Anonimlik</b></td><td>{"Ha" if is_anonymous else "Yo'q"}</td></tr>
        <tr><td><b>Tavsif (qisqa)</b></td><td>{description}</td></tr>
    </table>
    <br><a href="{settings.WEBHOOK_URL.replace('/api/telegram/webhook', '')}/admin">Admin panelga o'ting</a>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"[IntegrityBot] Yangi murojaat: {case_id}"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = settings.SMTP_USER
    msg.attach(MIMEText(html, "html"))

    smtp = aiosmtplib.SMTP(hostname=settings.SMTP_HOST, port=settings.SMTP_PORT, use_tls=False)
    await smtp.connect()
    if settings.SMTP_TLS:
        await smtp.starttls()
    await smtp.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
    await smtp.send_message(msg)
    await smtp.quit()


async def send_reporter_message(bot: Bot, telegram_chat_id: int, case_id: str, message: str):
    """Send reply back to reporter (works for both anonymous and non-anonymous cases)"""
    try:
        await bot.send_message(
            chat_id=telegram_chat_id,
            text=(
                f"📬 *Murojaat {case_id} bo'yicha javob keldi*\n"
                f"{'─' * 30}\n\n"
                f"{message}\n\n"
                f"_Compliance departamenti_"
            ),
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error(f"Failed to send reporter message to {telegram_chat_id}: {e}")


async def send_reporter_file(
    bot: Bot,
    telegram_chat_id: int,
    case_id: str,
    file_data: bytes,
    filename: str,
    mime_type: str,
    caption: str = "",
):
    """Send file/media from admin to reporter via Telegram"""
    import io
    caption_text = (
        f"📎 *Murojaat {case_id} bo'yicha fayl*"
        + (f"\n\n{caption}" if caption else "")
        + "\n\n_Compliance departamenti_"
    )
    try:
        buf = io.BytesIO(file_data)
        buf.name = filename

        if mime_type.startswith("image/"):
            await bot.send_photo(
                chat_id=telegram_chat_id,
                photo=buf,
                caption=caption_text,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif mime_type.startswith("video/"):
            await bot.send_video(
                chat_id=telegram_chat_id,
                video=buf,
                caption=caption_text,
                parse_mode=ParseMode.MARKDOWN,
            )
        elif mime_type.startswith("audio/"):
            await bot.send_audio(
                chat_id=telegram_chat_id,
                audio=buf,
                caption=caption_text,
                parse_mode=ParseMode.MARKDOWN,
                filename=filename,
            )
        elif mime_type == "audio/ogg" or filename.endswith(".oga") or filename.endswith(".opus"):
            await bot.send_voice(
                chat_id=telegram_chat_id,
                voice=buf,
                caption=caption_text,
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await bot.send_document(
                chat_id=telegram_chat_id,
                document=buf,
                filename=filename,
                caption=caption_text,
                parse_mode=ParseMode.MARKDOWN,
            )
    except Exception as e:
        logger.error(f"Failed to send file to reporter {telegram_chat_id}: {e}")

