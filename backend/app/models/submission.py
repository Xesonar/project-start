from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ProjectSubmissionStatus


class ProjectSubmission(Base):
    __tablename__ = "project_submissions"
    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_submission_project_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    summary: Mapped[str] = mapped_column(Text)
    result_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    status: Mapped[ProjectSubmissionStatus] = mapped_column(
        Enum(ProjectSubmissionStatus, name="project_submission_status"),
        default=ProjectSubmissionStatus.submitted,
    )
    review_note: Mapped[str | None] = mapped_column(Text, default=None)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    project: Mapped["Project"] = relationship()
    user: Mapped["User"] = relationship()
