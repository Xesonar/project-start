from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ExperienceLevel, SkillLevel


class SkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str


class UserSkillIn(BaseModel):
    skill_id: int
    level: SkillLevel
    rating: int | None = Field(default=None, ge=1, le=4)


class UserSkillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill: SkillRead
    level: SkillLevel
    rating: int


class ProfileUpdate(BaseModel):
    university: str | None = Field(default=None, max_length=255)
    course: int | None = Field(default=None, ge=1, le=10)
    specialty: str | None = Field(default=None, max_length=255)
    about: str | None = Field(default=None, max_length=2000)
    experience_level: ExperienceLevel | None = None
    portfolio_url: str | None = Field(default=None, max_length=1024)
    github_url: str | None = Field(default=None, max_length=1024)
    goal: str | None = Field(default=None, max_length=255)
    preferred_role: str | None = Field(default=None, max_length=255)


class ProfileRead(ProfileUpdate):
    model_config = ConfigDict(from_attributes=True)


class AssessmentUpdate(BaseModel):
    profile: ProfileUpdate
    skills: list[UserSkillIn] = Field(max_length=50)


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar_url: str | None
    role: str
    profile: ProfileRead | None
