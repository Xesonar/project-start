from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.bot.payload import encode
from app.core.deps import require_admin
from app.db.session import get_db
from app.models.application import Application
from app.models.enums import (
    ApplicationStatus,
    ProjectStatus,
    ProjectSubmissionStatus,
)
from app.models.organization import Organization
from app.models.profile import StudentProfile
from app.models.project import Project, ProjectRole, ProjectSkill
from app.models.skill import Skill
from app.models.result import ParticipationConfirmation, ProjectResult
from app.models.team import Team, TeamMember
from app.models.submission import ProjectSubmission
from app.models.user import User
from app.schemas.admin import (
    AdminApplicationRead,
    AdminMessageCreate,
    AdminMessageResult,
    AdminMetricsRead,
    ApplicationStatusUpdate,
    ProjectCommunicationRead,
    ProjectCommunicationUpdate,
    ProjectStatusUpdate,
)
from app.schemas.portfolio import (
    ConfirmationCreate,
    ConfirmationRead,
    ProjectCompleteRequest,
    ProjectFinalizeRequest,
)
from app.schemas.project import (
    OrganizationCreate,
    OrganizationRead,
    ProjectCreate,
    ProjectListItem,
    ProjectRead,
)
from app.schemas.team import TeamRead
from app.schemas.submission import AdminSubmissionRead, SubmissionReview
from app.services import max_bot_client
from app.services.applications import MAX_ACTIVE_PROJECTS
from app.services.notification_outbox import queue_failed_notification

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


def _send_user_message(
    user: User, *, text: str, buttons: list[list[dict]] | None = None
) -> dict | None:
    response = max_bot_client.send_message(
        user_id=user.max_user_id,
        text=text,
        buttons=buttons,
    )
    if response is None:
        queue_failed_notification(user_id=user.id, text=text, buttons=buttons)
    return response


@router.get("/metrics", response_model=AdminMetricsRead)
def get_metrics(db: Session = Depends(get_db)) -> AdminMetricsRead:
    students = db.scalar(select(func.count(User.id))) or 0
    assessed = db.scalar(
        select(func.count(StudentProfile.user_id))
        .where(StudentProfile.preferred_role.is_not(None))
    ) or 0
    applications = db.scalar(
        select(func.count(Application.id))
    ) or 0
    accepted = db.scalar(
        select(func.count(Application.id))
        .where(
            Application.status.in_(
                [ApplicationStatus.accepted, ApplicationStatus.leave_requested]
            )
        )
    ) or 0
    completed = db.scalar(
        select(func.count(Project.id)).where(Project.status == ProjectStatus.completed)
    ) or 0
    confirmations = db.scalar(
        select(func.count(ParticipationConfirmation.id))
    ) or 0
    pending_applications = db.scalar(
        select(func.count(Application.id)).where(
            Application.status == ApplicationStatus.pending
        )
    ) or 0
    overdue_applications = db.scalar(
        select(func.count(Application.id)).where(
            Application.status == ApplicationStatus.pending,
            Application.created_at < datetime.now(timezone.utc) - timedelta(hours=48),
        )
    ) or 0
    pending_submissions = db.scalar(
        select(func.count(ProjectSubmission.id)).where(
            ProjectSubmission.status == ProjectSubmissionStatus.submitted
        )
    ) or 0
    leave_requests = db.scalar(
        select(func.count(Application.id)).where(
            Application.status == ApplicationStatus.leave_requested
        )
    ) or 0
    return AdminMetricsRead(
        students=students,
        assessed_students=assessed,
        applications=applications,
        accepted_applications=accepted,
        completed_projects=completed,
        confirmed_participations=confirmations,
        assessment_rate=round(assessed / students * 100, 1) if students else 0,
        acceptance_rate=round(accepted / applications * 100, 1) if applications else 0,
        pending_applications=pending_applications,
        overdue_applications=overdue_applications,
        pending_submissions=pending_submissions,
        leave_requests=leave_requests,
    )


@router.get("/projects", response_model=list[ProjectListItem])
def list_all_projects(db: Session = Depends(get_db)) -> list[Project]:
    query = select(Project).options(
        selectinload(Project.organization),
        selectinload(Project.roles),
        selectinload(Project.required_skills).selectinload(ProjectSkill.skill),
    ).order_by(Project.created_at.desc())
    return list(db.scalars(query))


