from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.project import ProjectListItem


class ProjectCompleteRequest(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str = Field(min_length=3, max_length=5000)
    result_url: str | None = Field(default=None, max_length=1024)

    @field_validator("result_url")
    @classmethod
    def validate_result_url(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith(("https://", "http://")):
            raise ValueError("result_url must use http or https")
        return value


class ProjectResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str
    description: str
    result_url: str | None
    completed_at: datetime


class ConfirmationCreate(BaseModel):
    user_id: int
    role: str = Field(min_length=2, max_length=255)
    contribution: str | None = Field(default=None, max_length=2000)


class ProjectFinalizeRequest(BaseModel):
    result: ProjectCompleteRequest
    confirmations: list[ConfirmationCreate] = Field(min_length=1, max_length=100)


class ConfirmationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    role: str
    contribution: str | None
    confirmed_by: str
    confirmed_at: datetime


class PortfolioItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project: ProjectListItem
    result: ProjectResultRead | None
    confirmation: ConfirmationRead


class SkillPublic(BaseModel):
    name: str
    category: str
    level: str


class PortfolioPublicItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_title: str
    organization: str
    role: str
    contribution: str | None
    result: ProjectResultRead | None
    confirmed_at: datetime


class PortfolioPublic(BaseModel):
    """Everything a recruiter/teacher sees on /p/<slug>. No contacts."""

    name: str
    avatar_url: str | None = None
    specialty: str | None = None
    experience_level: str | None = None
    preferred_role: str | None = None
    skills: list[SkillPublic] = Field(default_factory=list)
    projects: list[PortfolioPublicItem] = Field(default_factory=list)


class PortfolioLinkResponse(BaseModel):
    slug: str
