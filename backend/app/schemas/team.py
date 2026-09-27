from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.project import ProjectListItem


class TeamMemberUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar_url: str | None


class TeamMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: TeamMemberUserRead
    role_title: str
    joined_at: datetime


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    project: ProjectListItem
    members: list[TeamMemberRead]
    team_chat_url: str | None = None
