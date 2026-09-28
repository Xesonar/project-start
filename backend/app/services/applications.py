from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.application import Application
from app.models.enums import ApplicationStatus, ProjectStatus
from app.models.project import Project, ProjectRole
from app.models.team import Team, TeamMember
from app.models.user import User


MAX_ACTIVE_PROJECTS = 3


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
    # Serialize applying with organizer status changes. Without this lock an
    # application could slip in while the organizer is closing recruitment.
    project = db.scalar(
        select(Project).where(Project.id == project_id).with_for_update()
    )
    if project is None:
        raise ApplicationError("project_not_found", "Проект не найден")
    if project.status != ProjectStatus.open:
        raise ApplicationError("project_not_open", "Набор в проект уже закрыт")

    # Acceptance also locks this row before changing the student's active
    # project count. That keeps a just-created pending application from
    # escaping automatic rejection when the third team slot is filled.
    db.scalar(select(User.id).where(User.id == user_id).with_for_update())
    active_team_count = db.scalar(
        select(func.count(func.distinct(TeamMember.team_id)))
        .join(Team, Team.id == TeamMember.team_id)
        .where(TeamMember.user_id == user_id, Team.status == "active")
    ) or 0
    if active_team_count >= MAX_ACTIVE_PROJECTS:
        raise ApplicationError(
            "already_in_team",
            f"У тебя уже есть {MAX_ACTIVE_PROJECTS} активных проекта",
        )

    role = db.get(ProjectRole, project_role_id)
    if role is None or role.project_id != project_id:
        raise ApplicationError("invalid_role", "Эта роль недоступна в проекте")

    existing = db.scalar(
        select(Application).where(
            Application.user_id == user_id,
            Application.project_id == project_id,
            Application.project_role_id == role.id,
            Application.status.in_(
                [
                    ApplicationStatus.pending,
                    ApplicationStatus.accepted,
                    ApplicationStatus.leave_requested,
                ]
            ),
        )
    )
    if existing is not None:
        raise ApplicationError("duplicate", "Ты уже откликнулся на эту роль")

    application = Application(
        user_id=user_id, project_id=project_id, project_role_id=role.id, message=message
    )
    db.add(application)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ApplicationError("duplicate", "Ты уже откликнулся на эту роль") from exc

    db.refresh(application)
    return application


def withdraw_application(db: Session, *, user_id: int, application_id: int) -> Application:
    application = db.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
        ).with_for_update()
    )
    if application is None:
        raise ApplicationError("application_not_found", "Отклик не найден")
    if application.status == ApplicationStatus.withdrawn:
        return application
    if application.status != ApplicationStatus.pending:
        raise ApplicationError(
            "not_pending",
            "Отменить можно только отклик на рассмотрении",
        )

    application.status = ApplicationStatus.withdrawn
    db.commit()
    db.refresh(application)
    return application


def request_team_leave(db: Session, *, user_id: int, application_id: int) -> Application:
    application = db.scalar(
        select(Application).where(
            Application.id == application_id,
            Application.user_id == user_id,
        ).with_for_update()
    )
    if application is None:
        raise ApplicationError("application_not_found", "Отклик не найден")
    if application.status == ApplicationStatus.leave_requested:
        return application
    if application.status != ApplicationStatus.accepted:
        raise ApplicationError(
            "not_accepted",
            "Запросить выход можно только после принятия в команду",
        )
    # Finalization locks the same project row first. Waiting for that lock
    # guarantees a leave request cannot appear just after completion.
    project = db.scalar(
        select(Project)
        .where(Project.id == application.project_id)
        .with_for_update()
    )
    if project is None:
        raise ApplicationError("project_not_found", "Проект не найден")
    if project.status == ProjectStatus.completed:
        raise ApplicationError(
            "project_completed",
            "Состав завершённого проекта изменить нельзя",
        )
    application.status = ApplicationStatus.leave_requested
    db.commit()
    db.refresh(application)
    return application
