from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import ProjectDifficulty, ProjectFormat, ProjectStatus
from app.models.project import Project, ProjectRole, ProjectSkill
from app.models.user import User
from app.schemas.project import ProjectListItem, ProjectRead, ProjectRecommendation
from app.services.recommendation import explain_top_recommendations, recommend_projects

router = APIRouter(tags=["projects"])


def _project_query():
    return select(Project).options(
        selectinload(Project.organization),
        selectinload(Project.roles),
        selectinload(Project.required_skills).selectinload(ProjectSkill.skill),
    )


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
    return list(db.scalars(query))


@router.get("/projects/recommended", response_model=list[ProjectRecommendation])
def list_recommended_projects(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[ProjectRecommendation]:
    scored, user_skills = recommend_projects(db, user_id=user.id, profile=user.profile)
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
                    else reasons.get(item.project.id)
                ),
            }
        )
        for item in scored
    ]


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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    return project
