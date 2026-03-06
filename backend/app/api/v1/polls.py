from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone
import uuid
import logging

from app.core.database import get_db
from app.core.config import settings
from app.models import Poll, PollQuestion, PollOption, PollStatus, User, AuditLog, AuditAction
from app.api.v1.auth import get_current_user, require_investigator_or_above, require_admin
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/polls", tags=["polls"])
logger = logging.getLogger(__name__)


class OptionCreate(BaseModel):
    option_text: str
    order: int = 0


class QuestionCreate(BaseModel):
    question_text: str
    order: int = 0
    options: list[OptionCreate]


class PollCreate(BaseModel):
    title: str
    description: Optional[str] = None
    questions: list[QuestionCreate]


@router.post("")
async def create_poll(
    body: PollCreate,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    poll = Poll(
        created_by=current_user.id,
        title=body.title,
        description=body.description,
        status=PollStatus.DRAFT,
    )
    db.add(poll)
    await db.flush()

    for q_data in body.questions:
        question = PollQuestion(
            poll_id=poll.id,
            question_text=q_data.question_text,
            order=q_data.order,
        )
        db.add(question)
        await db.flush()

        for o_data in q_data.options:
            option = PollOption(
                question_id=question.id,
                option_text=o_data.option_text,
                order=o_data.order,
            )
            db.add(option)

    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.SURVEY_CREATE,
        entity_type="poll",
        entity_id=str(poll.id),
    ))
    await db.commit()
    return {"id": str(poll.id), "message": "Poll created"}


@router.get("")
async def list_polls(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Poll)
        .options(selectinload(Poll.questions).selectinload(PollQuestion.options))
        .order_by(Poll.created_at.desc())
    )
    polls = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "description": p.description,
            "status": p.status,
            "created_at": p.created_at,
            "closed_at": p.closed_at,
            "questions_count": len(p.questions),
            "total_votes": sum(
                o.vote_count
                for q in p.questions
                for o in q.options
            ),
        }
        for p in polls
    ]


@router.get("/{poll_id}")
async def get_poll(
    poll_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Poll)
        .options(selectinload(Poll.questions).selectinload(PollQuestion.options))
        .where(Poll.id == uuid.UUID(poll_id))
    )
    poll = result.scalar_one_or_none()
    if not poll:
        raise HTTPException(status_code=404, detail="So'rovnoma topilmadi")

    return {
        "id": str(poll.id),
        "title": poll.title,
        "description": poll.description,
        "status": poll.status,
        "created_at": poll.created_at,
        "poll_chat_id": settings.POLL_CHAT_ID or None,
        "questions": [
            {
                "id": str(q.id),
                "question_text": q.question_text,
                "order": q.order,
                "telegram_message_id": q.telegram_message_id,
                "options": [
                    {"id": str(o.id), "option_text": o.option_text, "vote_count": o.vote_count, "order": o.order}
                    for o in sorted(q.options, key=lambda x: x.order)
                ],
            }
            for q in sorted(poll.questions, key=lambda x: x.order)
        ],
    }


