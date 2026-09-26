from app.db.session import SessionLocal
from app.seed.run_seed import main as run_seed


def _seed():
    run_seed()


def test_list_projects_returns_seeded_open_projects(client):
    _seed()
    resp = client.get("/projects")
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) == 12
    assert all(p["status"] == "open" for p in projects)


def test_list_projects_filters_by_difficulty(client):
    _seed()
    resp = client.get("/projects", params={"difficulty": "beginner"})
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) > 0
    assert all(p["difficulty"] == "beginner" for p in projects)


def test_list_projects_filters_by_skill(client):
    _seed()
    db = SessionLocal()
    try:
        from sqlalchemy import select

        from app.models.skill import Skill

        flutter_id = db.scalar(select(Skill.id).where(Skill.name == "Flutter"))
    finally:
        db.close()

    resp = client.get("/projects", params={"skill_id": [flutter_id]})
    assert resp.status_code == 200
    projects = resp.json()
    assert len(projects) == 1
    assert projects[0]["title"] == "Мобильный трекер привычек для студентов"


def test_get_project_detail_includes_roles_and_skills(client):
    _seed()
    projects = client.get("/projects").json()
    project_id = projects[0]["id"]

    resp = client.get(f"/projects/{project_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["roles"]) > 0
    assert len(body["required_skills"]) > 0


def test_get_project_detail_404_for_missing_project(client):
    resp = client.get("/projects/999999")
    assert resp.status_code == 404


def test_get_project_detail_does_not_expose_draft(client):
    _seed()
    from sqlalchemy import select

    from app.models.enums import ProjectStatus
    from app.models.project import Project

    db = SessionLocal()
    try:
        project = db.scalar(select(Project).where(Project.status == ProjectStatus.open))
        project_id = project.id
        project.status = ProjectStatus.draft
        db.commit()
    finally:
        db.close()

    resp = client.get(f"/projects/{project_id}")
    assert resp.status_code == 404


def test_list_projects_sort_by_difficulty(client):
    _seed()
    resp = client.get("/projects", params={"sort": "difficulty"})
    assert resp.status_code == 200
    order = {"beginner": 0, "intermediate": 1, "advanced": 2}
    difficulties = [order[p["difficulty"]] for p in resp.json()]
    assert difficulties == sorted(difficulties)
