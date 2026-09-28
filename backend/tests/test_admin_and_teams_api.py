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


def test_admin_can_publish_draft_project(client, monkeypatch):
    from app.seed.run_seed import main as run_seed

    run_seed()
    headers = _admin_headers(client, monkeypatch)
    organization_id = client.get("/admin/organizations", headers=headers).json()[0]["id"]
    skill_id = client.get("/skills").json()[0]["id"]
    payload = {
        "organization_id": organization_id,
        "title": "Черновик для публикации",
        "description": "Проект не должен появляться в каталоге до публикации.",
        "difficulty": "beginner",
        "status": "draft",
        "deadline": "14 дней",
        "format": "hybrid",
        "participant_limit": 2,
        "expected_result": "Рабочий прототип",
        "roles": [{"title": "Developer", "slots": 2}],
        "required_skills": [{"skill_id": skill_id, "required_level": "beginner"}],
    }
    created = client.post("/admin/projects", headers=headers, json=payload)
    assert created.status_code == 201
    project_id = created.json()["id"]
    assert client.get(f"/projects/{project_id}").status_code == 404

    published = client.post(f"/admin/projects/{project_id}/publish", headers=headers)
    assert published.status_code == 200
    assert published.json()["status"] == "open"
    assert client.get(f"/projects/{project_id}").status_code == 200

    repeated = client.post(f"/admin/projects/{project_id}/publish", headers=headers)
    assert repeated.status_code == 409


def test_admin_can_create_organization(client, monkeypatch):
    headers = _admin_headers(client, monkeypatch)
    created = client.post(
        "/admin/organizations",
        headers=headers,
        json={
            "name": "Лаборатория робототехники",
            "description": "Учебная лаборатория университета",
            "type": "Лаборатория",
            "verified": False,
        },
    )
    assert created.status_code == 201
    assert created.json()["verified"] is False
    duplicate = client.post(
        "/admin/organizations",
        headers=headers,
        json={
            "name": "лаборатория робототехники",
            "description": "Повтор",
            "type": "Лаборатория",
            "verified": False,
        },
    )
    assert duplicate.status_code == 409


def test_admin_can_close_and_reopen_recruitment(client, monkeypatch):
    from app.seed.run_seed import main as run_seed

    run_seed()
    headers = _admin_headers(client, monkeypatch)
    project = client.get("/projects").json()[0]
    closed = client.patch(
        f"/admin/projects/{project['id']}/status",
        headers=headers,
        json={"status": "in_progress"},
    )
    assert closed.status_code == 200
    assert closed.json()["status"] == "in_progress"
    assert all(item["id"] != project["id"] for item in client.get("/projects").json())

    reopened = client.patch(
        f"/admin/projects/{project['id']}/status",
        headers=headers,
        json={"status": "open"},
    )
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "open"


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
    assert metrics["students"] == 1
    assert metrics["assessed_students"] == 0
    assert metrics["applications"] == 1
    assert metrics["accepted_applications"] == 1
    assert metrics["completed_projects"] == 0
    assert metrics["confirmed_participations"] == 0
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
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "rejected", "note": "Сейчас нужен другой набор навыков"},
    )
    assert resp.status_code == 200

    resp = client.get("/me/team", headers=student_headers)
    assert resp.status_code == 404


def test_admin_must_explain_rejection(client, monkeypatch):
    student_headers = _student_headers(client, 216)
    admin_headers = _admin_headers(client, monkeypatch)
    _project, application = _seed_and_apply(client, student_headers)

    response = client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "rejected"},
    )
    assert response.status_code == 422


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

    leave_requested = client.post(
        f"/me/applications/{application['id']}/leave-request", headers=student_headers
    )
    assert leave_requested.status_code == 200

    rejected = client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "rejected", "note": "Выход подтверждён"},
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

    leave_requested = client.post(
        f"/me/applications/{application['id']}/leave-request", headers=student_headers
    )
    assert leave_requested.status_code == 200

    rejected = client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "rejected", "note": "Освобождаем место"},
    )
    assert rejected.status_code == 200
    assert client.get(f"/projects/{project['id']}").json()["status"] == "open"