@router.post("/{poll_id}/activate")
async def activate_poll(
    poll_id: str,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Poll)
        .options(selectinload(Poll.questions).selectinload(PollQuestion.options))
        .where(Poll.id == uuid.UUID(poll_id))
    )
    poll = result.scalar_one_or_none()
    if not poll:
        raise HTTPException(status_code=404, detail="So'rovnoma topilmadi")
    if poll.status != PollStatus.DRAFT:
        raise HTTPException(status_code=400, detail="Faqat qoralama so'rovnomalarni faollashtirish mumkin")

    poll.status = PollStatus.ACTIVE

    # Send each question as a native Telegram poll to POLL_CHAT_ID
    sent_count = 0
    if settings.POLL_CHAT_ID:
        try:
            from telegram import Bot as TGBot
            async with TGBot(token=settings.TELEGRAM_BOT_TOKEN) as bot:
                # Kanal yoki guruh ekanini aniqlash
                chat = await bot.get_chat(settings.POLL_CHAT_ID)
                is_channel = chat.type == "channel"
                # Kanal=anonymous (poll_update), guruh=non-anonymous (poll_answer)

                # Send poll title announcement first
                await bot.send_message(
                    chat_id=settings.POLL_CHAT_ID,
                    text=(
                        f"📊 *{poll.title}*"
                        + (f"\n\n_{poll.description}_" if poll.description else "")
                        + f"\n\nQuyidagi so'rovnomada ishtirok eting 👇"
                    ),
                    parse_mode="Markdown",
                )

                for question in sorted(poll.questions, key=lambda q: q.order):
                    options = sorted(question.options, key=lambda o: o.order)
                    tg_options = [o.option_text[:100] for o in options[:10]]

                    import asyncio
                    await asyncio.sleep(1)
                    msg = await bot.send_poll(
                        chat_id=settings.POLL_CHAT_ID,
                        question=question.question_text[:300],
                        options=tg_options,
                        is_anonymous=is_channel,
                        allows_multiple_answers=False,
                    )
                    question.telegram_message_id = msg.message_id
                    question.telegram_poll_id = msg.poll.id
                    sent_count += 1

        except Exception as e:
            logger.error(f"Failed to send poll to Telegram: {e}")
    else:
        logger.warning("POLL_CHAT_ID not set — poll activated without Telegram delivery")

    await db.commit()

    return {
        "message": "Poll activated",
        "telegram_sent": sent_count,
        "warning": None if settings.POLL_CHAT_ID else "POLL_CHAT_ID sozlanmagan — .env faylda POLL_CHAT_ID ni o'rnating",
    }


