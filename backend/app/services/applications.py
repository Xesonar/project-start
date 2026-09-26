from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.enums import ProjectStatus
from app.models.project import Project, ProjectRole


class ApplicationError(Exception):
    """reason is a stable machine-readable code — callers (HTTP route,
    bot screens) each map it to their own presentation (status code,
    Russian chat text) without duplicating the validation itself."""

    def __init__(self, reason: str, message: str):
        self.reason = reason
        super().__init__(message)


def create_application(
    db: Session, *, user_id: int, project_id: int, project_role_id: int, message: str | None = None
) -> Application:
    project = db.get(Project, project_id)
    if project is None:
        raise ApplicationError("project_not_found", "Project not found")
    if project.status != ProjectStatus.open:
        raise ApplicationError("project_not_open", "Project is not open for applications")

    role = db.get(ProjectRole, project_role_id)
    if role is None or role.project_id != project_id:
        raise ApplicationError("invalid_role", "Role does not belong to this project")

    application = Application(
        user_id=user_id, project_id=project_id, project_role_id=role.id, message=message
    )
    db.add(application)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApplicationError("duplicate", "You already applied for this role") from exc

    db.refresh(application)
    return application
