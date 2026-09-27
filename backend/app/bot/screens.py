"""Pure (text, buttons) builders for each bot-chat screen. No I/O beyond the
DB session passed in — reuses the same models/queries as the REST API
(app/api/projects.py, app/api/applications.py, app/api/teams.py) rather than
re-deriving business rules for the chat surface."""

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.bot.payload import Action, encode
from app.models.application import Application
from app.models.enums import ApplicationStatus, ProjectStatus
from app.models.project import Project, ProjectSkill
from app.models.team import Team, TeamMember
from app.models.user import User
from app.services.applications import ApplicationError
from app.services.applications import create_application as create_application_service
from app.services.applications import withdraw_application as withdraw_application_service

PAGE_SIZE = 5

_DIFFICULTY_LABELS = {"beginner": "начальный", "intermediate": "средний", "advanced": "продвинутый"}
_FORMAT_LABELS = {"online": "онлайн", "offline": "очно", "hybrid": "гибрид"}
_STATUS_LABELS = {
    "pending": "на рассмотрении",
    "accepted": "принята",
    "rejected": "отклонена",
    "withdrawn": "отменена",
}

Buttons = list[list[dict]]

_HOME_BUTTON: dict = {"type": "callback", "text": "Главная", "payload": encode("h")}
_OPEN_APP_BUTTON: dict = {"type": "open_app", "text": "Открыть приложение"}


def build_home(db, user: User) -> tuple[str, Buttons]:
    lines = [f"Привет, {user.name}!", "", "Здесь можно найти проект и откликнуться прямо в чате."]

    pending_total = len(
        list(
            db.scalars(
                select(Application.id).where(
                    Application.user_id == user.id, Application.status == ApplicationStatus.pending
                )
            )
        )
    )
    if pending_total:
        lines.append(f"У тебя {pending_total} отклик(ов) на рассмотрении.")

    buttons: Buttons = [
        [{"type": "callback", "text": "Найти проект", "payload": encode("p", 0)}],
        [{"type": "callback", "text": "Мои отклики", "payload": encode("a")}],
        [{"type": "callback", "text": "Моя команда", "payload": encode("t")}],
        [_OPEN_APP_BUTTON],
    ]
    return "\n".join(lines), buttons


def build_projects(db, page: int) -> tuple[str, Buttons]:
    rows = list(
        db.scalars(
            select(Project)
            .where(Project.status == ProjectStatus.open)
            .options(selectinload(Project.organization))
            .order_by(Project.created_at.desc())
            .offset(page * PAGE_SIZE)
            .limit(PAGE_SIZE + 1)
        )
    )
    has_next = len(rows) > PAGE_SIZE
    projects = rows[:PAGE_SIZE]

    if not projects:
        text = "Открытых проектов пока нет." if page == 0 else "Проектов больше нет."
        return text, [[_HOME_BUTTON]]

    lines = [f"Открытые проекты (стр. {page + 1}):", ""]
    buttons: Buttons = []
    for i, project in enumerate(projects, start=1):
        difficulty = _DIFFICULTY_LABELS[project.difficulty.value]
        lines.append(f"{i}. {project.title} — {project.organization.name} — {difficulty}")
        buttons.append(
            [{"type": "callback", "text": project.title[:40], "payload": encode("pd", project.id, page)}]
        )

    nav_row = []
    if page > 0:
        nav_row.append({"type": "callback", "text": "< Назад", "payload": encode("p", page - 1)})
    if has_next:
        nav_row.append({"type": "callback", "text": "Дальше >", "payload": encode("p", page + 1)})
    if nav_row:
        buttons.append(nav_row)
    buttons.append([_HOME_BUTTON])

    return "\n".join(lines), buttons


def build_project_detail(db, user: User, project_id: int, page: int) -> tuple[str, Buttons]:
    project = db.scalar(
        select(Project)
        .where(
            Project.id == project_id,
            Project.status != ProjectStatus.draft,
        )
        .options(
            selectinload(Project.organization),
            selectinload(Project.roles),
            selectinload(Project.required_skills).selectinload(ProjectSkill.skill),
        )
    )
    back_row = [{"type": "callback", "text": "< К списку", "payload": encode("p", page)}, _HOME_BUTTON]

    if project is None:
        return "Этот проект больше не найден.", [back_row]

    description = project.description
    if len(description) > 500:
        description = description[:497] + "..."

    lines = [
        project.title,
        project.organization.name,
        (
            f"{_DIFFICULTY_LABELS[project.difficulty.value]} · "
            f"{_FORMAT_LABELS[project.format.value]} · {project.deadline} · "
            f"до {project.participant_limit} мест"
        ),
        "",
        description,
        "",
        "Навыки: " + ", ".join(ps.skill.name for ps in project.required_skills),
    ]

    already_applied_role_ids = set(
        db.scalars(
            select(Application.project_role_id).where(
                Application.user_id == user.id,
                Application.project_id == project_id,
                Application.status != ApplicationStatus.withdrawn,
            )
        )
    )

    buttons: Buttons = []
    if project.status != ProjectStatus.open:
        lines.append("")
        lines.append("Проект сейчас закрыт для откликов.")
    else:
        applicable_roles = [r for r in project.roles if r.id not in already_applied_role_ids]
        if not applicable_roles:
            lines.append("")
            lines.append("Ты уже откликнулся на все роли этого проекта.")
        else:
            lines.append("")
            lines.append("Роли:")
            for role in applicable_roles:
                lines.append(f"— {role.title} (мест: {role.slots})")
                buttons.append(
                    [
                        {
                            "type": "callback",
                            "text": f"Откликнуться: {role.title}"[:40],
                            "payload": encode("apply", project.id, role.id),
                        }
                    ]
                )

    buttons.append(back_row)
    return "\n".join(lines), buttons


