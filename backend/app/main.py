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
from app.models import *  # noqa - register all models
from app.api.v1 import auth, cases, polls, telegram, audit, ws

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_polling_task = None
_redis_subscriber_task = None
_retention_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _polling_task, _redis_subscriber_task
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

    # Start Redis subscriber for WebSocket broadcast
    from app.services.websocket_manager import redis_subscriber
    _redis_subscriber_task = asyncio.create_task(redis_subscriber(settings.REDIS_URL))
    logger.info("Redis WS subscriber started ✅")

    # Start data retention scheduler (har kecha 02:00 UTC)
    from app.services.retention import run_retention
    _retention_task = asyncio.create_task(_run_retention_scheduler())
    logger.info("Data retention scheduler started ✅ (daily at 02:00 UTC)")

    # Start bot
    if settings.BOT_MODE == "polling":
        logger.info("Starting bot in POLLING mode...")
        from app.api.v1.telegram import get_bot_app
        bot_app = get_bot_app()
        await bot_app.initialize()
        await bot_app.bot.delete_webhook(drop_pending_updates=True)
        await bot_app.start()
        _polling_task = asyncio.create_task(_run_polling(bot_app))
        logger.info("Bot polling started ✅")
    else:
        logger.info("Bot mode: WEBHOOK (set webhook URL via /api/telegram/set-webhook)")

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
    if _polling_task:
        _polling_task.cancel()
        try:
            await _polling_task
        except asyncio.CancelledError:
            pass
    if settings.BOT_MODE == "polling":
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
app.include_router(ws.router, prefix="/api")
app.include_router(telegram.router, prefix="/api")

# Serve uploads (only in dev — use nginx in prod)
if settings.ENVIRONMENT != "production":
    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.UPLOADS_DIR), name="uploads")


@app.get("/api/health")
async def health():
    from app.services.storage import check_s3_connection
    storage_info = await check_s3_connection()
    return {
        "status": "ok",
        "version": "1.0.0",
        "storage": storage_info,
    }
