from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
import logging
import os
import asyncio

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging_config import setup_logging
from app.models import *  # noqa - register all models
from app.api.v1 import auth, cases, polls, telegram, audit, ws, tickets
from app.api.v1 import settings as settings_api

# ── Logging: JSON structured logging (structlog) ─────────────────────────────
setup_logging()

logger = logging.getLogger(__name__)

_polling_task = None
_redis_subscriber_task = None
_retention_task = None
_report_task = None
_deadline_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _polling_task, _redis_subscriber_task, _retention_task, _report_task, _deadline_task
    # ── Secrets backend (Vault / AWS KMS / env) ──────────────────────────
    from app.services.secrets import bootstrap_secrets
    await bootstrap_secrets()

    # Startup
    logger.info("Starting IntegrityBot API...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created/verified")

    # Create default admin if none exists
    from app.core.database import AsyncSessionLocal
    from app.core.security import hash_password
    from sqlalchemy import select
    from app.models import User, UserRole

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.role == UserRole.ADMIN))
        admin = result.scalar_one_or_none()
        if not admin:
            try:
                # Hardcoded parol ishlatilmaydi — .env dan o'qiladi
                admin_password = settings.ADMIN_DEFAULT_PASSWORD
                if admin_password == "CHANGE_ME" or len(admin_password) < 8:
                    logger.critical(
                        "⛔ ADMIN_DEFAULT_PASSWORD sozlanmagan yoki juda qisqa! "
                        ".env faylida ADMIN_DEFAULT_PASSWORD ni o'rnating (kamida 8 belgi)."
                    )
                    admin_password = "Admin@CHANGE_ME_NOW!"

                default_admin = User(
                    username="admin",
                    email="admin@company.uz",
                    full_name="Administrator",
                    hashed_password=hash_password(admin_password),
                    role=UserRole.ADMIN,
                    force_password_change=True,  # Birinchi kirishda majburiy o'zgartirish
                )
                db.add(default_admin)
                await db.commit()
                logger.warning(
                    "⚠️  Default admin yaratildi. "
                    "BIRINCHI KIRISHDA PAROLNI O'ZGARTIRING! "
                    "(force_password_change=True)"
                )
            except Exception:
                await db.rollback()
                logger.info("Admin user already exists, skipping creation.")

    # Start Redis subscriber for WebSocket broadcast (ixtiyoriy — REDIS_URL bo'lsa)
    if settings.REDIS_URL:
        from app.services.websocket_manager import redis_subscriber
        _redis_subscriber_task = asyncio.create_task(redis_subscriber(settings.REDIS_URL))
        logger.info("Redis WS subscriber started ✅")
    else:
        logger.info("REDIS_URL sozlanmagan — WebSocket bitta jarayonda ishlaydi (shared hosting)")

    # Start data retention scheduler (har kecha 02:00 UTC)
    from app.services.retention import run_retention
    _retention_task = asyncio.create_task(_run_retention_scheduler())
    logger.info("Data retention scheduler started ✅ (daily at 02:00 UTC)")

    # Start report scheduler (kunlik + haftalik hisobotlar)
    _report_task = asyncio.create_task(_run_report_scheduler())
    logger.info("Report scheduler started ✅")

    # Start deadline reminder scheduler
    _deadline_task = asyncio.create_task(_run_deadline_scheduler())
    logger.info("Deadline reminder scheduler started ✅")

    # ClamAV holati haqida startup logi
    if settings.CLAMAV_ENABLED:
        logger.info("🛡️  ClamAV antivirus YOQILGAN — fayllar skanlanadi")
    else:
        logger.warning(
            "⚠️  ClamAV antivirus O'CHIRILGAN (CLAMAV_ENABLED=false). "
            "Production muhitida yoqishni tavsiya qilamiz: "
            "docker compose --profile production up -d clamav"
        )

    # Start bot — webhook/polling konfliktini oldini olish
    bot_mode = settings.effective_bot_mode
    webhook_url_display = settings.WEBHOOK_URL or "(bosh)"
    logger.info(
        f"Bot rejimi: {bot_mode.upper()} "
        f"(BOT_MODE='{settings.BOT_MODE}', WEBHOOK_URL='{webhook_url_display}')"
    )

    if bot_mode == "polling":
        # Polling rejimi — avval webhook o'chiramiz (409 Conflict oldini olish)
        logger.info("Starting bot in POLLING mode...")
        from app.api.v1.telegram import get_bot_app
        bot_app = get_bot_app()
        await bot_app.initialize()
        try:
            await bot_app.bot.delete_webhook(drop_pending_updates=True)
            logger.info("Eski webhook o'chirildi (polling uchun) ✅")
        except Exception as e:
            logger.warning(f"Webhook o'chirishda xato (muhim emas): {e}")
        await bot_app.start()
        _polling_task = asyncio.create_task(_run_polling(bot_app))
        logger.info("Bot polling started ✅")
    else:
        # Webhook rejimi — polling ISHGA TUSHIRILMAYDI
        logger.info(f"Bot WEBHOOK rejimida ishlaydi: {settings.WEBHOOK_URL}")
        logger.info("Polling ishga tushirilmaydi — webhook orqali xabarlar qabul qilinadi")
        # Webhook ni Telegram ga ro'yxatdan o'tkazish (agar allaqachon o'rnatilmagan bo'lsa)
        try:
            from app.api.v1.telegram import get_bot_app
            bot_app = get_bot_app()
            await bot_app.initialize()
            webhook_info = await bot_app.bot.get_webhook_info()
            if webhook_info.url != settings.WEBHOOK_URL:
                await bot_app.bot.set_webhook(
                    url=settings.WEBHOOK_URL,
                    secret_token=settings.WEBHOOK_SECRET,
                    allowed_updates=["message", "callback_query", "edited_message", "poll_answer", "poll"],
                )
                logger.info(f"Webhook yangilandi: {settings.WEBHOOK_URL} ✅")
            else:
                logger.info(f"Webhook allaqachon o'rnatilgan: {settings.WEBHOOK_URL} ✅")
        except Exception as e:
            logger.error(
                f"⚠️  Webhook o'rnatishda xato: {e}. "
                "Qo'lda o'rnatish uchun: POST /api/telegram/set-webhook"
            )

    yield

    # Shutdown
    logger.info("Shutting down...")
    if _redis_subscriber_task:
        _redis_subscriber_task.cancel()
        try:
            await _redis_subscriber_task
        except asyncio.CancelledError:
            pass
    if _retention_task:
        _retention_task.cancel()
        try:
            await _retention_task
        except asyncio.CancelledError:
            pass
    if _report_task:
        _report_task.cancel()
        try:
            await _report_task
        except asyncio.CancelledError:
            pass
    if _deadline_task:
        _deadline_task.cancel()
        try:
            await _deadline_task
        except asyncio.CancelledError:
            pass
    if _polling_task:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
    if settings.effective_bot_mode == "polling":
        from app.api.v1.telegram import get_bot_app
        bot_app = get_bot_app()
        await bot_app.stop()
        await bot_app.shutdown()
    await engine.dispose()


