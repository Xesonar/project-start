"""Idempotent reference-data seeding, run automatically on container startup."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.enums import ProjectDifficulty, ProjectFormat, ProjectStatus, SkillLevel
from app.models.organization import Organization
from app.models.project import Project, ProjectRole, ProjectSkill
from app.models.skill import Skill
from app.seed.organizations_data import ORGANIZATIONS
from app.seed.projects_data import PROJECTS
from app.seed.skills_data import SKILLS


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


def main() -> None:
    db = SessionLocal()
    try:
        skills = seed_skills(db)
        organizations = seed_organizations(db)
        seed_projects(db, organizations, skills)
        db.commit()
        print(
            f"Seed: {len(skills)} skills, {len(organizations)} organizations, "
            f"{len(PROJECTS)} projects ensured."
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
