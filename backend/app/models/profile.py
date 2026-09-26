from sqlalchemy import Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ExperienceLevel


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    university: Mapped[str | None] = mapped_column(String(255), default=None)
    course: Mapped[int | None] = mapped_column(Integer, default=None)
    specialty: Mapped[str | None] = mapped_column(String(255), default=None)
    about: Mapped[str | None] = mapped_column(Text, default=None)
    experience_level: Mapped[ExperienceLevel | None] = mapped_column(
        Enum(ExperienceLevel, name="experience_level"), default=None
    )
    portfolio_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    github_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    goal: Mapped[str | None] = mapped_column(String(255), default=None)
    # Free-text role the student wants to try (e.g. "Frontend developer"),
    # matched loosely against ProjectRole.title for recommendation scoring.
    preferred_role: Mapped[str | None] = mapped_column(String(255), default=None)

    user: Mapped["User"] = relationship(back_populates="profile")