async def _run_polling(bot_app):
    """Run bot polling loop"""
    try:
        await bot_app.updater.start_polling(
            allowed_updates=[
                "message",
                "callback_query",
                "edited_message",
                "poll_answer",   # native poll'da ovoz berilganda
                "poll",          # poll holati o'zganganda
            ],
            drop_pending_updates=True,
        )
        # Keep running until cancelled
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await bot_app.updater.stop()
        raise


async def _run_retention_scheduler():
    """
    Data retention'ni har kecha 02:00 UTC da ishga tushiradi.
    Birinchi ishga tushirishdan oldin 02:00 ga qadar kutadi.
    """
    from app.services.retention import run_retention

    while True:
        try:
            now = datetime.now(timezone.utc)
            # Keyingi 02:00 UTC gacha hisoblash
            next_run = now.replace(hour=2, minute=0, second=0, microsecond=0)
            if next_run <= now:
                next_run = next_run + timedelta(days=1)
            wait_seconds = (next_run - now).total_seconds()

            logger.info(
                f"Data retention keyingi ishga tushishi: {next_run.strftime('%Y-%m-%d %H:%M')} UTC "
                f"({wait_seconds / 3600:.1f} soatdan keyin)"
            )
            await asyncio.sleep(wait_seconds)

            logger.info("Data retention ishga tushmoqda...")
            stats = await run_retention()
            logger.info(f"Data retention yakunlandi: {stats}")

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Data retention xato: {e}", exc_info=True)
            await asyncio.sleep(3600)  # Xato bo'lsa 1 soatdan keyin qayta urinish


