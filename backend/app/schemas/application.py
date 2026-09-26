from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ApplicationStatus
from app.schemas.project import ProjectListItem, ProjectRoleRead


class ApplicationCreate(BaseModel):
    project_role_id: int
    message: str | None = Field(default=None, max_length=2000)


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: ApplicationStatus
    message: str | None
    created_at: datetime
    project: ProjectListItem
    project_role: ProjectRoleRead
