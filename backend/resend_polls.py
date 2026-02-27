import asyncio
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models import Poll, PollQuestion, PollStatus
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from telegram import Bot as TGBot

async def resend_active_polls():
    """Mavjud active polllarni Telegram'ga qayta yuborish (kanal=anonymous, guruh=non-anonymous)"""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Poll)
            .options(selectinload(Poll.questions).selectinload(PollQuestion.options))
            .where(Poll.status == PollStatus.ACTIVE)
        )
        polls = result.scalars().all()
        print(f"Active polls: {len(polls)}")

        async with TGBot(token=settings.TELEGRAM_BOT_TOKEN) as bot:
            # Kanal yoki guruh ekanini aniqlash
            chat = await bot.get_chat(settings.POLL_CHAT_ID)
            is_channel = chat.type == "channel"
            print(f"Chat type: {chat.type} ({'anonymous' if is_channel else 'non-anonymous'})")

            for poll in polls:
                print(f"\nPoll: {poll.title} (id={poll.id})")
                try:
                    msg = await bot.send_message(
                        chat_id=settings.POLL_CHAT_ID,
                        text=f"📊 *{poll.title}*\n\nQuyidagi so'rovnomada ishtirok eting 👇",
                        parse_mode="Markdown",
                    )
                    print(f"  Announcement sent: {msg.message_id}")
                    await asyncio.sleep(1)

                    for question in sorted(poll.questions, key=lambda q: q.order):
                        options = sorted(question.options, key=lambda o: o.order)
                        tg_options = [o.option_text[:100] for o in options[:10]]
                        if len(tg_options) < 2:
                            print(f"  Skipping (need >=2 options): {question.question_text}")
                            continue
                        await asyncio.sleep(1)
                        poll_msg = await bot.send_poll(
                            chat_id=settings.POLL_CHAT_ID,
                            question=question.question_text[:300],
                            options=tg_options,
                            is_anonymous=is_channel,   # kanal=True, guruh=False
                        )
                        question.telegram_message_id = poll_msg.message_id
                        question.telegram_poll_id = poll_msg.poll.id
                        print(f"  Poll sent: msg_id={poll_msg.message_id}, poll_id={poll_msg.poll.id}, anonymous={is_channel}")

                    await db.commit()
                    print(f"  ✅ Done!")
                except Exception as e:
                    print(f"  ❌ ERROR: {type(e).__name__}: {e}")

asyncio.run(resend_active_polls())
