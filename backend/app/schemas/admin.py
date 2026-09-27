from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ApplicationStatus
from app.schemas.project import ProjectRoleRead
from app.schemas.user import ProfileRead


class ApplicantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar_url: str | None
    profile: ProfileRead | None


class AdminApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ApplicationStatus
    message: str | None
    decision_note: str | None
    created_at: datetime
    project_role: ProjectRoleRead
    user: ApplicantRead


class ApplicationStatusUpdate(BaseModel):
    status: Literal["accepted", "rejected"]
    note: str | None = Field(default=None, max_length=2000)


class AdminMessageCreate(BaseModel):
    text: str = Field(min_length=1, max_length=2000)


class AdminMessageResult(BaseModel):
    delivered: bool


class ProjectCommunicationRead(BaseModel):
    team_chat_url: str | None


class ProjectCommunicationUpdate(BaseModel):
    team_chat_url: str | None = Field(default=None, max_length=1024)

    @field_validator("team_chat_url")
    @classmethod
    def validate_team_chat_url(cls, value: str | None) -> str | None:
        value = value.strip() if value else None
        if value is not None and not value.startswith("https://max.ru/"):
            raise ValueError("team_chat_url must start with https://max.ru/")
        return value


class AdminMetricsRead(BaseModel):
    students: int
    assessed_students: int
    applications: int
    accepted_applications: int
    completed_projects: int
    confirmed_participations: int
    assessment_rate: float
    acceptance_rate: float