@router.get("/organizations", response_model=list[OrganizationRead])
def list_organizations(db: Session = Depends(get_db)) -> list[Organization]:
    return list(db.scalars(select(Organization).order_by(Organization.name)))


@router.post(
    "/organizations",
    response_model=OrganizationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_organization(
    payload: OrganizationCreate, db: Session = Depends(get_db)
) -> Organization:
    duplicate = db.scalar(
        select(Organization.id).where(func.lower(Organization.name) == payload.name.lower())
    )
    if duplicate is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Организация с таким названием уже существует",
        )
    organization = Organization(**payload.model_dump())
    db.add(organization)
    db.commit()
    db.refresh(organization)
    return organization


@router.post(
    "/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    if db.get(Organization, payload.organization_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Организация не найдена")

    skill_ids = [item.skill_id for item in payload.required_skills]
    if len(skill_ids) != len(set(skill_ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Навыки не должны повторяться")
    existing_skill_ids = (
        set(db.scalars(select(Skill.id).where(Skill.id.in_(skill_ids))))
        if skill_ids
        else set()
    )
    missing_skill_ids = sorted(set(skill_ids) - existing_skill_ids)
    if missing_skill_ids:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Не найдены навыки: {missing_skill_ids}",
        )

    data = payload.model_dump(exclude={"roles", "required_skills"})
    project = Project(**data)
    db.add(project)
    db.flush()
    db.add_all(
        [ProjectRole(project_id=project.id, **item.model_dump()) for item in payload.roles]
    )
    db.add_all(
        [
            ProjectSkill(project_id=project.id, **item.model_dump())
            for item in payload.required_skills
        ]
    )
    db.commit()
    return db.scalar(
        select(Project)
        .where(Project.id == project.id)
        .options(
            selectinload(Project.organization),
            selectinload(Project.roles),
            selectinload(Project.required_skills).selectinload(ProjectSkill.skill),
        )
    )


@router.post("/projects/{project_id}/publish", response_model=ProjectListItem)
def publish_project(project_id: int, db: Session = Depends(get_db)) -> Project:
    project = db.scalar(
        select(Project).where(Project.id == project_id).with_for_update()
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Проект не найден")
    if project.status != ProjectStatus.draft:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Опубликовать можно только черновик",
        )
    project.status = ProjectStatus.open
    db.commit()
    return db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.organization),
            selectinload(Project.roles),
            selectinload(Project.required_skills).selectinload(ProjectSkill.skill),
        )
    )


@router.patch("/projects/{project_id}/status", response_model=ProjectListItem)
def update_project_status(
    project_id: int,
    payload: ProjectStatusUpdate,
    db: Session = Depends(get_db),
) -> Project:
    started_users: list[User] = []
    project = db.scalar(select(Project).where(Project.id == project_id).with_for_update())
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Проект не найден")
    if project.status in {ProjectStatus.draft, ProjectStatus.completed}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Статус черновика или завершённого проекта меняется отдельным действием",
        )

    next_status = ProjectStatus(payload.status)
    allowed_transitions = {
        ProjectStatus.open: {ProjectStatus.recruitment_closed},
        ProjectStatus.recruitment_closed: {ProjectStatus.open, ProjectStatus.in_progress},
        ProjectStatus.in_progress: set(),
    }
    if next_status not in allowed_transitions.get(project.status, set()):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Недопустимый переход статуса проекта",
        )

    team = db.scalar(select(Team).where(Team.project_id == project_id))
    member_count = (
        db.scalar(
            select(func.count(TeamMember.user_id)).where(TeamMember.team_id == team.id)
        )
        if team is not None
        else 0
    ) or 0
    if next_status == ProjectStatus.open and member_count >= project.participant_limit:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Нельзя открыть набор: команда уже заполнена",
        )
    if next_status == ProjectStatus.in_progress and member_count == 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Нельзя начать проект без участников",
        )
    if next_status == ProjectStatus.in_progress:
        pending_count = db.scalar(
            select(func.count(Application.id)).where(
                Application.project_id == project_id,
                Application.status == ApplicationStatus.pending,
            )
        ) or 0
        if pending_count:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Сначала обработайте все ожидающие отклики",
            )
    if next_status == ProjectStatus.in_progress and team is not None:
        started_users = list(
            db.scalars(
                select(User)
                .join(TeamMember, TeamMember.user_id == User.id)
                .where(TeamMember.team_id == team.id)
            )
        )
    project.status = next_status
    db.commit()

    for user in started_users:
        buttons = [[{"type": "callback", "text": "Мои команды", "payload": encode("t")}]]
        if project.team_chat_url:
            buttons.insert(
                0,
                [{"type": "link", "text": "Открыть чат команды", "url": project.team_chat_url}],
            )
        _send_user_message(
            user,
            text=(
                f"Проект «{project.title}» начался. "
                "Теперь можно работать над задачей и отправлять результат на проверку."
            ),
            buttons=buttons,
        )
    return db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.organization),
            selectinload(Project.roles),
            selectinload(Project.required_skills).selectinload(ProjectSkill.skill),
        )
    )


