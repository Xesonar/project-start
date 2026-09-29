from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.application import Application
from app.models.enums import ApplicationStatus, ProjectDifficulty, ProjectFormat, ProjectStatus
from app.models.project import Project, ProjectRole, ProjectSkill
from app.models.skill import UserSkill
from app.models.user import User
from app.schemas.project import ProjectListItem, ProjectRead, ProjectRecommendation
from app.services.recommendation import (
    ScoredProject,
    explain_top_recommendations,
    recommend_projects,
    score_project,
)

router = APIRouter(tags=["projects"])


def _fallback_reason(item) -> str:
    strongest = max(item.breakdown, key=item.breakdown.get)
    labels = {
        "skills": "нужные навыки ближе всего к твоему профилю",
        "role": "выбранная роль совпадает с твоим направлением",
        "specialty": "тематика проекта подходит к твоей специальности",
        "difficulty": "уровень проекта соответствует твоей текущей подготовке",
    }
    return f"Подбор рассчитан по анкете: {labels[strongest]}."


def _project_query():
    return select(Project).options(
        selectinload(Project.organization),
        selectinload(Project.roles),
        selectinload(Project.required_skills).selectinload(ProjectSkill.skill),
    )


def _attach_application_counts(db: Session, projects: list[Project]) -> None:
    """Attach public, aggregate interest signals without exposing applicants."""
    project_ids = [project.id for project in projects]
    if not project_ids:
        return
    active_statuses = [
        ApplicationStatus.pending,
        ApplicationStatus.accepted,
        ApplicationStatus.leave_requested,
    ]
    project_counts = dict(
        db.execute(
            select(Application.project_id, func.count(func.distinct(Application.user_id)))
            .where(
                Application.project_id.in_(project_ids),
                Application.status.in_(active_statuses),
            )
            .group_by(Application.project_id)
        ).all()
    )
    role_counts = dict(
        db.execute(
            select(Application.project_role_id, func.count(Application.id))
            .where(
                Application.project_id.in_(project_ids),
                Application.status.in_(active_statuses),
            )
            .group_by(Application.project_role_id)
        ).all()
    )
    for project in projects:
        # These transient attributes are deliberately not stored: the counts
        # remain accurate at read time and never expose a student's identity.
        project.applicants_count = project_counts.get(project.id, 0)
        for role in project.roles:
            role.applicants_count = role_counts.get(role.id, 0)


@router.get("/projects", response_model=list[ProjectListItem])
def list_projects(
    difficulty: ProjectDifficulty | None = None,
    project_format: ProjectFormat | None = Query(default=None, alias="format"),
    skill_id: list[int] | None = Query(default=None),
    role: str | None = None,
    sort: Literal["newest", "difficulty"] = "newest",
    db: Session = Depends(get_db),
) -> list[Project]:
    query = _project_query().where(Project.status == ProjectStatus.open)

    if difficulty is not None:
        query = query.where(Project.difficulty == difficulty)
    if project_format is not None:
        query = query.where(Project.format == project_format)
    if skill_id:
        query = query.join(ProjectSkill).where(ProjectSkill.skill_id.in_(skill_id))
    if role:
        query = query.join(ProjectRole).where(ProjectRole.title.ilike(f"%{role}%"))

    query = query.distinct()
    if sort == "difficulty":
        # Postgres native enums sort by declaration order, which matches
        # ProjectDifficulty's definition order (beginner < intermediate <
        # advanced) — no need for an explicit CASE expression. A CASE here
        # would also break SELECT DISTINCT (Postgres requires ORDER BY
        # expressions to appear in the select list).
        query = query.order_by(Project.difficulty, Project.created_at.desc())
    else:
        query = query.order_by(Project.created_at.desc())
    projects = list(db.scalars(query))
    _attach_application_counts(db, projects)
    return projects


@router.get("/projects/recommended", response_model=list[ProjectRecommendation])
def list_recommended_projects(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ProjectRecommendation]:
    scored, user_skills = recommend_projects(db, user_id=user.id, profile=user.profile)
    _attach_application_counts(db, [item.project for item in scored])
    novice_profile = not user_skills or max(item.rating for item in user_skills) <= 1
    reasons = {} if novice_profile else explain_top_recommendations(
        scored, user.profile, user_skills
    )
    return [
        ProjectRecommendation.model_validate(item.project, from_attributes=True).model_copy(
            update={
                "score": round(item.score, 4),
                "breakdown": {key: round(value, 4) for key, value in item.breakdown.items()},
                "reason": (
                    "Начальный проект без завышенных требований — можно учиться прямо в процессе."
                    if novice_profile
                    else reasons.get(item.project.id) or _fallback_reason(item)
                ),
            }
        )
        for item in scored
    ]


@router.get(
    "/projects/{project_id}/recommendation",
    response_model=ProjectRecommendation,
)
def get_project_recommendation(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectRecommendation:
    """Return the same score used by the ranking for one project.

    This endpoint deliberately does not apply the top-10 or open-project
    filters. A project opened from search, an old application or a MAX deep
    link must show the exact same formula as its catalogue card.
    """
    project = db.scalar(
        _project_query().where(
            Project.id == project_id,
            Project.status != ProjectStatus.draft,
        )
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Проект не найден")
    _attach_application_counts(db, [project])

    user_skills = list(
        db.scalars(select(UserSkill).where(UserSkill.user_id == user.id))
    )
    rating_by_skill_id = {item.skill_id: item.rating for item in user_skills}
    score, breakdown = score_project(project, rating_by_skill_id, user.profile)
    scored = ScoredProject(project=project, score=score, breakdown=breakdown)
    return ProjectRecommendation.model_validate(project, from_attributes=True).model_copy(
        update={
            "score": round(score, 4),
            "breakdown": {key: round(value, 4) for key, value in breakdown.items()},
            "reason": _fallback_reason(scored),
        }
    )


@router.get("/projects/{project_id}", response_model=ProjectRead)
def get_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    # Drafts are visible only through the protected admin API. Completed
    # projects stay readable for applications, teams and portfolio history.
    project = db.scalar(
        _project_query().where(
            Project.id == project_id,
            Project.status != ProjectStatus.draft,
        )
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Проект не найден")
    _attach_application_counts(db, [project])
    return project
