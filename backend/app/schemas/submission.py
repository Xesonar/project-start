from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ProjectSubmissionStatus


class SubmissionCreate(BaseModel):
    summary: str = Field(min_length=10, max_length=3000)
    result_url: str | None = Field(default=None, max_length=1024)

    @field_validator("result_url")
    @classmethod
    def validate_result_url(cls, value: str | None) -> str | None:
        value = value.strip() if value else None
        if value is not None and not value.startswith(("https://", "http://")):
            raise ValueError("result_url must use http or https")
        return value


class SubmissionUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    avatar_url: str | None


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    user_id: int
    summary: str
    result_url: str | None
    status: ProjectSubmissionStatus
    review_note: str | None
    submitted_at: datetime
    reviewed_at: datetime | None


class AdminSubmissionRead(SubmissionRead):
    user: SubmissionUserRead


class SubmissionReview(BaseModel):
    status: Literal["approved", "revision_requested", "rejected"]
    note: str | None = Field(default=None, max_length=2000)