@router.get(
    "/projects/{project_id}/communication",
    response_model=ProjectCommunicationRead,
)
def get_project_communication(
    project_id: int, db: Session = Depends(get_db)
) -> ProjectCommunicationRead:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Проект не найден")
    return ProjectCommunicationRead(team_chat_url=project.team_chat_url)


@router.patch(
    "/projects/{project_id}/communication",
    response_model=ProjectCommunicationRead,
)
def update_project_communication(
    project_id: int,
    payload: ProjectCommunicationUpdate,
    db: Session = Depends(get_db),
) -> ProjectCommunicationRead:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Проект не найден")
    project.team_chat_url = payload.team_chat_url
    db.commit()
    return ProjectCommunicationRead(team_chat_url=project.team_chat_url)


def _admin_application_query():
    return select(Application).options(
        selectinload(Application.project_role),
        selectinload(Application.user).selectinload(User.profile),
    )


@router.get("/projects/{project_id}/applications", response_model=list[AdminApplicationRead])
def list_project_applications(project_id: int, db: Session = Depends(get_db)) -> list[Application]:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Проект не найден")

    query = (
        _admin_application_query()
        .where(Application.project_id == project_id)
        .order_by(Application.created_at)
    )
    return list(db.scalars(query))


@router.patch("/applications/{application_id}", response_model=AdminApplicationRead)
def update_application_status(
    application_id: int, payload: ApplicationStatusUpdate, db: Session = Depends(get_db)
) -> Application:
    automatic_notifications: list[tuple[User, str]] = []
    application = db.scalar(
        _admin_application_query()
        .where(Application.id == application_id)
        .with_for_update()
    )
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Отклик не найден")
    if application.status == ApplicationStatus.withdrawn:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Отменённый студентом отклик обработать нельзя",
        )

    previous_status = application.status
    next_status = ApplicationStatus(payload.status)
    if previous_status not in {
        ApplicationStatus.pending,
        ApplicationStatus.leave_requested,
    }:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Это решение уже принято. Сначала верните отклик на рассмотрение",
        )
    project = db.scalar(
        select(Project).where(Project.id == application.project_id).with_for_update()
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Проект не найден")
    if project.status == ProjectStatus.completed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Состав завершённого проекта изменить нельзя",
        )
    if (
        previous_status == ApplicationStatus.pending
        and next_status == ApplicationStatus.accepted
        and project.status not in {ProjectStatus.open, ProjectStatus.recruitment_closed}
    ):
        raise HTTPException(status.HTTP_409_CONFLICT, "Набор в проект закрыт")
    if next_status == ApplicationStatus.rejected and not payload.note:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Укажите причину отказа",
        )
    application.status = next_status
    application.decision_note = payload.note
    application.decided_at = datetime.now(timezone.utc)

    if application.status == ApplicationStatus.accepted:
        if previous_status == ApplicationStatus.pending:
            # Serialize decisions for the same student across different
            # projects. Project-row locks alone do not protect the global
            # three-active-project limit.
            db.scalar(select(User.id).where(User.id == application.user_id).with_for_update())
            active_team_count = db.scalar(
                select(func.count(func.distinct(Team.id)))
                .join(TeamMember, TeamMember.team_id == Team.id)
                .where(
                    TeamMember.user_id == application.user_id,
                    Team.status == "active",
                    Team.project_id != application.project_id,
                )
            ) or 0
            if active_team_count >= MAX_ACTIVE_PROJECTS:
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"Студент уже участвует в {MAX_ACTIVE_PROJECTS} активных проектах",
                )
        accepted_for_role = db.scalar(
            select(func.count(Application.id)).where(
                Application.id != application.id,
                Application.project_role_id == application.project_role_id,
                Application.status.in_(
                    [ApplicationStatus.accepted, ApplicationStatus.leave_requested]
                ),
            )
        ) or 0
        if accepted_for_role >= application.project_role.slots:
            raise HTTPException(status.HTTP_409_CONFLICT, "На этой роли больше нет мест")

        accepted_user_ids = set(
            db.scalars(
                select(Application.user_id).where(
                    Application.id != application.id,
                    Application.project_id == application.project_id,
                    Application.status.in_(
                        [ApplicationStatus.accepted, ApplicationStatus.leave_requested]
                    ),
                )
            )
        )
        if (
            application.user_id not in accepted_user_ids
            and len(accepted_user_ids) >= project.participant_limit
        ):
            raise HTTPException(status.HTTP_409_CONFLICT, "Команда проекта уже заполнена")

        team = db.scalar(select(Team).where(Team.project_id == application.project_id))
        if team is None:
            team = Team(project_id=application.project_id)
            db.add(team)
            db.flush()

        existing_member = db.get(TeamMember, (team.id, application.user_id))
        if existing_member is None:
            db.add(
                TeamMember(
                    team_id=team.id,
                    user_id=application.user_id,
                    role_title=application.project_role.title,
                )
            )
        else:
            existing_member.role_title = application.project_role.title

        # A person occupies exactly one team seat in a project. They may
        # apply to several roles while deciding, but accepting one role must
        # close every other application for this same project.
        other_applications = list(
            db.scalars(
                select(Application).where(
                    Application.id != application.id,
                    Application.project_id == application.project_id,
                    Application.user_id == application.user_id,
                    Application.status.in_(
                        [
                            ApplicationStatus.pending,
                            ApplicationStatus.accepted,
                            ApplicationStatus.leave_requested,
                        ]
                    ),
                )
            )
        )
        for other_application in other_applications:
            other_application.status = ApplicationStatus.rejected
            other_application.decision_note = "Вы приняты на другую роль этого проекта."
            other_application.decided_at = datetime.now(timezone.utc)
            automatic_notifications.append(
                (other_application.user, f"Другой отклик на «{project.title}» закрыт: ты принят на выбранную роль.")
            )

        db.flush()
        active_team_count = db.scalar(
            select(func.count(func.distinct(Team.id)))
            .join(TeamMember, TeamMember.team_id == Team.id)
            .where(
                TeamMember.user_id == application.user_id,
                Team.status == "active",
            )
        ) or 0
        if active_team_count >= MAX_ACTIVE_PROJECTS:
            other_project_applications = list(
                db.scalars(
                    select(Application).where(
                        Application.user_id == application.user_id,
                        Application.project_id != application.project_id,
                        Application.status == ApplicationStatus.pending,
                    )
                )
            )
            for other_application in other_project_applications:
                other_application.status = ApplicationStatus.rejected
                other_application.decision_note = (
                    f"Достигнут лимит: {MAX_ACTIVE_PROJECTS} активных проекта."
                )
                other_application.decided_at = datetime.now(timezone.utc)
                automatic_notifications.append(
                    (
                        other_application.user,
                        f"Отклик на «{other_application.project.title}» закрыт: достигнут лимит — {MAX_ACTIVE_PROJECTS} активных проекта.",
                    )
                )

        member_count = db.scalar(
            select(func.count(TeamMember.user_id)).where(TeamMember.team_id == team.id)
        ) or 0
        if member_count >= project.participant_limit:
            project.status = ProjectStatus.recruitment_closed
            remaining_applications = list(
                db.scalars(
                    select(Application).where(
                        Application.project_id == project.id,
                        Application.status == ApplicationStatus.pending,
                    )
                )
            )
            for remaining in remaining_applications:
                remaining.status = ApplicationStatus.rejected
                remaining.decision_note = "Команда проекта уже сформирована."
                remaining.decided_at = datetime.now(timezone.utc)
                automatic_notifications.append(
                    (
                        remaining.user,
                        f"Отклик на «{project.title}» закрыт: команда уже сформирована.",
                    )
                )
    else:
        project = db.get(Project, application.project_id)
        team = db.scalar(select(Team).where(Team.project_id == application.project_id))
        if team is not None:
            existing_member = db.get(TeamMember, (team.id, application.user_id))
            if existing_member is not None:
                other_accepted = db.scalar(
                    _admin_application_query()
                    .where(
                        Application.id != application.id,
                        Application.project_id == application.project_id,
                        Application.user_id == application.user_id,
                        Application.status.in_(
                            [ApplicationStatus.accepted, ApplicationStatus.leave_requested]
                        ),
                    )
                    .order_by(Application.created_at.desc())
                )
                if other_accepted is None:
                    db.delete(existing_member)
                else:
                    existing_member.role_title = other_accepted.project_role.title

    db.commit()

    # Best-effort — max_bot_client swallows its own errors and returns None,
    # so a MAX hiccup never turns a successful accept/reject into a 500.
    if previous_status == ApplicationStatus.leave_requested:
        if application.status == ApplicationStatus.accepted:
            text = f"Организатор оставил тебя в команде проекта «{application.project.title}»."
        else:
            text = f"Запрос на выход из проекта «{application.project.title}» подтверждён."
    elif application.status == ApplicationStatus.accepted:
        text = (
            f"Твой отклик на «{application.project.title}» "
            f"(роль: {application.project_role.title}) принят."
        )
    else:
        text = (
            f"Твой отклик на «{application.project.title}» "
            f"(роль: {application.project_role.title}) отклонён."
        )
    if payload.note:
        text += f"\n\nКомментарий организатора: {payload.note}"
    buttons = [[{"type": "callback", "text": "Мои отклики", "payload": encode("a")}]]
    if application.status == ApplicationStatus.accepted and application.project.team_chat_url:
        buttons.insert(
            0,
            [
                {
                    "type": "link",
                    "text": "Вступить в чат команды",
                    "url": application.project.team_chat_url,
                }
            ],
        )
    _send_user_message(
        application.user,
        text=text,
        buttons=buttons,
    )
    for affected_user, affected_text in automatic_notifications:
        _send_user_message(affected_user, text=affected_text, buttons=buttons)

    return db.scalar(_admin_application_query().where(Application.id == application_id))


