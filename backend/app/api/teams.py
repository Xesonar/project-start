from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import case, select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.project import Project, ProjectSkill
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.team import TeamRead

router = APIRouter(tags=["teams"])


def _team_response(team: Team) -> TeamRead:
    response = TeamRead.model_validate(team)
    return response.model_copy(update={"team_chat_url": team.project.team_chat_url})


def _my_teams(db: Session, user_id: int) -> list[Team]:
    team_ids = list(
        db.scalars(
            select(TeamMember.team_id)
            .join(Team, Team.id == TeamMember.team_id)
            .where(
                TeamMember.user_id == user_id,
                Team.status.in_(["active", "completed"]),
            )
            .order_by(
                case((Team.status == "active", 0), else_=1),
                TeamMember.joined_at.desc(),
                TeamMember.team_id.desc(),
            )
        )
    )
    if not team_ids:
        return []
    teams = list(
        db.scalars(
            select(Team)
            .where(Team.id.in_(team_ids))
            .options(
                selectinload(Team.project).selectinload(Project.organization),
                selectinload(Team.project).selectinload(Project.roles),
                selectinload(Team.project)
                .selectinload(Project.required_skills)
                .selectinload(ProjectSkill.skill),
                selectinload(Team.members).selectinload(TeamMember.user),
            )
        )
    )
    by_id = {team.id: team for team in teams}
    return [by_id[team_id] for team_id in team_ids]


@router.get("/me/teams", response_model=list[TeamRead])
def get_my_teams(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[TeamRead]:
    return [_team_response(team) for team in _my_teams(db, user.id)]


@router.get("/me/team", response_model=TeamRead)
def get_my_team(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> TeamRead:
    teams = _my_teams(db, user.id)
    if not teams:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "You are not part of a team yet")
    return _team_response(teams[0])
