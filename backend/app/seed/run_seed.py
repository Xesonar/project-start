"""Idempotent demo-data seeding, run automatically on container startup."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.enums import ProjectDifficulty, ProjectFormat, ProjectStatus, SkillLevel
from app.models.organization import Organization
from app.models.project import Project, ProjectRole, ProjectSkill
from app.models.result import ParticipationConfirmation, ProjectResult
from app.models.skill import Skill
from app.seed.organizations_data import ORGANIZATIONS
from app.seed.projects_data import PROJECTS
from app.seed.skills_data import SKILLS
from app.services.user_upsert import _DEMO_SKILL_NAMES, ensure_demo_user


def seed_skills(db: Session) -> dict[str, Skill]:
    existing = {s.name: s for s in db.scalars(select(Skill))}
    for name, category in SKILLS:
        if name not in existing:
            skill = Skill(name=name, category=category)
            db.add(skill)
            existing[name] = skill
    db.flush()
    return existing


def seed_organizations(db: Session) -> dict[str, Organization]:
    existing = {o.name: o for o in db.scalars(select(Organization))}
    for org in ORGANIZATIONS:
        if org["name"] not in existing:
            organization = Organization(**org)
            db.add(organization)
            existing[org["name"]] = organization
    db.flush()
    return existing


def seed_projects(
    db: Session, organizations: dict[str, Organization], skills: dict[str, Skill]
) -> None:
    existing_titles = {p.title for p in db.scalars(select(Project))}
    for data in PROJECTS:
        if data["title"] in existing_titles:
            continue

        project = Project(
            organization_id=organizations[data["organization"]].id,
            title=data["title"],
            description=data["description"],
            difficulty=ProjectDifficulty(data["difficulty"]),
            status=ProjectStatus.open,
            deadline=data["deadline"],
            format=ProjectFormat(data["format"]),
            participant_limit=data["participant_limit"],
            expected_result=data["expected_result"],
        )
        db.add(project)
        db.flush()

        for role in data["roles"]:
            db.add(
                ProjectRole(
                    project_id=project.id,
                    title=role["title"],
                    description=role.get("description"),
                    slots=role["slots"],
                )
            )

        for skill_name, level in data["skills"]:
            db.add(
                ProjectSkill(
                    project_id=project.id,
                    skill_id=skills[skill_name].id,
                    required_level=SkillLevel(level),
                )
            )


_DEMO_PROJECT_TITLE = "Демо: навигатор по мероприятиям университета"


def seed_demo_portfolio(db: Session) -> None:
    """Gives the demo student one *confirmed* project.

    The public demo link has to look alive the moment a judge opens it, so
    this seeds a completed project + organiser confirmation for the demo
    user. The project is deliberately not one of the 12 open catalog
    projects (it is `completed`, so the catalog filters it out) — the
    catalog count and recommendation tests stay exact.
    """
    user = ensure_demo_user(db, skill_names=_DEMO_SKILL_NAMES)

    project = db.scalar(select(Project).where(Project.title == _DEMO_PROJECT_TITLE))
    if project is None:
        organization = db.scalar(
            select(Organization).where(
                Organization.name == "Университетский проектный офис"
            )
        ) or db.scalars(select(Organization)).first()
        project = Project(
            organization_id=organization.id,
            title=_DEMO_PROJECT_TITLE,
            description=(
                "Прототип навигатора по мероприятиям университета: фильтры по "
                "факультету, карточки активностей, расписание. Собран в рамках "
                "демо-сценария платформы."
            ),
            difficulty=ProjectDifficulty.beginner,
            status=ProjectStatus.completed,
            deadline="14 дней",
            format=ProjectFormat.hybrid,
            participant_limit=4,
            expected_result="Рабочий прототип мини-приложения и презентация.",
            is_demo=True,
        )
        db.add(project)
        db.flush()
    else:
        project.is_demo = True

    project_result = db.scalar(
        select(ProjectResult).where(ProjectResult.project_id == project.id)
    )
    if project_result is None:
        project_result = ProjectResult(
            project_id=project.id,
            title="Рабочий прототип мини-приложения",
            description=(
                "Навигатор по мероприятиям: фильтры по факультету, карточки, "
                "расписание — собрано и протестировано на реальных данных."
            ),
            result_url="https://example.com/project-result",
        )
        db.add(project_result)
    else:
        project_result.result_url = "https://example.com/project-result"

    if (
        db.scalar(
            select(ParticipationConfirmation).where(
                ParticipationConfirmation.user_id == user.id,
                ParticipationConfirmation.project_id == project.id,
            )
        )
        is None
    ):
        db.add(
            ParticipationConfirmation(
                project_id=project.id,
                user_id=user.id,
                confirmed_by="Университетский проектный офис",
                role="Frontend developer",
                contribution=(
                    "Собрал интерфейс мини-приложения: карточки мероприятий, "
                    "фильтры и навигация."
                ),
            )
        )
    db.flush()


def main() -> None:
    db = SessionLocal()
    try:
        skills = seed_skills(db)
        organizations = seed_organizations(db)
        seed_projects(db, organizations, skills)
        seed_demo_portfolio(db)
        db.commit()
        print(
            f"Seed: {len(skills)} skills, {len(organizations)} organizations, "
            f"{len(PROJECTS)} projects ensured."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
