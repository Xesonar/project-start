from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.application import Application
from app.models.project import Project
from app.models.user import User
from app.schemas.application import ApplicationCreate, ApplicationRead
from app.services.applications import (
    ApplicationError,
    create_application as create_application_service,
    request_team_leave as request_team_leave_service,
    withdraw_application as withdraw_application_service,
)

router = APIRouter(tags=["applications"])


def _application_query():
    return select(Application).options(
        selectinload(Application.project).selectinload(Project.organization),
        selectinload(Application.project_role),
    )


@router.post(
    "/projects/{project_id}/applications",
    response_model=ApplicationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_application(
    project_id: int,
    payload: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Application:
    try:
        application = create_application_service(
            db,
            user_id=user.id,
            project_id=project_id,
            project_role_id=payload.project_role_id,
            message=payload.message,
        )
    except ApplicationError as exc:
        status_by_reason = {
            "project_not_found": status.HTTP_404_NOT_FOUND,
            "project_not_open": status.HTTP_400_BAD_REQUEST,
            "invalid_role": status.HTTP_400_BAD_REQUEST,
            "duplicate": status.HTTP_409_CONFLICT,
        }
        raise HTTPException(status_by_reason[exc.reason], str(exc)) from exc

    return db.scalar(_application_query().where(Application.id == application.id))


@router.get("/me/applications", response_model=list[ApplicationRead])
def list_my_applications(
    user: User = Depends(get_current_user), db: Session = Depends(get_db)
) -> list[Application]:
    query = (
        _application_query()
        .where(Application.user_id == user.id)
        .order_by(Application.created_at.desc())
    )
    return list(db.scalars(query))


@router.delete(
    "/me/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def withdraw_my_application(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    try:
        withdraw_application_service(db, user_id=user.id, application_id=application_id)
    except ApplicationError as exc:
        status_by_reason = {
            "application_not_found": status.HTTP_404_NOT_FOUND,
            "not_pending": status.HTTP_409_CONFLICT,
        }
        raise HTTPException(status_by_reason[exc.reason], str(exc)) from exc


@router.post(
    "/me/applications/{application_id}/leave-request",
    response_model=ApplicationRead,
)
def request_application_team_leave(
    application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Application:
    try:
        request_team_leave_service(db, user_id=user.id, application_id=application_id)
    except ApplicationError as exc:
        status_by_reason = {
            "application_not_found": status.HTTP_404_NOT_FOUND,
            "not_accepted": status.HTTP_409_CONFLICT,
        }
        raise HTTPException(status_by_reason[exc.reason], str(exc)) from exc
    return db.scalar(_application_query().where(Application.id == application_id))
