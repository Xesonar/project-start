from app.core.config import settings
from tests.test_max_auth import build_init_data


def _student_headers(client, max_user_id: int) -> dict:
    init_data = build_init_data(user={"id": max_user_id, "first_name": "Студент"})
    resp = client.post("/auth/max", json={"init_data": init_data})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _admin_headers(client, monkeypatch) -> dict:
    monkeypatch.setattr(settings, "admin_password", "secret")
    resp = client.post("/admin/login", json={"password": "secret"})
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _seed_and_apply(client, headers):
    from app.seed.run_seed import main as run_seed

    run_seed()
    project = client.get("/projects").json()[0]
    detail = client.get(f"/projects/{project['id']}").json()
    role_id = detail["roles"][0]["id"]
    resp = client.post(
        f"/projects/{project['id']}/applications", headers=headers, json={"project_role_id": role_id}
    )
    return detail, resp.json()


def test_admin_endpoints_require_admin_token(client):
    resp = client.get("/admin/projects")
    assert resp.status_code == 401


def test_student_token_cannot_access_admin_endpoints(client):
    headers = _student_headers(client, 201)
    resp = client.get("/admin/projects", headers=headers)
    assert resp.status_code == 403


def test_admin_can_list_project_applications(client, monkeypatch):
    student_headers = _student_headers(client, 202)
    admin_headers = _admin_headers(client, monkeypatch)
    project, application = _seed_and_apply(client, student_headers)

    resp = client.get(f"/admin/projects/{project['id']}/applications", headers=admin_headers)
    assert resp.status_code == 200
    apps = resp.json()
    assert len(apps) == 1
    assert apps[0]["id"] == application["id"]
    assert apps[0]["user"]["name"] == "Студент"


def test_admin_can_create_project(client, monkeypatch):
    from app.seed.run_seed import main as run_seed

    run_seed()
    headers = _admin_headers(client, monkeypatch)
    organizations = client.get("/admin/organizations", headers=headers).json()
    skills = client.get("/skills").json()
    payload = {
        "organization_id": organizations[0]["id"],
        "title": "Новый проект из админки",
        "description": "Подробное описание нового учебного проекта.",
        "difficulty": "beginner",
        "status": "open",
        "deadline": "14 дней",
        "format": "hybrid",
        "participant_limit": 3,
        "expected_result": "Рабочий прототип",
        "roles": [{"title": "Frontend developer", "slots": 3}],
        "required_skills": [
            {"skill_id": skills[0]["id"], "required_level": "beginner"}
        ],
    }
    response = client.post("/admin/projects", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == payload["title"]
    assert body["roles"][0]["slots"] == 3
    assert body["required_skills"][0]["skill"]["id"] == skills[0]["id"]


def test_admin_rejects_project_when_role_slots_cannot_fill_team(client, monkeypatch):
    from app.seed.run_seed import main as run_seed

    run_seed()
    headers = _admin_headers(client, monkeypatch)
    organization_id = client.get("/admin/organizations", headers=headers).json()[0]["id"]
    payload = {
        "organization_id": organization_id,
        "title": "Проект с неверной вместимостью",
        "description": "У этого проекта недостаточно ролевых слотов для команды.",
        "difficulty": "beginner",
        "status": "open",
        "deadline": "14 дней",
        "format": "hybrid",
        "participant_limit": 3,
        "expected_result": "Рабочий прототип",
        "roles": [{"title": "Developer", "slots": 2}],
        "required_skills": [],
    }

    response = client.post("/admin/projects", headers=headers, json=payload)
    assert response.status_code == 422


def test_admin_rejects_duplicate_role_titles(client, monkeypatch):
    from app.seed.run_seed import main as run_seed

    run_seed()
    headers = _admin_headers(client, monkeypatch)
    organization_id = client.get("/admin/organizations", headers=headers).json()[0]["id"]
    payload = {
        "organization_id": organization_id,
        "title": "Проект с одинаковыми ролями",
        "description": "Роли с одинаковым названием не должны создаваться дважды.",
        "difficulty": "beginner",
        "status": "open",
        "deadline": "14 дней",
        "format": "hybrid",
        "participant_limit": 2,
        "expected_result": "Рабочий прототип",
        "roles": [
            {"title": "Developer", "slots": 1},
            {"title": " developer ", "slots": 1},
        ],
        "required_skills": [],
    }

    response = client.post("/admin/projects", headers=headers, json=payload)
    assert response.status_code == 422


def test_admin_metrics_expose_measurable_funnel(client, monkeypatch):
    student_headers = _student_headers(client, 209)
    admin_headers = _admin_headers(client, monkeypatch)
    _project, application = _seed_and_apply(client, student_headers)
    accepted = client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "accepted"},
    )
    assert accepted.status_code == 200

    response = client.get("/admin/metrics", headers=admin_headers)
    assert response.status_code == 200
    metrics = response.json()
    assert metrics["students"] >= 1
    assert metrics["applications"] == 1
    assert metrics["accepted_applications"] == 1
    assert metrics["acceptance_rate"] == 100.0