@router.post("/{poll_id}/vote/{option_id}")
async def vote(
    poll_id: str,
    option_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Anonymous voting endpoint (no auth required for Telegram users)"""
    result = await db.execute(
        select(PollOption)
        .join(PollQuestion)
        .join(Poll)
        .where(
            PollOption.id == uuid.UUID(option_id),
            Poll.id == uuid.UUID(poll_id),
            Poll.status == PollStatus.ACTIVE,
        )
    )
    option = result.scalar_one_or_none()
    if not option:
        raise HTTPException(status_code=404, detail="Variant topilmadi yoki so'rovnoma faol emas")

    option.vote_count += 1
    await db.commit()
    return {"message": "Vote recorded"}


@router.post("/{poll_id}/close")
async def close_poll(
    poll_id: str,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Poll)
        .options(selectinload(Poll.questions))
        .where(Poll.id == uuid.UUID(poll_id))
    )
    poll = result.scalar_one_or_none()
    if not poll:
        raise HTTPException(status_code=404, detail="So'rovnoma topilmadi")

    poll.status = PollStatus.CLOSED
    poll.closed_at = datetime.now(timezone.utc)

    # Stop Telegram polls
    if settings.POLL_CHAT_ID:
        try:
            from telegram import Bot as TGBot
            async with TGBot(token=settings.TELEGRAM_BOT_TOKEN) as bot:
                for question in poll.questions:
                    if question.telegram_message_id:
                        try:
                            await bot.stop_poll(
                                chat_id=settings.POLL_CHAT_ID,
                                message_id=question.telegram_message_id,
                            )
                        except Exception as e:
                            logger.warning(f"Could not stop Telegram poll {question.id}: {e}")
                await bot.send_message(
                    chat_id=settings.POLL_CHAT_ID,
                    text=f"✅ *{poll.title}* so'rovnomasi yakunlandi. Ishtirok etganlar uchun rahmat!",
                    parse_mode="Markdown",
                )
        except Exception as e:
            logger.error(f"Failed to close Telegram poll: {e}")

    await db.commit()
    return {"message": "Poll closed"}



class OptionCreate(BaseModel):
    option_text: str
    order: int = 0


class QuestionCreate(BaseModel):
    question_text: str
    order: int = 0
    options: list[OptionCreate]


class PollCreate(BaseModel):
    title: str
    description: Optional[str] = None
    questions: list[QuestionCreate]


@router.post("")
async def create_poll(
    body: PollCreate,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    poll = Poll(
        created_by=current_user.id,
        title=body.title,
        description=body.description,
        status=PollStatus.DRAFT,
    )
    db.add(poll)
    await db.flush()

    for q_data in body.questions:
        question = PollQuestion(
            poll_id=poll.id,
            question_text=q_data.question_text,
            order=q_data.order,
        )
        db.add(question)
        await db.flush()

        for o_data in q_data.options:
            option = PollOption(
                question_id=question.id,
                option_text=o_data.option_text,
                order=o_data.order,
            )
            db.add(option)

    db.add(AuditLog(
        user_id=current_user.id,
        action=AuditAction.SURVEY_CREATE,
        entity_type="poll",
        entity_id=str(poll.id),
    ))
    await db.commit()
    return {"id": str(poll.id), "message": "Poll created"}


@router.get("")
async def list_polls(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Poll)
        .options(selectinload(Poll.questions).selectinload(PollQuestion.options))
        .order_by(Poll.created_at.desc())
    )
    polls = result.scalars().all()
    return [
        {
            "id": str(p.id),
            "title": p.title,
            "description": p.description,
            "status": p.status,
            "created_at": p.created_at,
            "closed_at": p.closed_at,
            "questions_count": len(p.questions),
            "total_votes": sum(
                o.vote_count
                for q in p.questions
                for o in q.options
            ),
        }
        for p in polls
    ]


@router.get("/{poll_id}")
async def get_poll(
    poll_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Poll)
        .options(selectinload(Poll.questions).selectinload(PollQuestion.options))
        .where(Poll.id == uuid.UUID(poll_id))
    )
    poll = result.scalar_one_or_none()
    if not poll:
        raise HTTPException(status_code=404, detail="So'rovnoma topilmadi")

    return {
        "id": str(poll.id),
        "title": poll.title,
        "description": poll.description,
        "status": poll.status,
        "created_at": poll.created_at,
        "questions": [
            {
                "id": str(q.id),
                "question_text": q.question_text,
                "order": q.order,
                "options": [
                    {"id": str(o.id), "option_text": o.option_text, "vote_count": o.vote_count, "order": o.order}
                    for o in sorted(q.options, key=lambda x: x.order)
                ],
            }
            for q in sorted(poll.questions, key=lambda x: x.order)
        ],
    }


@router.post("/{poll_id}/activate")
async def activate_poll(
    poll_id: str,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Poll).where(Poll.id == uuid.UUID(poll_id)))
    poll = result.scalar_one_or_none()
    if not poll:
        raise HTTPException(status_code=404, detail="So'rovnoma topilmadi")

    poll.status = PollStatus.ACTIVE
    await db.commit()

    # TODO: Send poll to Telegram bot as native poll
    return {"message": "Poll activated"}


@router.post("/{poll_id}/vote/{option_id}")
async def vote(
    poll_id: str,
    option_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Anonymous voting endpoint (no auth required for Telegram users)"""
    result = await db.execute(
        select(PollOption)
        .join(PollQuestion)
        .join(Poll)
        .where(
            PollOption.id == uuid.UUID(option_id),
            Poll.id == uuid.UUID(poll_id),
            Poll.status == PollStatus.ACTIVE,
        )
    )
    option = result.scalar_one_or_none()
    if not option:
        raise HTTPException(status_code=404, detail="Variant topilmadi yoki so'rovnoma faol emas")

    option.vote_count += 1
    await db.commit()
    return {"message": "Vote recorded"}


@router.post("/{poll_id}/close")
async def close_poll(
    poll_id: str,
    current_user: User = Depends(require_investigator_or_above),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Poll).where(Poll.id == uuid.UUID(poll_id)))
    poll = result.scalar_one_or_none()
    if not poll:
        raise HTTPException(status_code=404, detail="So'rovnoma topilmadi")

    poll.status = PollStatus.CLOSED
    poll.closed_at = datetime.now(timezone.utc)
    await db.commit()
    return {"message": "Poll closed"}
