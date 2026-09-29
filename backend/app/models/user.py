from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Enum, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    max_user_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    avatar_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"), default=UserRole.student
    )
    # Public portfolio handle (/p/<slug>). Null until the student explicitly
    # creates a shareable link — portfolio data is never public by default.
    portfolio_slug: Mapped[str | None] = mapped_column(
        String(64), unique=True, index=True, default=None
    )
    # Rewards are granted only when an organizer verifies a completed project.
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    profile: Mapped["StudentProfile | None"] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    skills: Mapped[list["UserSkill"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def level(self) -> int:
        from app.services.progression import level_for_xp

        return level_for_xp(self.xp)

    @property
    def next_level_xp(self) -> int | None:
        from app.services.progression import next_level_xp

        return next_level_xp(self.xp)