def test_accepting_application_creates_team_membership(client, monkeypatch):
    student_headers = _student_headers(client, 203)
    admin_headers = _admin_headers(client, monkeypatch)
    project, application = _seed_and_apply(client, student_headers)

    resp = client.patch(
        f"/admin/applications/{application['id']}", headers=admin_headers, json={"status": "accepted"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "accepted"

    resp = client.get("/me/team", headers=student_headers)
    assert resp.status_code == 200
    team = resp.json()
    assert team["project"]["id"] == project["id"]
    assert len(team["members"]) == 1
    assert team["members"][0]["role_title"] == application["project_role"]["title"]


def test_accepting_one_role_rejects_other_roles_for_same_student(client, monkeypatch):
    student_headers = _student_headers(client, 210)
    admin_headers = _admin_headers(client, monkeypatch)
    project, first_application = _seed_and_apply(client, student_headers)
    second_role_id = project["roles"][1]["id"]
    second_application = client.post(
        f"/projects/{project['id']}/applications",
        headers=student_headers,
        json={"project_role_id": second_role_id},
    ).json()

    accepted = client.patch(
        f"/admin/applications/{second_application['id']}",
        headers=admin_headers,
        json={"status": "accepted"},
    )
    assert accepted.status_code == 200

    applications = client.get(
        f"/admin/projects/{project['id']}/applications", headers=admin_headers
    ).json()
    status_by_id = {item["id"]: item["status"] for item in applications}
    assert status_by_id[second_application["id"]] == "accepted"
    assert status_by_id[first_application["id"]] == "rejected"

    team = client.get("/me/team", headers=student_headers).json()
    assert len(team["members"]) == 1
    assert team["members"][0]["role_title"] == second_application["project_role"]["title"]


def test_rejecting_application_does_not_create_team(client, monkeypatch):
    student_headers = _student_headers(client, 204)
    admin_headers = _admin_headers(client, monkeypatch)
    _project, application = _seed_and_apply(client, student_headers)

    resp = client.patch(
        f"/admin/applications/{application['id']}", headers=admin_headers, json={"status": "rejected"}
    )
    assert resp.status_code == 200

    resp = client.get("/me/team", headers=student_headers)
    assert resp.status_code == 404


def test_admin_cannot_process_withdrawn_application(client, monkeypatch):
    student_headers = _student_headers(client, 211)
    admin_headers = _admin_headers(client, monkeypatch)
    _project, application = _seed_and_apply(client, student_headers)
    assert client.delete(
        f"/me/applications/{application['id']}", headers=student_headers
    ).status_code == 204

    response = client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "accepted"},
    )
    assert response.status_code == 409


def test_rejecting_previously_accepted_application_removes_team_membership(client, monkeypatch):
    student_headers = _student_headers(client, 206)
    admin_headers = _admin_headers(client, monkeypatch)
    _project, application = _seed_and_apply(client, student_headers)

    accepted = client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "accepted"},
    )
    assert accepted.status_code == 200
    assert client.get("/me/team", headers=student_headers).status_code == 200

    rejected = client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "rejected"},
    )
    assert rejected.status_code == 200
    assert client.get("/me/team", headers=student_headers).status_code == 404


def test_my_team_404_when_not_a_member(client):
    headers = _student_headers(client, 205)
    resp = client.get("/me/team", headers=headers)
    assert resp.status_code == 404


def test_admin_cannot_accept_more_students_than_role_slots(client, monkeypatch):
    first_headers = _student_headers(client, 207)
    second_headers = _student_headers(client, 208)
    admin_headers = _admin_headers(client, monkeypatch)
    project, first_application = _seed_and_apply(client, first_headers)
    role_id = first_application["project_role"]["id"]
    second_application = client.post(
        f"/projects/{project['id']}/applications",
        headers=second_headers,
        json={"project_role_id": role_id},
    ).json()

    first = client.patch(
        f"/admin/applications/{first_application['id']}",
        headers=admin_headers,
        json={"status": "accepted"},
    )
    assert first.status_code == 200
    second = client.patch(
        f"/admin/applications/{second_application['id']}",
        headers=admin_headers,
        json={"status": "accepted"},
    )
    assert second.status_code == 409


def test_full_team_closes_project_and_rejection_reopens_it(client, monkeypatch):
    student_headers = _student_headers(client, 211)
    admin_headers = _admin_headers(client, monkeypatch)
    project, application = _seed_and_apply(client, student_headers)

    # Make the seeded project a one-person project to exercise the boundary.
    from sqlalchemy import update

    from app.db.session import SessionLocal
    from app.models.project import Project

    with SessionLocal() as db:
        db.execute(
            update(Project)
            .where(Project.id == project["id"])
            .values(participant_limit=1)
        )
        db.commit()

    accepted = client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "accepted"},
    )
    assert accepted.status_code == 200
    assert client.get(f"/projects/{project['id']}").json()["status"] == "in_progress"

    new_student_headers = _student_headers(client, 212)
    blocked = client.post(
        f"/projects/{project['id']}/applications",
        headers=new_student_headers,
        json={"project_role_id": application["project_role"]["id"]},
    )
    assert blocked.status_code == 400

    rejected = client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "rejected"},
    )
    assert rejected.status_code == 200
    assert client.get(f"/projects/{project['id']}").json()["status"] == "open"
