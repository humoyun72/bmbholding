import asyncio
from app.core.config import settings
from telegram import Bot as TGBot

async def test_activate():
    print(f"POLL_CHAT_ID: {settings.POLL_CHAT_ID}")

    async with TGBot(token=settings.TELEGRAM_BOT_TOKEN) as bot:
        me = await bot.get_me()
        print(f"Bot: @{me.username}")

        try:
            msg = await bot.send_message(
                chat_id=settings.POLL_CHAT_ID,
                text="📊 *Test so'rovnoma*\n\nQuyidagi so'rovnomada ishtirok eting 👇",
                parse_mode="Markdown",
            )
            print(f"✅ Message sent: message_id={msg.message_id}")
        except Exception as e:
            print(f"❌ send_message ERROR: {type(e).__name__}: {e}")
            return

        try:
            poll_msg = await bot.send_poll(
                chat_id=settings.POLL_CHAT_ID,
                question="Admin paneldan test so'rovnomasi",
                options=["Variant A", "Variant B", "Variant C"],
                is_anonymous=True,
                allows_multiple_answers=False,
            )
            print(f"✅ Poll sent: message_id={poll_msg.message_id}, poll_id={poll_msg.poll.id}")
            print("🎉 SUCCESS!")
        except Exception as e:
            print(f"❌ send_poll ERROR: {type(e).__name__}: {e}")

asyncio.run(test_activate())
