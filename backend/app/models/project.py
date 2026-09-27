from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ProjectDifficulty, ProjectFormat, ProjectStatus, SkillLevel


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    organization_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[ProjectDifficulty] = mapped_column(
        Enum(ProjectDifficulty, name="project_difficulty")
    )
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"), default=ProjectStatus.open
    )
    # Human-readable duration/deadline as shown to students (e.g. "14 дней") —
    # a free-text field is enough for demo data, no date arithmetic needed.
    deadline: Mapped[str] = mapped_column(String(100))
    format: Mapped[ProjectFormat] = mapped_column(Enum(ProjectFormat, name="project_format"))
    participant_limit: Mapped[int] = mapped_column(Integer)
    expected_result: Mapped[str] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    team_chat_url: Mapped[str | None] = mapped_column(String(1024), default=None)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    organization: Mapped["Organization"] = relationship()
    roles: Mapped[list["ProjectRole"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    required_skills: Mapped[list["ProjectSkill"]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectRole(Base):
    __tablename__ = "project_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, default=None)
    slots: Mapped[int] = mapped_column(Integer, default=1)

    project: Mapped["Project"] = relationship(back_populates="roles")


class ProjectSkill(Base):
    __tablename__ = "project_skills"

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skills.id", ondelete="CASCADE"), primary_key=True
    )
    required_level: Mapped[SkillLevel] = mapped_column(
        Enum(SkillLevel, name="skill_level")
    )

    project: Mapped["Project"] = relationship(back_populates="required_skills")
    skill: Mapped["Skill"] = relationship()
