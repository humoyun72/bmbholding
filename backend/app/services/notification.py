import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from telegram import Bot
from telegram.constants import ParseMode
from app.core.config import settings
from app.models import CaseCategory

logger = logging.getLogger(__name__)

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
):
    """Send notification to admin Telegram group and email"""
    cat_label = CATEGORY_LABELS.get(category, str(category))
    short_desc = description[:300] + ("..." if len(description) > 300 else "")
    anon_text = "✅ Anonim" if is_anonymous else "❌ Anonim emas"

    message = (
        f"🔔 *Yangi murojaat keldi!*\n\n"
        f"📋 *Raqam:* `{case_id}`\n"
        f"📂 *Kategoriya:* {cat_label}\n"
        f"🔒 *Anonimlik:* {anon_text}\n\n"
        f"📝 *Tavsif:*\n_{short_desc}_\n\n"
        f"👉 [Admin panelga o'ting]({settings.WEBHOOK_URL.replace('/api/telegram/webhook', '')}/admin)"
    )

    # Telegram notification
    try:
        await bot.send_message(
            chat_id=settings.ADMIN_CHAT_ID,
            text=message,
            parse_mode=ParseMode.MARKDOWN,
        )
    except Exception as e:
        logger.error(f"Telegram notify failed: {e}")

    # Email notification
    try:
        await send_email_notification(case_id, cat_label, short_desc, is_anonymous)
    except Exception as e:
        logger.error(f"Email notify failed: {e}")


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

