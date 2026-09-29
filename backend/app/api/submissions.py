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


def _require_active_membership(db: Session, *, project_id: int, user_id: int) -> Project:
    project = db.scalar(
        select(Project).where(Project.id == project_id).with_for_update()
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Проект не найден")
    if project.status == ProjectStatus.completed:
        raise HTTPException(status.HTTP_409_CONFLICT, "В завершённом проекте сдачи заблокированы")
    if project.status != ProjectStatus.in_progress:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Сдача откроется после того, как организатор запустит проект",
        )
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
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Вы не состоите в активной команде проекта")
    return project


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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сдача не найдена")
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
        ).with_for_update()
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
