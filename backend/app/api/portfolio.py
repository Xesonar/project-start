from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.project import Project, ProjectSkill
from app.models.result import ParticipationConfirmation, ProjectResult
from app.models.user import User
from app.schemas.portfolio import (
    ConfirmationRead,
    PortfolioItem,
    PortfolioLinkResponse,
    PortfolioPublic,
    ProjectResultRead,
)
from app.schemas.project import ProjectListItem
from app.services.portfolio import build_public_portfolio, ensure_portfolio_slug

router = APIRouter(tags=["portfolio"])


@router.get("/me/portfolio", response_model=list[PortfolioItem])
def get_my_portfolio(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[PortfolioItem]:
    confirmations = list(
        db.scalars(
            select(ParticipationConfirmation)
            .where(ParticipationConfirmation.user_id == user.id)
            .options(
                selectinload(ParticipationConfirmation.project).selectinload(Project.organization),
                selectinload(ParticipationConfirmation.project).selectinload(Project.roles),
                selectinload(ParticipationConfirmation.project)
                .selectinload(Project.required_skills)
                .selectinload(ProjectSkill.skill),
            )
            .order_by(ParticipationConfirmation.confirmed_at.desc())
        )
    )

    project_ids = [c.project_id for c in confirmations]
    results_by_project = {
        r.project_id: r
        for r in db.scalars(
            select(ProjectResult).where(ProjectResult.project_id.in_(project_ids))
        )
    } if project_ids else {}

    items = []
    for confirmation in confirmations:
        result = results_by_project.get(confirmation.project_id)
        items.append(
            PortfolioItem(
                project=ProjectListItem.model_validate(confirmation.project, from_attributes=True),
                result=ProjectResultRead.model_validate(result, from_attributes=True)
                if result
                else None,
                confirmation=ConfirmationRead.model_validate(confirmation, from_attributes=True),
            )
        )
    return items


@router.post("/me/portfolio/link", response_model=PortfolioLinkResponse)
def create_my_portfolio_link(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> PortfolioLinkResponse:
    """Turns the student's confirmed experience into a shareable public page.

    Deliberately explicit: nothing is public until the student asks for a
    link. Calling it again returns the same slug.
    """
    return ensure_portfolio_slug(db, user)


@router.get("/p/{slug}", response_model=PortfolioPublic)
def get_public_portfolio(slug: str, db: Session = Depends(get_db)) -> PortfolioPublic:
    """Public portfolio — no auth, no contact details, recruiter-friendly."""
    portfolio = build_public_portfolio(db, slug)
    if portfolio is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Portfolio not found")
    return portfolio