@router.post("/applications/{application_id}/reset", response_model=AdminApplicationRead)
def reset_application_decision(
    application_id: int, db: Session = Depends(get_db)
) -> Application:
    """Returns an organizer decision to review and repairs team membership."""
    application = db.scalar(
        _admin_application_query()
        .where(Application.id == application_id)
        .with_for_update()
    )
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Отклик не найден")
    if application.status in {ApplicationStatus.pending, ApplicationStatus.withdrawn}:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Этот отклик нельзя вернуть на рассмотрение",
        )

    project = db.scalar(
        select(Project).where(Project.id == application.project_id).with_for_update()
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Проект не найден")
    if project.status == ProjectStatus.completed:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Решения по завершённому проекту менять нельзя",
        )
    team = db.scalar(select(Team).where(Team.project_id == application.project_id))
    if project.status == ProjectStatus.in_progress:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "После начала проекта решение можно изменить только через запрос на выход",
        )
    if team is not None and application.status in {
        ApplicationStatus.accepted,
        ApplicationStatus.leave_requested,
    }:
        member = db.get(TeamMember, (team.id, application.user_id))
        if member is not None:
            db.delete(member)
            db.flush()
    application.status = ApplicationStatus.pending
    application.decision_note = None
    application.decided_at = None
    db.commit()

    _send_user_message(
        application.user,
        text=(
            f"Организатор вернул твой отклик на «{application.project.title}» "
            "на повторное рассмотрение."
        ),
        buttons=[[{"type": "callback", "text": "Мои отклики", "payload": encode("a")}]],
    )
    return db.scalar(
        _admin_application_query().where(Application.id == application_id)
    )