def build_apply_result(db, user: User, project_id: int, role_id: int) -> tuple[str, Buttons]:
    back_row = [{"type": "callback", "text": "Мои отклики", "payload": encode("a")}, _HOME_BUTTON]
    try:
        create_application_service(
            db, user_id=user.id, project_id=project_id, project_role_id=role_id
        )
    except ApplicationError as exc:
        friendly = {
            "project_not_found": "Этот проект больше не найден.",
            "project_not_open": "Проект уже закрыт для откликов.",
            "invalid_role": "Эта роль недоступна.",
            "duplicate": "Ты уже откликался на эту роль.",
        }
        return friendly.get(exc.reason, "Не удалось отправить отклик."), [back_row]

    return "Отклик отправлен! Статус будет виден в «Мои отклики».", [back_row]


def build_my_applications(db, user: User) -> tuple[str, Buttons]:
    applications = list(
        db.scalars(
            select(Application)
            .where(Application.user_id == user.id)
            .options(selectinload(Application.project), selectinload(Application.project_role))
            .order_by(Application.created_at.desc())
        )
    )
    if not applications:
        return "Пока нет откликов — найди проект на главной.", [[_HOME_BUTTON]]

    lines = ["Мои отклики:", ""]
    buttons: Buttons = []
    for app in applications:
        status_label = _STATUS_LABELS[app.status.value]
        lines.append(f"— {app.project.title} ({app.project_role.title}): {status_label}")
        if app.status == ApplicationStatus.pending:
            buttons.append(
                [
                    {
                        "type": "callback",
                        "text": f"Отменить: {app.project.title}"[:40],
                        "payload": encode("withdraw", app.id),
                    }
                ]
            )

    buttons.append([_HOME_BUTTON])
    return "\n".join(lines), buttons


def build_withdraw_result(db, user: User, application_id: int) -> tuple[str, Buttons]:
    try:
        withdraw_application_service(db, user_id=user.id, application_id=application_id)
    except ApplicationError as exc:
        friendly = {
            "application_not_found": "Отклик не найден.",
            "not_pending": "Этот отклик уже нельзя отменить.",
        }
        return friendly.get(exc.reason, "Не удалось отменить отклик."), [[_HOME_BUTTON]]
    return "Отклик отменён. На эту роль можно откликнуться снова.", [
        [{"type": "callback", "text": "Мои отклики", "payload": encode("a")}],
        [_HOME_BUTTON],
    ]


def build_my_team(db, user: User) -> tuple[str, Buttons]:
    team_member = db.scalar(
        select(TeamMember)
        .join(Team, Team.id == TeamMember.team_id)
        .where(TeamMember.user_id == user.id, Team.status == "active")
        .order_by(TeamMember.joined_at.desc(), TeamMember.team_id.desc())
    )
    if team_member is None:
        return "Пока ты не в команде — дождись решения по своим откликам.", [[_HOME_BUTTON]]

    team = db.scalar(
        select(Team)
        .where(Team.id == team_member.team_id)
        .options(
            selectinload(Team.project).selectinload(Project.organization),
            selectinload(Team.members).selectinload(TeamMember.user),
        )
    )
    lines = [team.project.title, team.project.organization.name, "", "Команда:"]
    for member in team.members:
        lines.append(f"— {member.user.name} ({member.role_title})")

    return "\n".join(lines), [[_HOME_BUTTON]]


def route(db, user: User, action: Action) -> tuple[str, Buttons]:
    """Dispatches a decoded button payload to the matching screen builder.
    Unknown/malformed payloads fall back to Home rather than erroring —
    a stale button from an old app version shouldn't dead-end the chat."""
    try:
        if action.screen == "p":
            return build_projects(db, int(action.args[0]))
        if action.screen == "pd":
            return build_project_detail(db, user, int(action.args[0]), int(action.args[1]))
        if action.screen == "apply":
            return build_apply_result(db, user, int(action.args[0]), int(action.args[1]))
        if action.screen == "a":
            return build_my_applications(db, user)
        if action.screen == "withdraw":
            return build_withdraw_result(db, user, int(action.args[0]))
        if action.screen == "t":
            return build_my_team(db, user)
    except (IndexError, ValueError):
        pass
    return build_home(db, user)
