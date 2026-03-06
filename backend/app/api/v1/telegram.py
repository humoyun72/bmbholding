from fastapi import APIRouter, Request, HTTPException, Depends
from telegram import Update
from app.core.config import settings
import logging

router = APIRouter(prefix="/telegram", tags=["telegram"])
logger = logging.getLogger(__name__)

_bot_app = None


def get_bot_app():
    global _bot_app
    if _bot_app is None:
        from app.bot.handlers import build_application
        _bot_app = build_application()
    return _bot_app


@router.post("/webhook")
async def telegram_webhook(request: Request):
    # Validate secret token
    secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
    if secret != settings.WEBHOOK_SECRET:
        raise HTTPException(status_code=403, detail="Noto'g'ri webhook maxfiy kaliti")

    try:
        data = await request.json()
        app = get_bot_app()
        update = Update.de_json(data, app.bot)
        await app.process_update(update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")

    return {"ok": True}


@router.post("/set-webhook")
async def set_webhook():
    """Set the webhook URL with Telegram"""
    if not settings.WEBHOOK_URL:
        raise HTTPException(status_code=400, detail="WEBHOOK_URL .env faylida sozlanmagan")
    if not settings.WEBHOOK_URL.startswith("https://"):
        raise HTTPException(
            status_code=400,
            detail="WEBHOOK_URL https:// bilan boshlanishi kerak. "
                   "Lokal dev uchun polling rejimini ishlating (WEBHOOK_URL=bo'sh)."
        )
    app = get_bot_app()
    await app.initialize()
    await app.bot.set_webhook(
        url=settings.WEBHOOK_URL,
        secret_token=settings.WEBHOOK_SECRET,
        allowed_updates=["message", "callback_query", "edited_message", "poll_answer", "poll"],
    )
    return {"ok": True, "message": f"Webhook ulandi: {settings.WEBHOOK_URL}", "mode": "webhook"}


@router.post("/delete-webhook")
async def delete_webhook():
    """Delete the webhook (switch to polling mode)"""
    app = get_bot_app()
    await app.initialize()
    await app.bot.delete_webhook(drop_pending_updates=True)
    return {"ok": True, "message": "Webhook o'chirildi"}


@router.get("/info")
async def bot_info():
    """Get bot information and status"""
    try:
        app = get_bot_app()
        await app.initialize()
        me = await app.bot.get_me()
        webhook = await app.bot.get_webhook_info()
        return {
            "ok": True,
            "bot": {
                "id": me.id,
                "username": f"@{me.username}",
                "name": me.full_name,
                "link": f"https://t.me/{me.username}",
            },
            "mode": settings.effective_bot_mode,
            "mode_config": settings.BOT_MODE,  # config dagi qiymat
            "webhook_url": webhook.url or "(none - polling mode)",
            "pending_updates": webhook.pending_update_count,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