@router.get(
    "/projects/{project_id}/submissions",
    response_model=list[AdminSubmissionRead],
)
def list_project_submissions(
    project_id: int, db: Session = Depends(get_db)
) -> list[ProjectSubmission]:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Проект не найден")
    return list(
        db.scalars(
            select(ProjectSubmission)
            .where(ProjectSubmission.project_id == project_id)
            .options(selectinload(ProjectSubmission.user))
            .order_by(ProjectSubmission.submitted_at)
        )
    )


@router.patch(
    "/submissions/{submission_id}",
    response_model=AdminSubmissionRead,
)
def review_project_submission(
    submission_id: int,
    payload: SubmissionReview,
    db: Session = Depends(get_db),
) -> ProjectSubmission:
    submission_ref = db.get(ProjectSubmission, submission_id)
    if submission_ref is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Сдача не найдена")
    db.scalar(
        select(Project.id)
        .where(Project.id == submission_ref.project_id)
        .with_for_update()
    )
    submission = db.scalar(
        select(ProjectSubmission)
        .where(ProjectSubmission.id == submission_id)
        .with_for_update()
        .options(selectinload(ProjectSubmission.user), selectinload(ProjectSubmission.project))
    )
    if submission.project.status != ProjectStatus.in_progress:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Проверка доступна только после запуска проекта",
        )
    if submission.status != ProjectSubmissionStatus.submitted:
        raise HTTPException(status.HTTP_409_CONFLICT, "Эта сдача сейчас не ожидает проверки")
    next_status = ProjectSubmissionStatus(payload.status)
    if next_status != ProjectSubmissionStatus.approved and not payload.note:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "При отказе или возврате на доработку нужен комментарий",
        )
    submission.status = next_status
    submission.review_note = payload.note
    submission.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(submission)

    verdict = {
        ProjectSubmissionStatus.approved: "Работа подтверждена и будет добавлена в портфолио после завершения проекта.",
        ProjectSubmissionStatus.revision_requested: "Работу нужно доработать и отправить повторно.",
        ProjectSubmissionStatus.rejected: "Работа не подтверждена.",
    }[next_status]
    text = f"Проект «{submission.project.title}»: {verdict}"
    if payload.note:
        text += f"\n\nКомментарий организатора: {payload.note}"
    _send_user_message(submission.user, text=text)
    return submission


