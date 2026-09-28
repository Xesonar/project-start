"""Deterministic, explainable project recommendation scoring.

score = 0.4 * skill_overlap + 0.25 * role_match + 0.15 * difficulty_match + 0.2 * interest_match

The formula owns the order. The optional LLM only turns the measured profile
and score breakdown into a short explanation; it never changes the ranking.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import ProjectDifficulty, ProjectStatus
from app.models.profile import StudentProfile
from app.models.project import Project, ProjectSkill
from app.models.skill import UserSkill
from app.services.ai_client import explain_recommendations

_DIFFICULTY_ORDER = {"beginner": 0, "intermediate": 1, "advanced": 2}
_DIFFICULTY_MATCH_BY_DISTANCE = {0: 1.0, 1: 0.5}

_WEIGHT_SKILL_OVERLAP = 0.4
_WEIGHT_ROLE_MATCH = 0.25
_WEIGHT_DIFFICULTY_MATCH = 0.15
_WEIGHT_INTEREST_MATCH = 0.2


@dataclass
class ScoredProject:
    project: Project
    score: float
    breakdown: dict[str, float]


_REQUIRED_RATING = {"beginner": 2, "intermediate": 3, "advanced": 4}


def _skill_overlap(project: Project, user_rating_by_skill_id: dict[int, int]) -> float:
    if not project.required_skills:
        # No declared requirements means there is no skill gap. Keep this in
        # sync with the frontend match ring, which also treats it as 100%.
        return 1.0
    credit = 0.0
    for required in project.required_skills:
        rating = user_rating_by_skill_id.get(required.skill_id, 0)
        threshold = _REQUIRED_RATING[required.required_level.value]
        credit += min(rating / threshold, 1.0)
    return credit / len(project.required_skills)


def _role_match(project: Project, preferred_role: str | None) -> float:
    if not preferred_role:
        return 0.0
    preferred = preferred_role.strip().lower()
    if not preferred:
        return 0.0
    for role in project.roles:
        title = role.title.lower()
        if preferred in title or title in preferred:
            return 1.0
    return 0.0


def _difficulty_match(project: Project, experience_level: str | None) -> float:
    if not experience_level:
        return 0.0
    distance = abs(_DIFFICULTY_ORDER[project.difficulty.value] - _DIFFICULTY_ORDER[experience_level])
    return _DIFFICULTY_MATCH_BY_DISTANCE.get(distance, 0.0)


def _interest_match(project: Project, specialty: str | None) -> float:
    if not specialty or not project.required_skills:
        return 0.0
    matching = sum(1 for ps in project.required_skills if ps.skill.category == specialty)
    return matching / len(project.required_skills)


def score_project(
    project: Project,
    user_rating_by_skill_id: dict[int, int],
    profile: StudentProfile | None,
) -> tuple[float, dict[str, float]]:
    experience_level = profile.experience_level.value if profile and profile.experience_level else None
    breakdown = {
        "skills": _WEIGHT_SKILL_OVERLAP * _skill_overlap(project, user_rating_by_skill_id),
        "role": _WEIGHT_ROLE_MATCH
        * _role_match(project, profile.preferred_role if profile else None),
        "specialty": _WEIGHT_INTEREST_MATCH
        * _interest_match(project, profile.specialty if profile else None),
        "difficulty": _WEIGHT_DIFFICULTY_MATCH
        * _difficulty_match(project, experience_level),
    }
    return sum(breakdown.values()), breakdown


_RATING_LABELS = {
    1: "слышал(а)",
    2: "изучал(а)",
    3: "применял(а) в проекте",
    4: "уверенно применял(а) в нескольких проектах",
}


def _profile_summary(profile: StudentProfile | None, user_skills: list[UserSkill]) -> str:
    if profile is None:
        return "Профиль не заполнен."
    parts = [
        f"Специализация: {profile.specialty or 'не указана'}",
        f"Уровень: {profile.experience_level.value if profile.experience_level else 'не указан'}",
        f"Интересующая роль: {profile.preferred_role or 'не указана'}",
        f"Цель: {profile.goal or 'не указана'}",
        "Самооценка навыков: "
        + (
            ", ".join(
                f"{item.skill.name} — {_RATING_LABELS.get(item.rating, item.level.value)}"
                for item in user_skills
            )
            or "не указана"
        ),
    ]
    return "; ".join(parts)


def explain_top_recommendations(
    scored: list[ScoredProject],
    profile: StudentProfile | None,
    user_skills: list[UserSkill],
    top_n: int = 5,
) -> dict[int, str]:
    """Explains the deterministic top results without changing their order."""
    top = scored[:top_n]
    if not top:
        return {}

    candidates = [
        {
            "project_id": item.project.id,
            "title": item.project.title,
            "difficulty": item.project.difficulty.value,
            "roles": [role.title for role in item.project.roles],
            "skills": [ps.skill.name for ps in item.project.required_skills],
            "score_percent": round(item.score * 100),
            "score_breakdown": {
                key: round(value * 100) for key, value in item.breakdown.items()
            },
        }
        for item in top
    ]

    items = explain_recommendations(_profile_summary(profile, user_skills), candidates)
    if not items:
        return {}
    return {item["project_id"]: item["reason"] for item in items}


def recommend_projects(
    db: Session, user_id: int, profile: StudentProfile | None, limit: int = 10
) -> tuple[list[ScoredProject], list[UserSkill]]:
    projects = list(
        db.scalars(
            select(Project)
            .where(Project.status == ProjectStatus.open)
            .options(
                selectinload(Project.organization),
                selectinload(Project.roles),
                selectinload(Project.required_skills).selectinload(ProjectSkill.skill),
            )
            .order_by(Project.created_at.desc(), Project.id.desc())
        )
    )
    user_skills = list(
        db.scalars(
            select(UserSkill)
            .where(UserSkill.user_id == user_id)
            .options(selectinload(UserSkill.skill))
        )
    )
    user_rating_by_skill_id = {item.skill_id: item.rating for item in user_skills}
    novice_profile = not user_skills or max(item.rating for item in user_skills) <= 1

    if novice_profile:
        projects = [
            project for project in projects if project.difficulty == ProjectDifficulty.beginner
        ]
    elif profile and profile.experience_level == ProjectDifficulty.beginner:
        # A few strong matching keywords must not promote an advanced project
        # to the top for a beginner. Intermediate projects may still be shown
        # as a stretch option; advanced ones are deliberately hidden.
        projects = [
            project
            for project in projects
            if project.difficulty != ProjectDifficulty.advanced
        ]

    scored = []
    for project in projects:
        score, breakdown = score_project(project, user_rating_by_skill_id, profile)
        scored.append(ScoredProject(project=project, score=score, breakdown=breakdown))
    scored.sort(key=lambda item: item.score, reverse=True)
    return scored[:limit], user_skills
