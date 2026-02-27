import asyncio
from app.core.config import settings

async def test():
    from app.api.v1.telegram import get_bot_app
    bot_app = get_bot_app()
    await bot_app.initialize()
    bot = bot_app.bot

    print(f"Bot: {(await bot.get_me()).username}")
    print(f"Sending to POLL_CHAT_ID: {settings.POLL_CHAT_ID}")

    # 1. Test oddiy xabar
    try:
        msg = await bot.send_message(
            chat_id=settings.POLL_CHAT_ID,
            text="Test xabar — admin paneldan poll testi"
        )
        print(f"Message sent OK: message_id={msg.message_id}")
    except Exception as e:
        print(f"send_message ERROR: {type(e).__name__}: {e}")

    # 2. Test native poll
    try:
        poll_msg = await bot.send_poll(
            chat_id=settings.POLL_CHAT_ID,
            question="Test so'rovnoma — admin paneldan",
            options=["Ha", "Yo'q", "Bilmayman"],
            is_anonymous=True,
        )
        print(f"Poll sent OK: message_id={poll_msg.message_id}, poll_id={poll_msg.poll.id}")
    except Exception as e:
        print(f"send_poll ERROR: {type(e).__name__}: {e}")

    await bot_app.shutdown()

asyncio.run(test())