@router.post(
    "/applications/{application_id}/message",
    response_model=AdminMessageResult,
)
def message_application_student(
    application_id: int,
    payload: AdminMessageCreate,
    db: Session = Depends(get_db),
) -> AdminMessageResult:
    application = db.scalar(_admin_application_query().where(Application.id == application_id))
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Отклик не найден")

    buttons = None
    if (
        application.status in {ApplicationStatus.accepted, ApplicationStatus.leave_requested}
        and application.project.team_chat_url
    ):
        buttons = [
            [
                {
                    "type": "link",
                    "text": "Открыть чат команды",
                    "url": application.project.team_chat_url,
                }
            ]
        ]
    response = _send_user_message(
        application.user,
        text=f"Сообщение от организатора проекта «{application.project.title}»:\n\n{payload.text}",
        buttons=buttons,
    )
    return AdminMessageResult(delivered=response is not None)


@router.get("/projects/{project_id}/team", response_model=TeamRead)
def get_project_team(project_id: int, db: Session = Depends(get_db)) -> Team:
    team = db.scalar(
        select(Team)
        .where(Team.project_id == project_id)
        .options(
            selectinload(Team.project).selectinload(Project.organization),
            selectinload(Team.project).selectinload(Project.roles),
            selectinload(Team.project)
            .selectinload(Project.required_skills)
            .selectinload(ProjectSkill.skill),
            selectinload(Team.members).selectinload(TeamMember.user),
        )
    )
    if team is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "У проекта пока нет команды")
    return team


@router.post(
    "/projects/{project_id}/complete",
    response_model=ProjectListItem,
    deprecated=True,
    include_in_schema=False,
)
def complete_project(
    project_id: int, payload: ProjectCompleteRequest, db: Session = Depends(get_db)
) -> Project:
    raise HTTPException(
        status.HTTP_410_GONE,
        "Завершайте проект после подтверждения результатов всех участников",
    )


