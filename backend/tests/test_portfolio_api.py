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


def _apply_and_accept(client, student_headers, admin_headers):
    from app.seed.run_seed import main as run_seed

    run_seed()
    project = client.get("/projects").json()[0]
    detail = client.get(f"/projects/{project['id']}").json()
    role_id = detail["roles"][0]["id"]

    application = client.post(
        f"/projects/{project['id']}/applications",
        headers=student_headers,
        json={"project_role_id": role_id},
    ).json()
    client.patch(
        f"/admin/applications/{application['id']}", headers=admin_headers, json={"status": "accepted"}
    )
    return detail, application


def _submit_and_approve(
    client,
    student_headers,
    admin_headers,
    project,
    summary="Написал API бота и проверил интеграцию",
):
    submitted = client.put(
        f"/me/projects/{project['id']}/submission",
        headers=student_headers,
        json={"summary": summary, "result_url": "https://example.com/demo"},
    )
    assert submitted.status_code == 200
    submission = submitted.json()
    reviewed = client.patch(
        f"/admin/submissions/{submission['id']}",
        headers=admin_headers,
        json={"status": "approved"},
    )
    assert reviewed.status_code == 200
    return reviewed.json()


def _finalize(client, admin_headers, project, member, *, contribution="ignored by server"):
    response = client.post(
        f"/admin/projects/{project['id']}/finalize",
        headers=admin_headers,
        json={
            "result": {
                "title": "Рабочий прототип бота",
                "description": "Бот запущен и протестирован с реальными данными.",
                "result_url": "https://example.com/demo",
            },
            "confirmations": [
                {
                    "user_id": member["user"]["id"],
                    "role": member["role_title"],
                    "contribution": contribution,
                }
            ],
        },
    )
    return response


def test_full_completion_and_portfolio_flow(client, monkeypatch):
    student_headers = _student_headers(client, 301)
    admin_headers = _admin_headers(client, monkeypatch)
    project, application = _apply_and_accept(client, student_headers, admin_headers)

    summary = "Написал API бота и проверил интеграцию"
    _submit_and_approve(client, student_headers, admin_headers, project, summary)
    team = client.get(f"/admin/projects/{project['id']}/team", headers=admin_headers).json()
    resp = _finalize(client, admin_headers, project, team["members"][0])
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    completed_team = client.get("/me/team", headers=student_headers)
    assert completed_team.status_code == 200
    assert completed_team.json()["status"] == "completed"

    resp = client.get("/me/portfolio", headers=student_headers)
    assert resp.status_code == 200
    portfolio = resp.json()
    assert len(portfolio) == 1
    assert portfolio[0]["project"]["id"] == project["id"]
    assert portfolio[0]["result"]["title"] == "Рабочий прототип бота"
    assert portfolio[0]["confirmation"]["contribution"] == summary


def test_atomic_finalize_rejects_invalid_member_without_completing_project(client, monkeypatch):
    student_headers = _student_headers(client, 305)
    admin_headers = _admin_headers(client, monkeypatch)
    project, _application = _apply_and_accept(client, student_headers, admin_headers)

    response = client.post(
        f"/admin/projects/{project['id']}/finalize",
        headers=admin_headers,
        json={
            "result": {"title": "Result", "description": "Done"},
            "confirmations": [{"user_id": 999999, "role": "Developer"}],
        },
    )
    assert response.status_code == 400

    refreshed = next(
        item
        for item in client.get("/admin/projects", headers=admin_headers).json()
        if item["id"] == project["id"]
    )
    assert refreshed["status"] != "completed"


def test_finalize_requires_approved_work_from_every_member(client, monkeypatch):
    student_headers = _student_headers(client, 307)
    admin_headers = _admin_headers(client, monkeypatch)
    project, _application = _apply_and_accept(client, student_headers, admin_headers)
    team = client.get(f"/admin/projects/{project['id']}/team", headers=admin_headers).json()

    response = _finalize(client, admin_headers, project, team["members"][0])
    assert response.status_code == 409

    refreshed = next(
        item
        for item in client.get("/admin/projects", headers=admin_headers).json()
        if item["id"] == project["id"]
    )
    assert refreshed["status"] != "completed"


def test_student_can_fix_and_resubmit_work(client, monkeypatch):
    student_headers = _student_headers(client, 308)
    admin_headers = _admin_headers(client, monkeypatch)
    project, _application = _apply_and_accept(client, student_headers, admin_headers)
    submitted = client.put(
        f"/me/projects/{project['id']}/submission",
        headers=student_headers,
        json={"summary": "Первая версия результата", "result_url": None},
    ).json()

    missing_note = client.patch(
        f"/admin/submissions/{submitted['id']}",
        headers=admin_headers,
        json={"status": "revision_requested"},
    )
    assert missing_note.status_code == 422

    revision = client.patch(
        f"/admin/submissions/{submitted['id']}",
        headers=admin_headers,
        json={"status": "revision_requested", "note": "Добавь ссылку и детали проверки"},
    )
    assert revision.status_code == 200
    assert revision.json()["status"] == "revision_requested"

    resubmitted = client.put(
        f"/me/projects/{project['id']}/submission",
        headers=student_headers,
        json={
            "summary": "Исправил результат и подробно описал проверку",
            "result_url": "https://example.com/fixed",
        },
    )
    assert resubmitted.status_code == 200
    assert resubmitted.json()["status"] == "submitted"
    assert resubmitted.json()["review_note"] is None

    approved = client.patch(
        f"/admin/submissions/{submitted['id']}",
        headers=admin_headers,
        json={"status": "approved"},
    )
    assert approved.status_code == 200

    team = client.get(f"/admin/projects/{project['id']}/team", headers=admin_headers).json()
    assert _finalize(client, admin_headers, project, team["members"][0]).status_code == 200

    locked = client.put(
        f"/me/projects/{project['id']}/submission",
        headers=student_headers,
        json={"summary": "Попытка изменить завершённую работу", "result_url": None},
    )
    assert locked.status_code == 409


