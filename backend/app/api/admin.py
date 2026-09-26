from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.bot.payload import encode
from app.core.deps import require_admin
from app.db.session import get_db
from app.models.application import Application
from app.models.enums import ApplicationStatus, ProjectStatus
from app.models.organization import Organization
from app.models.profile import StudentProfile
from app.models.project import Project, ProjectRole, ProjectSkill
from app.models.skill import Skill
from app.models.result import ParticipationConfirmation, ProjectResult
from app.models.team import Team, TeamMember
from app.models.user import User
from app.schemas.admin import AdminApplicationRead, AdminMetricsRead, ApplicationStatusUpdate
from app.schemas.portfolio import (
    ConfirmationCreate,
    ConfirmationRead,
    ProjectCompleteRequest,
    ProjectFinalizeRequest,
)
from app.schemas.project import OrganizationRead, ProjectCreate, ProjectRead, ProjectListItem
from app.schemas.team import TeamRead
from app.services import max_bot_client

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/metrics", response_model=AdminMetricsRead)
def get_metrics(db: Session = Depends(get_db)) -> AdminMetricsRead:
    students = db.scalar(select(func.count(User.id))) or 0
    assessed = db.scalar(
        select(func.count(StudentProfile.user_id)).where(
            StudentProfile.preferred_role.is_not(None)
        )
    ) or 0
    applications = db.scalar(select(func.count(Application.id))) or 0
    accepted = db.scalar(
        select(func.count(Application.id)).where(
            Application.status == ApplicationStatus.accepted
        )
    ) or 0
    completed = db.scalar(
        select(func.count(Project.id)).where(Project.status == ProjectStatus.completed)
    ) or 0
    confirmations = db.scalar(select(func.count(ParticipationConfirmation.id))) or 0
    return AdminMetricsRead(
        students=students,
        assessed_students=assessed,
        applications=applications,
        accepted_applications=accepted,
        completed_projects=completed,
        confirmed_participations=confirmations,
        assessment_rate=round(assessed / students * 100, 1) if students else 0,
        acceptance_rate=round(accepted / applications * 100, 1) if applications else 0,
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
    "/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> Project:
    if db.get(Organization, payload.organization_id) is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Unknown organization")

    skill_ids = [item.skill_id for item in payload.required_skills]
    if len(skill_ids) != len(set(skill_ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Duplicate skill ids")
    existing_skill_ids = (
        set(db.scalars(select(Skill.id).where(Skill.id.in_(skill_ids))))
        if skill_ids
        else set()
    )
    missing_skill_ids = sorted(set(skill_ids) - existing_skill_ids)
    if missing_skill_ids:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Unknown skill ids: {missing_skill_ids}",
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


def _admin_application_query():
    return select(Application).options(
        selectinload(Application.project_role),
        selectinload(Application.user).selectinload(User.profile),
    )


@router.get("/projects/{project_id}/applications", response_model=list[AdminApplicationRead])
def list_project_applications(project_id: int, db: Session = Depends(get_db)) -> list[Application]:
    if db.get(Project, project_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

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
    application = db.scalar(_admin_application_query().where(Application.id == application_id))
    if application is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")

    application.status = ApplicationStatus(payload.status)

    if application.status == ApplicationStatus.accepted:
        project = db.scalar(
            select(Project).where(Project.id == application.project_id).with_for_update()
        )
        accepted_for_role = db.scalar(
            select(func.count(Application.id)).where(
                Application.id != application.id,
                Application.project_role_id == application.project_role_id,
                Application.status == ApplicationStatus.accepted,
            )
        ) or 0
        if accepted_for_role >= application.project_role.slots:
            raise HTTPException(status.HTTP_409_CONFLICT, "No slots left for this role")

        accepted_user_ids = set(
            db.scalars(
                select(Application.user_id).where(
                    Application.id != application.id,
                    Application.project_id == application.project_id,
                    Application.status == ApplicationStatus.accepted,
                )
            )
        )
        if (
            application.user_id not in accepted_user_ids
            and len(accepted_user_ids) >= project.participant_limit
        ):
            raise HTTPException(status.HTTP_409_CONFLICT, "Project team is full")

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
                        [ApplicationStatus.pending, ApplicationStatus.accepted]
                    ),
                )
            )
        )
        for other_application in other_applications:
            other_application.status = ApplicationStatus.rejected

        db.flush()
        member_count = db.scalar(
            select(func.count(TeamMember.user_id)).where(TeamMember.team_id == team.id)
        ) or 0
        if member_count >= project.participant_limit:
            project.status = ProjectStatus.in_progress
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
                        Application.status == ApplicationStatus.accepted,
                    )
                    .order_by(Application.created_at.desc())
                )
                if other_accepted is None:
                    db.delete(existing_member)
                else:
                    existing_member.role_title = other_accepted.project_role.title

            db.flush()
            member_count = db.scalar(
                select(func.count(TeamMember.user_id)).where(TeamMember.team_id == team.id)
            ) or 0
            if (
                project is not None
                and project.status == ProjectStatus.in_progress
                and member_count < project.participant_limit
            ):
                project.status = ProjectStatus.open

    db.commit()

    # Best-effort — max_bot_client swallows its own errors and returns None,
    # so a MAX hiccup never turns a successful accept/reject into a 500.
    verdict = "принят" if application.status == ApplicationStatus.accepted else "отклонён"
    text = f"Твой отклик на «{application.project.title}» (роль: {application.project_role.title}) {verdict}."
    max_bot_client.send_message(
        user_id=application.user.max_user_id,
        text=text,
        buttons=[[{"type": "callback", "text": "Мои отклики", "payload": encode("a")}]],
    )

    return db.scalar(_admin_application_query().where(Application.id == application_id))


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
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This project has no team yet")
    return team


