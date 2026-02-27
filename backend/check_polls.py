import asyncio
import uuid
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.models import Poll, PollQuestion, PollOption, PollStatus
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Poll)
            .options(selectinload(Poll.questions).selectinload(PollQuestion.options))
            .order_by(Poll.created_at.desc())
        )
        polls = result.scalars().all()
        print(f"Total polls: {len(polls)}")
        for p in polls:
            print(f"\nPoll: {p.title} | status={p.status} | id={p.id}")
            for q in p.questions:
                print(f"  Q: {q.question_text}")
                print(f"     telegram_message_id={q.telegram_message_id}")
                print(f"     telegram_poll_id={q.telegram_poll_id}")
                for o in q.options:
                    print(f"     Option: {o.option_text} | votes={o.vote_count}")

asyncio.run(check())

