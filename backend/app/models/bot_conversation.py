from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class BotConversationMessage(Base):
    """A short, scoped memory for the MAX assistant.

    A private dialog is keyed by its MAX user id; a group dialog is keyed by
    its MAX chat id.  The service trims each scope to a small fixed window, so
    this table is conversation context rather than an unbounded chat archive.
    """

    __tablename__ = "bot_conversation_messages"
    __table_args__ = (
        Index("ix_bot_conversation_scope_created", "conversation_key", "created_at", "id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conversation_key: Mapped[str] = mapped_column(String(80), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    sender_max_user_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
