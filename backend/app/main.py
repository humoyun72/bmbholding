from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
import os
import asyncio

from app.core.config import settings
from app.core.database import engine, Base
from app.models import *  # noqa - register all models
from app.api.v1 import auth, cases, polls, telegram, audit

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

_polling_task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _polling_task
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
                default_admin = User(
                    username="admin",
                    email="admin@company.uz",
                    full_name="Administrator",
                    hashed_password=hash_password("Admin@123456"),
                    role=UserRole.ADMIN,
                )
                db.add(default_admin)
                await db.commit()
                logger.warning("Default admin created: admin / Admin@123456 — CHANGE IMMEDIATELY!")
            except Exception:
                await db.rollback()
                logger.info("Admin user already exists, skipping creation.")

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
            allowed_updates=["message", "callback_query", "edited_message"],
            drop_pending_updates=True,
        )
        # Keep running until cancelled
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        await bot_app.updater.stop()
        raise


app = FastAPI(
    title="IntegrityBot API",
    description="Anonymous whistleblowing bot with admin panel",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(cases.router, prefix="/api/v1")
app.include_router(polls.router, prefix="/api/v1")
app.include_router(audit.router, prefix="/api/v1")
app.include_router(telegram.router, prefix="/api")

# Serve uploads (only in dev — use nginx in prod)
if settings.ENVIRONMENT != "production":
    os.makedirs(settings.UPLOADS_DIR, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.UPLOADS_DIR), name="uploads")


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
