from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

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
    created_at: datetime
    project_role: ProjectRoleRead
    user: ApplicantRead


class ApplicationStatusUpdate(BaseModel):
    status: Literal["accepted", "rejected"]


class AdminMetricsRead(BaseModel):
    students: int
    assessed_students: int
    applications: int
    accepted_applications: int
    completed_projects: int
    confirmed_participations: int
    assessment_rate: float
    acceptance_rate: float
