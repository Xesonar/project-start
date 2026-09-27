from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.enums import ProjectStatus, ProjectSubmissionStatus
from app.models.project import Project
from app.models.submission import ProjectSubmission
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.submission import SubmissionCreate, SubmissionRead

router = APIRouter(tags=["submissions"])


def _require_active_membership(db: Session, *, project_id: int, user_id: int) -> None:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if project.status == ProjectStatus.completed:
        raise HTTPException(status.HTTP_409_CONFLICT, "Completed project submissions are locked")
    membership = db.scalar(
        select(TeamMember)
        .join(Team, Team.id == TeamMember.team_id)
        .where(
            Team.project_id == project_id,
            Team.status == "active",
            TeamMember.user_id == user_id,
        )
    )
    if membership is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not an active team member")


@router.get(
    "/me/projects/{project_id}/submission",
    response_model=SubmissionRead,
)
def get_my_submission(
    project_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectSubmission:
    submission = db.scalar(
        select(ProjectSubmission).where(
            ProjectSubmission.project_id == project_id,
            ProjectSubmission.user_id == user.id,
        )
    )
    if submission is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Submission not found")
    return submission


@router.put(
    "/me/projects/{project_id}/submission",
    response_model=SubmissionRead,
)
def submit_project_result(
    project_id: int,
    payload: SubmissionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectSubmission:
    _require_active_membership(db, project_id=project_id, user_id=user.id)
    submission = db.scalar(
        select(ProjectSubmission).where(
            ProjectSubmission.project_id == project_id,
            ProjectSubmission.user_id == user.id,
        )
    )
    if submission is None:
        submission = ProjectSubmission(
            project_id=project_id,
            user_id=user.id,
            summary=payload.summary.strip(),
            result_url=payload.result_url,
        )
        db.add(submission)
    else:
        submission.summary = payload.summary.strip()
        submission.result_url = payload.result_url
        submission.status = ProjectSubmissionStatus.submitted
        submission.review_note = None
        submission.reviewed_at = None
        submission.submitted_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(submission)
    return submission
