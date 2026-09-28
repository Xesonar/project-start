from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ApplicationStatus


class Application(Base):
    __tablename__ = "applications"
    __table_args__ = (
        Index(
            "uq_application_active_role",
            "user_id",
            "project_id",
            "project_role_id",
            unique=True,
            postgresql_where=text("status IN ('pending', 'accepted', 'leave_requested')"),
            sqlite_where=text("status IN ('pending', 'accepted', 'leave_requested')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    project_role_id: Mapped[int] = mapped_column(ForeignKey("project_roles.id", ondelete="CASCADE"))
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, name="application_status"), default=ApplicationStatus.pending
    )
    message: Mapped[str | None] = mapped_column(Text, default=None)
    decision_note: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    project: Mapped["Project"] = relationship()
    project_role: Mapped["ProjectRole"] = relationship()
    user: Mapped["User"] = relationship()
