from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.enums import ExperienceLevel, SkillLevel, UserRole
from app.models.profile import StudentProfile
from app.models.skill import Skill, UserSkill
from app.models.user import User


def upsert_max_user(
    db: Session,
    *,
    max_user_id: int,
    first_name: str | None = None,
    last_name: str | None = None,
    username: str | None = None,
    avatar_url: str | None = None,
    is_demo: bool = False,
) -> User:
    """Creates or updates a User from MAX-provided profile fields.

    Shared by /auth/max (trust comes from HMAC-validated initData) and the
    bot webhook (trust comes from the webhook secret instead) — both hand
    MAX user fields to the same upsert so there's one place that decides
    what a "name" is.
    """
    name = (
        " ".join(str(part).strip() for part in (first_name, last_name) if part).strip()
        or (str(username).strip() if username else "")
        or f"user{max_user_id}"
    )[:255]
    safe_avatar_url = str(avatar_url)[:1024] if avatar_url is not None else None

    user = db.scalar(select(User).where(User.max_user_id == max_user_id))
    if user is None:
        user = User(
            max_user_id=max_user_id,
            name=name,
            avatar_url=safe_avatar_url,
            role=UserRole.student,
            is_demo=is_demo,
        )
        db.add(user)
    else:
        user.name = name
        user.is_demo = is_demo
        if avatar_url is not None:
            user.avatar_url = safe_avatar_url
    db.commit()
    db.refresh(user)
    return user


_DEMO_PROFILE = {
    "specialty": "Разработка",
    "experience_level": ExperienceLevel.beginner,
    "preferred_role": "Frontend developer",
    "goal": "Найти первый проект",
}

_DEMO_SKILL_NAMES = ("JavaScript", "HTML/CSS", "React", "Figma", "Git", "Python")


def cleanup_stale_demo_users(db: Session, *, keep_max_user_id: int) -> None:
    """Bound passwordless demo data without touching the seeded showcase user."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.demo_user_ttl_days)
    db.execute(
        delete(User).where(
            User.is_demo.is_(True),
            User.max_user_id != settings.demo_max_user_id,
            User.max_user_id != keep_max_user_id,
            User.created_at < cutoff,
        )
    )


def ensure_demo_user(
    db: Session,
    *,
    max_user_id: int | None = None,
    skill_names: tuple[str, ...] = (),
) -> User:
    """Idempotently creates the demo student used by POST /auth/demo.

    The profile is pre-filled so a first-time visitor lands straight on the
    personalised recommendation screen instead of an empty onboarding —
    the strongest single "wow" moment in the demo.
    """
    user = upsert_max_user(
        db,
        max_user_id=max_user_id if max_user_id is not None else settings.demo_max_user_id,
        first_name=settings.demo_user_name,
        is_demo=True,
    )

    if user.profile is None:
        db.add(StudentProfile(user_id=user.id, **_DEMO_PROFILE))
        db.flush()

    existing_skill_ids = {us.skill_id for us in user.skills}
    if skill_names:
        skills = {
            skill.name: skill
            for skill in db.scalars(select(Skill).where(Skill.name.in_(skill_names)))
        }
        for name in skill_names:
            skill = skills.get(name)
            if skill is not None and skill.id not in existing_skill_ids:
                db.add(
                    UserSkill(
                        user_id=user.id,
                        skill_id=skill.id,
                        level=SkillLevel.beginner,
                        rating=2,
                    )
                )
        db.flush()

    db.commit()
    db.refresh(user)
    return user


def ensure_demo_portfolio_confirmation(db: Session, user: User) -> None:
    """Copies the seeded demo portfolio entry to an isolated demo visitor."""
    from app.models.project import Project
    from app.models.result import ParticipationConfirmation

    project = db.scalar(
        select(Project).where(Project.title == "Демо: навигатор по мероприятиям университета")
    )
    if project is None:
        return

    existing = db.scalar(
        select(ParticipationConfirmation).where(
            ParticipationConfirmation.user_id == user.id,
            ParticipationConfirmation.project_id == project.id,
        )
    )
    if existing is not None:
        return

    db.add(
        ParticipationConfirmation(
            project_id=project.id,
            user_id=user.id,
            confirmed_by="Университетский проектный офис",
            role="Frontend developer",
            contribution=(
                "Собрал интерфейс мини-приложения: карточки мероприятий, "
                "фильтры и навигация."
            ),
        )
    )
    db.commit()