def test_filling_team_rejects_remaining_pending_applications(client, monkeypatch):
    first_headers = _student_headers(client, 217)
    second_headers = _student_headers(client, 218)
    admin_headers = _admin_headers(client, monkeypatch)
    project, first_application = _seed_and_apply(client, first_headers)
    second_application = client.post(
        f"/projects/{project['id']}/applications",
        headers=second_headers,
        json={"project_role_id": first_application["project_role"]["id"]},
    )
    assert second_application.status_code == 201

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
        f"/admin/applications/{first_application['id']}",
        headers=admin_headers,
        json={"status": "accepted"},
    )
    assert accepted.status_code == 200

    applications = client.get(
        f"/admin/projects/{project['id']}/applications", headers=admin_headers
    ).json()
    remaining = next(item for item in applications if item["id"] == second_application.json()["id"])
    assert remaining["status"] == "rejected"
    assert remaining["decision_note"] == "Команда проекта уже сформирована."


def test_student_can_join_three_active_projects_but_not_a_fourth(client, monkeypatch):
    student_headers = _student_headers(client, 219)
    admin_headers = _admin_headers(client, monkeypatch)
    first_project, first_application = _seed_and_apply(client, student_headers)
    other_projects = [
        item for item in client.get("/projects").json() if item["id"] != first_project["id"]
    ][:3]
    details = [client.get(f"/projects/{item['id']}").json() for item in other_projects]

    second_application = client.post(
        f"/projects/{details[0]['id']}/applications",
        headers=student_headers,
        json={"project_role_id": details[0]["roles"][0]["id"]},
    )
    fourth_application = client.post(
        f"/projects/{details[2]['id']}/applications",
        headers=student_headers,
        json={"project_role_id": details[2]["roles"][0]["id"]},
    )
    assert second_application.status_code == 201
    assert fourth_application.status_code == 201

    assert client.patch(
        f"/admin/applications/{first_application['id']}",
        headers=admin_headers,
        json={"status": "accepted"},
    ).status_code == 200
    assert client.patch(
        f"/admin/applications/{second_application.json()['id']}",
        headers=admin_headers,
        json={"status": "accepted"},
    ).status_code == 200

    fourth_before_limit = next(
        item
        for item in client.get("/me/applications", headers=student_headers).json()
        if item["id"] == fourth_application.json()["id"]
    )
    assert fourth_before_limit["status"] == "pending"

    third_application = client.post(
        f"/projects/{details[1]['id']}/applications",
        headers=student_headers,
        json={"project_role_id": details[1]["roles"][0]["id"]},
    )
    assert third_application.status_code == 201
    assert client.patch(
        f"/admin/applications/{third_application.json()['id']}",
        headers=admin_headers,
        json={"status": "accepted"},
    ).status_code == 200

    teams = client.get("/me/teams", headers=student_headers)
    assert teams.status_code == 200
    assert len([team for team in teams.json() if team["status"] == "active"]) == 3

    fourth_after_limit = next(
        item
        for item in client.get("/me/applications", headers=student_headers).json()
        if item["id"] == fourth_application.json()["id"]
    )
    assert fourth_after_limit["status"] == "rejected"
    assert fourth_after_limit["decision_note"] == "Достигнут лимит: 3 активных проекта."

    blocked = client.post(
        f"/projects/{details[2]['id']}/applications",
        headers=student_headers,
        json={"project_role_id": details[2]["roles"][0]["id"]},
    )
    assert blocked.status_code == 409


