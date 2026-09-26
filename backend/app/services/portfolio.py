"""Shareable public portfolio.

A student's portfolio is private until they explicitly create a link. This
module owns slug generation (stable, readable, collision-free) and the
public read model — everything an outsider needs to verify the student's
experience, with no contact details.
"""

import re
import secrets

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.project import Project
from app.models.skill import UserSkill
from app.models.result import ParticipationConfirmation, ProjectResult
from app.models.user import User
from app.schemas.portfolio import (
    PortfolioLinkResponse,
    PortfolioPublic,
    PortfolioPublicItem,
    SkillPublic,
)

# Compact transliteration — keeps Russian names readable in a URL without a
# dependency, and degrades to "student" for anything non-latin.
_TRANSLIT = str.maketrans({
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
    "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
})
_MAX_ATTEMPTS = 10


def _slug_base(name: str) -> str:
    transliterated = name.lower().translate(_TRANSLIT)
    base = re.sub(r"[^a-z0-9]+", "-", transliterated).strip("-")
    return base or "student"


def _generate_slug(db: Session, base: str) -> str:
    for _ in range(_MAX_ATTEMPTS):
        candidate = f"{base}-{secrets.token_hex(3)}"
        exists = db.scalar(
            select(User.id).where(User.portfolio_slug == candidate)
        )
        if exists is None:
            return candidate
    raise RuntimeError("could not generate a unique portfolio slug")


def ensure_portfolio_slug(db: Session, user: User) -> PortfolioLinkResponse:
    """Creates the student's shareable slug, or returns the existing one."""
    if not user.portfolio_slug:
        user.portfolio_slug = _generate_slug(db, _slug_base(user.name))
        db.commit()
        db.refresh(user)
    return PortfolioLinkResponse(slug=user.portfolio_slug)


def build_public_portfolio(db: Session, slug: str) -> PortfolioPublic | None:
    """Public portfolio view, or None if no such slug exists."""
    user = db.scalar(
        select(User)
        .where(User.portfolio_slug == slug)
        .options(
            selectinload(User.profile),
            selectinload(User.skills).selectinload(UserSkill.skill),
        )
    )
    if user is None:
        return None

    confirmations = list(
        db.scalars(
            select(ParticipationConfirmation)
            .where(ParticipationConfirmation.user_id == user.id)
            .options(
                selectinload(ParticipationConfirmation.project)
                .selectinload(Project.organization),
            )
            .order_by(ParticipationConfirmation.confirmed_at.desc())
        )
    )
    results_by_project = {
        r.project_id: r
        for r in db.scalars(
            select(ProjectResult).where(
                ProjectResult.project_id.in_([c.project_id for c in confirmations])
            )
        )
    } if confirmations else {}

    return PortfolioPublic(
        name=user.name,
        avatar_url=user.avatar_url,
        specialty=user.profile.specialty if user.profile else None,
        experience_level=(
            user.profile.experience_level.value if user.profile and user.profile.experience_level else None
        ),
        preferred_role=user.profile.preferred_role if user.profile else None,
        skills=[
            SkillPublic(
                name=us.skill.name, category=us.skill.category, level=us.level.value
            )
            for us in user.skills
        ],
        projects=[
            PortfolioPublicItem(
                project_title=c.project.title,
                organization=c.project.organization.name,
                role=c.role,
                contribution=c.contribution,
                result=results_by_project.get(c.project_id),
                confirmed_at=c.confirmed_at,
            )
            for c in confirmations
        ],
    )
