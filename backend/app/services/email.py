"""
Email yuborish servisi.
SMTP orqali transaksion emaillar (parol tiklash va boshqalar) yuboradi.
"""
import aiosmtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)


async def send_email(to: str, subject: str, body: str, html: str = None) -> bool:
    """
    Email yuboradi.
    SMTP sozlamalari .env faylidan olinadi.
    """
    if not settings.SMTP_USER or not settings.SMTP_HOST:
        logger.warning("SMTP sozlanmagan — email yuborilmadi")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM or settings.SMTP_USER
    msg["To"] = to

    msg.attach(MIMEText(body, "plain", "utf-8"))
    if html:
        msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.SMTP_HOST,
            port=settings.SMTP_PORT,
            username=settings.SMTP_USER,
            password=settings.SMTP_PASSWORD,
            use_tls=False,
            start_tls=settings.SMTP_TLS,
        )
        logger.info(f"Email yuborildi: {to} — {subject}")
        return True
    except Exception as e:
        logger.error(f"Email yuborishda xato ({to}): {e}")
        return False