def test_student_can_apply_again_after_rejection(client, monkeypatch):
    student_headers = _student_headers(client, 220)
    admin_headers = _admin_headers(client, monkeypatch)
    project, application = _seed_and_apply(client, student_headers)
    rejected = client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "rejected", "note": "Сначала обнови описание опыта"},
    )
    assert rejected.status_code == 200

    repeated = client.post(
        f"/projects/{project['id']}/applications",
        headers=student_headers,
        json={
            "project_role_id": application["project_role"]["id"],
            "message": "Обновил опыт и пробую снова",
        },
    )
    assert repeated.status_code == 201
    assert repeated.json()["id"] != application["id"]
    history = client.get("/me/applications", headers=student_headers).json()
    assert [item["status"] for item in history[:2]] == ["pending", "rejected"]
    assert repeated.json()["status"] == "pending"
    assert repeated.json()["decision_note"] is None


def test_admin_can_return_rejected_application_to_review(client, monkeypatch):
    student_headers = _student_headers(client, 221)
    admin_headers = _admin_headers(client, monkeypatch)
    _project, application = _seed_and_apply(client, student_headers)
    assert client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "rejected", "note": "Нужно уточнение"},
    ).status_code == 200

    reset = client.post(
        f"/admin/applications/{application['id']}/reset",
        headers=admin_headers,
    )
    assert reset.status_code == 200
    assert reset.json()["status"] == "pending"
    assert reset.json()["decision_note"] is None


def test_project_chat_is_visible_only_to_team_member(client, monkeypatch):
    student_headers = _student_headers(client, 213)
    admin_headers = _admin_headers(client, monkeypatch)
    project, application = _seed_and_apply(client, student_headers)
    chat_url = "https://max.ru/join/project-team"

    saved = client.patch(
        f"/admin/projects/{project['id']}/communication",
        headers=admin_headers,
        json={"team_chat_url": chat_url},
    )
    assert saved.status_code == 200
    assert saved.json()["team_chat_url"] == chat_url
    assert "team_chat_url" not in client.get(f"/projects/{project['id']}").json()

    accepted = client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "accepted"},
    )
    assert accepted.status_code == 200
    assert client.get("/me/team", headers=student_headers).json()["team_chat_url"] == chat_url


def test_admin_can_message_student_through_max_bot(client, monkeypatch):
    student_headers = _student_headers(client, 214)
    admin_headers = _admin_headers(client, monkeypatch)
    project, application = _seed_and_apply(client, student_headers)
    sent: list[dict] = []

    def fake_send_message(**kwargs):
        sent.append(kwargs)
        return {"body": {"mid": "message-id"}}

    monkeypatch.setattr("app.api.admin.max_bot_client.send_message", fake_send_message)
    response = client.post(
        f"/admin/applications/{application['id']}/message",
        headers=admin_headers,
        json={"text": "Когда сможешь созвониться?"},
    )
    assert response.status_code == 200
    assert response.json() == {"delivered": True}
    assert sent[0]["user_id"] == 214
    assert project["title"] in sent[0]["text"]


def test_student_requests_team_leave_and_admin_confirms(client, monkeypatch):
    student_headers = _student_headers(client, 215)
    admin_headers = _admin_headers(client, monkeypatch)
    _project, application = _seed_and_apply(client, student_headers)
    assert client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "accepted"},
    ).status_code == 200

    requested = client.post(
        f"/me/applications/{application['id']}/leave-request",
        headers=student_headers,
    )
    assert requested.status_code == 200
    assert requested.json()["status"] == "leave_requested"
    assert client.get("/me/team", headers=student_headers).status_code == 200

    team = client.get(
        f"/admin/projects/{_project['id']}/team", headers=admin_headers
    ).json()
    blocked_finalize = client.post(
        f"/admin/projects/{_project['id']}/finalize",
        headers=admin_headers,
        json={
            "result": {"title": "Результат", "description": "Готово"},
            "confirmations": [
                {
                    "user_id": team["members"][0]["user"]["id"],
                    "role": team["members"][0]["role_title"],
                }
            ],
        },
    )
    assert blocked_finalize.status_code == 409

    confirmed = client.patch(
        f"/admin/applications/{application['id']}",
        headers=admin_headers,
        json={"status": "rejected", "note": "Выход из команды подтверждён"},
    )
    assert confirmed.status_code == 200
    assert client.get("/me/team", headers=student_headers).status_code == 404