def test_atomic_finalize_populates_portfolio(client, monkeypatch):
    student_headers = _student_headers(client, 306)
    admin_headers = _admin_headers(client, monkeypatch)
    project, _application = _apply_and_accept(client, student_headers, admin_headers)
    team = client.get(f"/admin/projects/{project['id']}/team", headers=admin_headers).json()
    member = team["members"][0]
    summary = "Собрал и протестировал рабочий прототип"
    _submit_and_approve(client, student_headers, admin_headers, project, summary)

    response = _finalize(client, admin_headers, project, member, contribution="Подменённый текст")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert client.get("/me/team", headers=student_headers).json()["status"] == "completed"
    portfolio = client.get("/me/portfolio", headers=student_headers).json()[0]
    assert portfolio["result"]["title"] == "Рабочий прототип бота"
    assert portfolio["confirmation"]["contribution"] == summary


def test_portfolio_empty_before_confirmation(client):
    headers = _student_headers(client, 302)
    resp = client.get("/me/portfolio", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_confirmations_require_admin(client):
    resp = client.post("/admin/projects/1/confirmations", json=[])
    assert resp.status_code == 401


def test_legacy_confirmation_endpoint_is_disabled(client, monkeypatch):
    student_headers = _student_headers(client, 303)
    admin_headers = _admin_headers(client, monkeypatch)
    project, _application = _apply_and_accept(client, student_headers, admin_headers)
    response = client.post(
        f"/admin/projects/{project['id']}/confirmations",
        headers=admin_headers,
        json=[],
    )
    assert response.status_code == 410


def test_legacy_complete_endpoint_is_disabled(client, monkeypatch):
    student_headers = _student_headers(client, 304)
    admin_headers = _admin_headers(client, monkeypatch)
    project, _application = _apply_and_accept(client, student_headers, admin_headers)
    response = client.post(
        f"/admin/projects/{project['id']}/complete",
        headers=admin_headers,
        json={"title": "Result", "description": "Done"},
    )
    assert response.status_code == 410


def _complete_and_confirm(client, student_headers, admin_headers, project):
    """Drives a project to the state where the student has a real portfolio."""
    _submit_and_approve(client, student_headers, admin_headers, project)
    team = client.get(f"/admin/projects/{project['id']}/team", headers=admin_headers).json()
    member = team["members"][0]
    resp = _finalize(client, admin_headers, project, member)
    assert resp.status_code == 200
    return member["user"]["id"]


def test_public_portfolio_link_and_view(client, monkeypatch):
    student_headers = _student_headers(client, 311)
    admin_headers = _admin_headers(client, monkeypatch)
    project, application = _apply_and_accept(client, student_headers, admin_headers)
    _complete_and_confirm(client, student_headers, admin_headers, project)

    resp = client.post("/me/portfolio/link", headers=student_headers)
    assert resp.status_code == 200
    slug = resp.json()["slug"]
    # Slugs are readable, latin, and unique per student.
    assert slug.startswith("student-")

    # The public page needs no auth — that is the whole point.
    public = client.get(f"/p/{slug}")
    assert public.status_code == 200
    body = public.json()
    assert body["name"] == "Студент"
    assert body["projects"][0]["project_title"] == project["title"]
    assert body["projects"][0]["organization"] == project["organization"]["name"]
    assert body["projects"][0]["role"] == application["project_role"]["title"]
    assert body["projects"][0]["result"]["title"] == "Рабочий прототип бота"
    # Contact details never leak to the public view.
    assert "university" not in body
    assert "goal" not in body


def test_portfolio_link_is_idempotent(client):
    headers = _student_headers(client, 312)
    first = client.post("/me/portfolio/link", headers=headers).json()["slug"]
    second = client.post("/me/portfolio/link", headers=headers).json()["slug"]
    assert first == second


def test_public_portfolio_for_empty_student(client):
    headers = _student_headers(client, 313)
    slug = client.post("/me/portfolio/link", headers=headers).json()["slug"]
    public = client.get(f"/p/{slug}")
    assert public.status_code == 200
    assert public.json()["projects"] == []


def test_public_portfolio_unknown_slug_is_404(client):
    assert client.get("/p/does-not-exist").status_code == 404


def test_creating_portfolio_link_requires_auth(client):
    assert client.post("/me/portfolio/link").status_code == 401
