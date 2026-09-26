from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ProjectResult(Base):
    __tablename__ = "project_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), unique=True
    )
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    result_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship()


class ParticipationConfirmation(Base):
    __tablename__ = "participation_confirmations"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_confirmation_per_project_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    confirmed_by: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(255))
    contribution: Mapped[str | None] = mapped_column(Text, default=None)
    confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship()
    user: Mapped["User"] = relationship()
