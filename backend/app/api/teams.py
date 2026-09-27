from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.project import Project, ProjectSkill
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.team import TeamRead

router = APIRouter(tags=["teams"])


@router.get("/me/team", response_model=TeamRead)
def get_my_team(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TeamRead:
    team_id = db.scalar(
        select(TeamMember.team_id)
        .join(Team, Team.id == TeamMember.team_id)
        .where(TeamMember.user_id == user.id, Team.status == "active")
        .order_by(TeamMember.joined_at.desc(), TeamMember.team_id.desc())
    )
    if team_id is None:
        team_id = db.scalar(
            select(TeamMember.team_id)
            .join(Team, Team.id == TeamMember.team_id)
            .where(TeamMember.user_id == user.id, Team.status == "completed")
            .order_by(TeamMember.joined_at.desc(), TeamMember.team_id.desc())
        )
    if team_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You are not part of a team yet")

    team = db.scalar(
        select(Team)
        .where(Team.id == team_id)
        .options(
            selectinload(Team.project).selectinload(Project.organization),
            selectinload(Team.project).selectinload(Project.roles),
            selectinload(Team.project)
            .selectinload(Project.required_skills)
            .selectinload(ProjectSkill.skill),
            selectinload(Team.members).selectinload(TeamMember.user),
        )
    )
    response = TeamRead.model_validate(team)
    return response.model_copy(update={"team_chat_url": team.project.team_chat_url})