async def _run_deadline_scheduler():
    """
    Deadline eslatmalarni belgilangan oraliqda yuboradi.
    Interval SystemSettings dan o'qiladi: "deadline_check_interval_hours" (default: 4 soat).
    """
    from app.core.database import AsyncSessionLocal
    from app.api.v1.settings import get_all_settings
    from app.bot.reports import send_deadline_reminders

    # Startup da 60 soniya kutish (bot to'liq ishga tushishi uchun)
    await asyncio.sleep(60)
    logger.info("Deadline reminder scheduler ishga tushdi")

    while True:
        try:
            # SystemSettings dan intervalni o'qish
            interval_hours = 4  # default
            try:
                async with AsyncSessionLocal() as db:
                    sys_settings = await get_all_settings(db)
                interval_hours = int(sys_settings.get("deadline_check_interval_hours", "4"))
                if interval_hours < 1:
                    interval_hours = 1
            except Exception as e:
                logger.warning(f"Deadline interval o'qishda xato, default 4 soat: {e}")

            logger.info(f"Deadline reminder tekshiruvi boshlanmoqda (interval: {interval_hours} soat)")

            try:
                sent = await send_deadline_reminders()
                logger.info(f"Deadline reminders yakunlandi: {sent or 0} ta xabar yuborildi ✅")
            except Exception as e:
                logger.error(f"Deadline reminders xatosi: {e}", exc_info=True)

            await asyncio.sleep(interval_hours * 3600)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Deadline scheduler xato: {e}", exc_info=True)
            await asyncio.sleep(3600)


