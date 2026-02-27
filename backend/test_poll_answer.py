"""
poll_answer update kelayotganini tekshirish
Bu skriptni ishga tushirib, Telegram'da ovoz bering
"""
import asyncio
from telegram import Bot as TGBot
from app.core.config import settings

async def listen_updates():
    async with TGBot(token=settings.TELEGRAM_BOT_TOKEN) as bot:
        me = await bot.get_me()
        print(f"Bot: @{me.username}")
        print(f"Listening for poll_answer updates... (Telegram'da ovoz bering!)")
        print("-" * 50)

        offset = None
        for i in range(30):  # 30 ta urinish (30 soniya)
            updates = await bot.get_updates(
                offset=offset,
                timeout=2,
                allowed_updates=["poll_answer", "poll", "message"],
            )
            for update in updates:
                offset = update.update_id + 1
                print(f"UPDATE #{update.update_id}: type={list(update.__dict__.keys())}")
                if update.poll_answer:
                    pa = update.poll_answer
                    print(f"  ✅ POLL_ANSWER: poll_id={pa.poll_id}, options={pa.option_ids}")
                if update.poll:
                    print(f"  📊 POLL update: id={update.poll.id}, total_voters={update.poll.total_voter_count}")
                if update.message:
                    print(f"  💬 MESSAGE: {update.message.text}")
            await asyncio.sleep(1)
        print("Done.")

asyncio.run(listen_updates())