@router.post("/projects/{project_id}/complete", response_model=ProjectListItem)
def complete_project(
    project_id: int, payload: ProjectCompleteRequest, db: Session = Depends(get_db)
) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    project.status = ProjectStatus.completed
    team = db.scalar(select(Team).where(Team.project_id == project_id))
    if team is not None:
        team.status = "completed"

    result = db.scalar(select(ProjectResult).where(ProjectResult.project_id == project_id))
    if result is None:
        result = ProjectResult(project_id=project_id, **payload.model_dump())
        db.add(result)
    else:
        for field, value in payload.model_dump().items():
            setattr(result, field, value)

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


@router.post("/projects/{project_id}/finalize", response_model=ProjectListItem)
def finalize_project(
    project_id: int, payload: ProjectFinalizeRequest, db: Session = Depends(get_db)
) -> Project:
    """Atomically save the result, confirmations and completed state.

    The older two-step endpoints remain available for API compatibility, but
    the admin UI uses this endpoint so a failed confirmation cannot leave a
    completed project without portfolio records.
    """
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    user_ids = [item.user_id for item in payload.confirmations]
    if len(user_ids) != len(set(user_ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Duplicate user ids")

    team = db.scalar(select(Team).where(Team.project_id == project_id))
    if team is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Project has no team")
    team_user_ids = set(
        db.scalars(select(TeamMember.user_id).where(TeamMember.team_id == team.id))
    )
    unknown_user_ids = sorted(set(user_ids) - team_user_ids)
    if unknown_user_ids:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Users are not project team members: {unknown_user_ids}",
        )

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
                    role=item.role,
                    contribution=item.contribution,
                )
            )
        else:
            confirmation.role = item.role
            confirmation.contribution = item.contribution

    project.status = ProjectStatus.completed
    team.status = "completed"
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


@router.post("/projects/{project_id}/confirmations", response_model=list[ConfirmationRead])
def confirm_participation(
    project_id: int, payload: list[ConfirmationCreate], db: Session = Depends(get_db)
) -> list[ParticipationConfirmation]:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    if project.status != ProjectStatus.completed:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Project must be completed before participation can be confirmed",
        )

    user_ids = [item.user_id for item in payload]
    if len(user_ids) != len(set(user_ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Duplicate user ids")

    team = db.scalar(select(Team).where(Team.project_id == project_id))
    team_user_ids = (
        set(
            db.scalars(
                select(TeamMember.user_id).where(TeamMember.team_id == team.id)
            )
        )
        if team is not None
        else set()
    )
    unknown_user_ids = sorted(set(user_ids) - team_user_ids)
    if unknown_user_ids:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Users are not project team members: {unknown_user_ids}",
        )

    confirmations = []
    for item in payload:
        confirmation = db.scalar(
            select(ParticipationConfirmation).where(
                ParticipationConfirmation.project_id == project_id,
                ParticipationConfirmation.user_id == item.user_id,
            )
        )
        if confirmation is None:
            confirmation = ParticipationConfirmation(
                project_id=project_id,
                user_id=item.user_id,
                confirmed_by=project.organization.name,
                role=item.role,
                contribution=item.contribution,
            )
            db.add(confirmation)
        else:
            confirmation.role = item.role
            confirmation.contribution = item.contribution
        confirmations.append(confirmation)

    db.commit()
    for confirmation in confirmations:
        db.refresh(confirmation)
    return confirmations
