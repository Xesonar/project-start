"""Bounded, per-conversation context for the MAX text assistant."""

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.bot_conversation import BotConversationMessage

MEMORY_LIMIT = 10


def recent_messages(db: Session, conversation_key: str) -> list[BotConversationMessage]:
    rows = list(
        db.scalars(
            select(BotConversationMessage)
            .where(BotConversationMessage.conversation_key == conversation_key)
            .order_by(BotConversationMessage.created_at.desc(), BotConversationMessage.id.desc())
            .limit(MEMORY_LIMIT)
        )
    )
    return list(reversed(rows))


def remember(
    db: Session,
    *,
    conversation_key: str,
    role: str,
    text: str,
    sender_max_user_id: int | None = None,
) -> None:
    db.add(
        BotConversationMessage(
            conversation_key=conversation_key,
            role=role,
            text=text[:4000],
            sender_max_user_id=sender_max_user_id,
        )
    )
    db.flush()
    stale_ids = list(
        db.scalars(
            select(BotConversationMessage.id)
            .where(BotConversationMessage.conversation_key == conversation_key)
            .order_by(BotConversationMessage.created_at.desc(), BotConversationMessage.id.desc())
            .offset(MEMORY_LIMIT)
        )
    )
    if stale_ids:
        db.execute(delete(BotConversationMessage).where(BotConversationMessage.id.in_(stale_ids)))
    db.commit()


def clear(db: Session, conversation_key: str) -> None:
    db.execute(
        delete(BotConversationMessage).where(
            BotConversationMessage.conversation_key == conversation_key
        )
    )
    db.commit()