async def _run_report_scheduler():
    """
    Kunlik va haftalik hisobotlarni belgilangan vaqtda yuboradi.
    Vaqtlar SystemSettings dan o'qiladi (fallback: kunlik 13:00 UTC = 18:00 UZT,
    haftalik dushanba 04:00 UTC = 09:00 UZT).
    """
    from app.core.database import AsyncSessionLocal
    from app.api.v1.settings import get_all_settings
    from app.bot.reports import send_daily_report, send_weekly_report

    logger.info("Report scheduler ishga tushdi")

    while True:
        try:
            now = datetime.now(timezone.utc)

            # ── Sozlamalarni o'qish ───────────────────────────────────────
            async with AsyncSessionLocal() as db:
                sys_settings = await get_all_settings(db)

            # Sozlamalar UI tomonidan "notif_" prefiksi bilan saqlanadi (NOTIFICATION_KEYS),
            # eski DEFAULTS esa "notify_" prefiksi bilan. Yangi kalit ustuvor.
            daily_enabled_raw = sys_settings.get(
                "notif_daily_report_enabled",
                sys_settings.get("notify_daily_report", "true"),
            )
            daily_enabled = str(daily_enabled_raw).lower() == "true"

            weekly_enabled_raw = sys_settings.get(
                "notif_weekly_report_enabled",
                sys_settings.get("notify_weekly_report", "true"),
            )
            weekly_enabled = str(weekly_enabled_raw).lower() == "true"

            # Vaqtni parse qilish (HH:MM) → UTC ga o'tkazish (UZT - 5)
            daily_time_str = sys_settings.get(
                "notif_daily_report_time",
                sys_settings.get("notify_daily_report_time", "18:00"),
            )
            weekly_time_str = sys_settings.get(
                "notif_weekly_report_time",
                sys_settings.get("notify_weekly_report_time", "09:00"),
            )

            # weekly_day: NOTIFICATION_KEYS 0-asosli (0=Dush) saqlaydi,
            # eski DEFAULTS esa 1-asosli (1=Dush). Scheduler formula 1-asosli kutadi.
            if "notif_weekly_report_day" in sys_settings:
                weekly_day = int(sys_settings["notif_weekly_report_day"]) + 1  # 0-asosli → 1-asosli
            else:
                weekly_day = int(sys_settings.get("notify_weekly_report_day", "1"))  # 1=Dushanba

            def parse_hhmm_to_utc(time_str: str):
                """HH:MM (UZT) → UTC soat, daqiqa"""
                try:
                    h, m = map(int, time_str.split(":"))
                    utc_h = (h - 5) % 24
                    return utc_h, m
                except Exception:
                    return 13, 0  # fallback: 18:00 UZT = 13:00 UTC

            d_hour, d_min = parse_hhmm_to_utc(daily_time_str)
            w_hour, w_min = parse_hhmm_to_utc(weekly_time_str)

            # ── Keyingi ishga tushirish vaqtlarini hisoblash ──────────────
            # Kunlik
            next_daily = now.replace(hour=d_hour, minute=d_min, second=0, microsecond=0)
            if next_daily <= now:
                next_daily += timedelta(days=1)

            # Haftalik — kelasi weekly_day (0=Dush)
            days_ahead = (weekly_day - 1 - now.weekday()) % 7
            next_weekly = (now + timedelta(days=days_ahead)).replace(
                hour=w_hour, minute=w_min, second=0, microsecond=0)
            if next_weekly <= now:
                next_weekly += timedelta(weeks=1)

            # Ikki vaqtdan eng yaqinini kutamiz
            wait_until = next_daily
            run_type = "daily"
            if weekly_enabled and next_weekly < next_daily:
                wait_until = next_weekly
                run_type = "weekly"

            wait_sec = max((wait_until - now).total_seconds(), 1)
            logger.info(
                f"Keyingi hisobot: {run_type} — "
                f"{wait_until.strftime('%Y-%m-%d %H:%M')} UTC "
                f"({wait_sec/3600:.1f} soatdan keyin)"
            )

            await asyncio.sleep(wait_sec)

            # ── Hisobotni yuborish ────────────────────────────────────────
            now_after = datetime.now(timezone.utc)
            if run_type == "daily" and daily_enabled:
                try:
                    await send_daily_report()
                    logger.info("Kunlik hisobot yuborildi ✅")
                except Exception as e:
                    logger.error(f"Kunlik hisobot xatosi: {e}", exc_info=True)
            elif run_type == "weekly" and weekly_enabled:
                try:
                    await send_weekly_report()
                    logger.info("Haftalik hisobot yuborildi ✅")
                except Exception as e:
                    logger.error(f"Haftalik hisobot xatosi: {e}", exc_info=True)

            # Ikki marta ishlamasligi uchun 70 soniya kutamiz
            await asyncio.sleep(70)

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"Report scheduler xato: {e}", exc_info=True)
            await asyncio.sleep(300)  # 5 daqiqa kutib qayta urinish


app = FastAPI(
    title="IntegrityBot API",
    description="Anonymous whistleblowing bot with admin panel",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Prometheus metrics — /api/metrics endpoint
try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        excluded_handlers=["/api/health", "/api/metrics"],
    ).instrument(app).expose(app, endpoint="/api/metrics", include_in_schema=False)
    logger.info("Prometheus metrics enabled at /api/metrics")
except ImportError:
    logger.warning("prometheus-fastapi-instrumentator not installed, metrics disabled")

# Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(cases.router, prefix="/api/v1")
app.include_router(polls.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(tickets.router, prefix="/api/v1")
app.include_router(settings_api.router, prefix="/api/v1")
app.include_router(ws.router, prefix="/api")
app.include_router(telegram.router, prefix="/api")

# Serve uploads (only in dev — use nginx in prod)
if settings.ENVIRONMENT != "production":
    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.UPLOADS_DIR), name="uploads")


@app.get("/api/health")
async def health():
    from app.services.storage import check_s3_connection, check_clamav_health
    from app.services.jira_integration import ticket_service
    from app.services.siem import siem_service
    storage_info = await check_s3_connection()
    clamav_info = await check_clamav_health()
    ticket_info = await ticket_service.health_check()
    siem_info = siem_service.status()   # health_check() SIEM ga test event yuboradi, status() yetarli
    return {
        "status": "ok",
        "version": "1.0.0",
        "storage": storage_info,
        "antivirus": clamav_info,
        "ticketing": ticket_info,
        "siem": siem_info,
    }
