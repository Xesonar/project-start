from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import ProjectDifficulty, ProjectFormat, ProjectStatus, SkillLevel
from app.schemas.user import SkillRead


class ProjectRoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    slots: int


class ProjectRoleCreate(BaseModel):
    title: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=2000)
    slots: int = Field(default=1, ge=1, le=100)


class ProjectSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill: SkillRead
    required_level: SkillLevel


class ProjectSkillCreate(BaseModel):
    skill_id: int
    required_level: SkillLevel = SkillLevel.beginner


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    type: str
    verified: bool


class ProjectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    difficulty: ProjectDifficulty
    status: ProjectStatus
    format: ProjectFormat
    deadline: str
    participant_limit: int
    organization: OrganizationRead


class ProjectRead(ProjectListItem):
    expected_result: str
    roles: list[ProjectRoleRead]
    required_skills: list[ProjectSkillRead]


class ProjectRecommendation(ProjectListItem):
    score: float = 0.0
    breakdown: dict[str, float] = Field(default_factory=dict)
    # Populated by the optional LLM explanation layer; stays None
    # when that layer is skipped or fails, so the UI never depends on it.
    reason: str | None = None


class ProjectCreate(BaseModel):
    organization_id: int
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10, max_length=10000)
    difficulty: ProjectDifficulty
    status: Literal[ProjectStatus.draft, ProjectStatus.open] = ProjectStatus.open
    deadline: str = Field(min_length=1, max_length=100)
    format: ProjectFormat
    participant_limit: int = Field(ge=1, le=100)
    expected_result: str = Field(min_length=3, max_length=5000)
    roles: list[ProjectRoleCreate] = Field(min_length=1, max_length=20)
    required_skills: list[ProjectSkillCreate] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_role_capacity(self):
        normalized_titles = [role.title.strip().casefold() for role in self.roles]
        if len(normalized_titles) != len(set(normalized_titles)):
            raise ValueError("Role titles must be unique")
        if sum(role.slots for role in self.roles) < self.participant_limit:
            raise ValueError("Role slots must cover the participant limit")
        return self