@router.post("/projects/{project_id}/finalize", response_model=ProjectListItem)
def finalize_project(
    project_id: int, payload: ProjectFinalizeRequest, db: Session = Depends(get_db)
) -> Project:
    """Atomically save the result, verified contributions and completed state."""
    closed_applications: list[Application] = []
    project = db.scalar(
        select(Project).where(Project.id == project_id).with_for_update()
    )
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Проект не найден")
    if project.status == ProjectStatus.completed:
        raise HTTPException(status.HTTP_409_CONFLICT, "Проект уже завершён")
    if project.status != ProjectStatus.in_progress:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Сначала закройте набор и запустите проект",
        )

    pending_leave_requests = db.scalar(
        select(func.count(Application.id)).where(
            Application.project_id == project_id,
            Application.status == ApplicationStatus.leave_requested,
        )
    ) or 0
    if pending_leave_requests:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Сначала обработайте все запросы на выход из команды",
        )

    # Finalization is also the hard end of recruitment. This safety net
    # handles projects completed directly from an open state and legacy
    # pending applications created before closing recruitment became final.
    closed_applications = list(
        db.scalars(
            _admin_application_query().where(
                Application.project_id == project_id,
                Application.status == ApplicationStatus.pending,
            )
        )
    )
    for application in closed_applications:
        application.status = ApplicationStatus.rejected
        application.decision_note = "Проект завершён, набор закрыт."
        application.decided_at = datetime.now(timezone.utc)

    user_ids = [item.user_id for item in payload.confirmations]
    if len(user_ids) != len(set(user_ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Участник указан несколько раз")

    team = db.scalar(select(Team).where(Team.project_id == project_id))
    if team is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "У проекта нет команды")
    if team.status != "active":
        raise HTTPException(status.HTTP_409_CONFLICT, "Команда проекта уже не активна")
    team_user_ids = set(
        db.scalars(select(TeamMember.user_id).where(TeamMember.team_id == team.id))
    )
    provided_user_ids = set(user_ids)
    if provided_user_ids != team_user_ids:
        missing_user_ids = sorted(team_user_ids - provided_user_ids)
        unknown_user_ids = sorted(provided_user_ids - team_user_ids)
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Список подтверждений должен точно совпадать с командой: "
            f"не указаны={missing_user_ids}, лишние={unknown_user_ids}",
        )

    submissions = list(
        db.scalars(
            select(ProjectSubmission).where(
                ProjectSubmission.project_id == project_id,
                ProjectSubmission.user_id.in_(team_user_ids),
            ).with_for_update()
        )
    )
    submissions_by_user = {item.user_id: item for item in submissions}
    unapproved_user_ids = sorted(
        user_id
        for user_id in team_user_ids
        if user_id not in submissions_by_user
        or submissions_by_user[user_id].status != ProjectSubmissionStatus.approved
    )
    if unapproved_user_ids:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Нужно подтвердить работу каждого участника: {unapproved_user_ids}",
        )
    roles_by_user = {
        member.user_id: member.role_title
        for member in db.scalars(select(TeamMember).where(TeamMember.team_id == team.id))
    }

    result = db.scalar(select(ProjectResult).where(ProjectResult.project_id == project_id))
    if result is None:
        result = ProjectResult(project_id=project_id, **payload.result.model_dump())
        db.add(result)
    else:
        for field, value in payload.result.model_dump().items():
            setattr(result, field, value)

    for item in payload.confirmations:
        confirmation = db.scalar(
            select(ParticipationConfirmation).where(
                ParticipationConfirmation.project_id == project_id,
                ParticipationConfirmation.user_id == item.user_id,
            )
        )
        if confirmation is None:
            db.add(
                ParticipationConfirmation(
                    project_id=project_id,
                    user_id=item.user_id,
                    confirmed_by=project.organization.name,
                    role=roles_by_user[item.user_id],
                    contribution=submissions_by_user[item.user_id].summary,
                )
            )
        else:
            confirmation.role = roles_by_user[item.user_id]
            confirmation.contribution = submissions_by_user[item.user_id].summary

    project.status = ProjectStatus.completed
    team.status = "completed"
    db.commit()

    completed_users = list(db.scalars(select(User).where(User.id.in_(team_user_ids))))
    for completed_user in completed_users:
        _send_user_message(
            completed_user,
            text=(
                f"Проект «{project.title}» завершён. Подтверждённый результат "
                "добавлен в твоё портфолио."
            ),
            buttons=[[{"type": "callback", "text": "Моя команда", "payload": encode("t")}]],
        )
    for application in closed_applications:
        _send_user_message(
            application.user,
            text=f"Отклик на «{project.title}» закрыт: проект уже завершён.",
            buttons=[[{"type": "callback", "text": "Мои отклики", "payload": encode("a")}]],
        )

    return db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .options(
            selectinload(Project.organization),
            selectinload(Project.roles),
            selectinload(Project.required_skills).selectinload(ProjectSkill.skill),
        )
    )


@router.post(
    "/projects/{project_id}/confirmations",
    response_model=list[ConfirmationRead],
    deprecated=True,
    include_in_schema=False,
)
def confirm_participation(
    project_id: int, payload: list[ConfirmationCreate], db: Session = Depends(get_db)
) -> list[ParticipationConfirmation]:
    raise HTTPException(
        status.HTTP_410_GONE,
        "Подтверждения создаются только при завершении проекта",
    )
