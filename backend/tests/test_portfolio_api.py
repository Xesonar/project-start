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


def test_full_completion_and_portfolio_flow(client, monkeypatch):
    student_headers = _student_headers(client, 301)
    admin_headers = _admin_headers(client, monkeypatch)
    project, _application = _apply_and_accept(client, student_headers, admin_headers)

    resp = client.post(
        f"/admin/projects/{project['id']}/complete",
        headers=admin_headers,
        json={
            "title": "Рабочий прототип бота",
            "description": "Бот запущен и протестирован с реальными данными.",
            "result_url": "https://example.com/demo",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    team = client.get(f"/admin/projects/{project['id']}/team", headers=admin_headers).json()
    user_id = team["members"][0]["user"]["id"]

    resp = client.post(
        f"/admin/projects/{project['id']}/confirmations",
        headers=admin_headers,
        json=[{"user_id": user_id, "role": "Backend developer", "contribution": "Написал API бота"}],
    )
    assert resp.status_code == 200
    assert resp.json()[0]["role"] == "Backend developer"

    # Completed work belongs in the portfolio, not in the active-team tab.
    assert client.get("/me/team", headers=student_headers).status_code == 404

    resp = client.get("/me/portfolio", headers=student_headers)
    assert resp.status_code == 200
    portfolio = resp.json()
    assert len(portfolio) == 1
    assert portfolio[0]["project"]["id"] == project["id"]
    assert portfolio[0]["result"]["title"] == "Рабочий прототип бота"
    assert portfolio[0]["confirmation"]["contribution"] == "Написал API бота"


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


def test_atomic_finalize_populates_portfolio(client, monkeypatch):
    student_headers = _student_headers(client, 306)
    admin_headers = _admin_headers(client, monkeypatch)
    project, _application = _apply_and_accept(client, student_headers, admin_headers)
    team = client.get(f"/admin/projects/{project['id']}/team", headers=admin_headers).json()
    member = team["members"][0]

    response = client.post(
        f"/admin/projects/{project['id']}/finalize",
        headers=admin_headers,
        json={
            "result": {"title": "Result", "description": "Done"},
            "confirmations": [
                {
                    "user_id": member["user"]["id"],
                    "role": member["role_title"],
                    "contribution": "Built the prototype",
                }
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert client.get("/me/team", headers=student_headers).status_code == 404
    assert client.get("/me/portfolio", headers=student_headers).json()[0]["result"]["title"] == "Result"


def test_portfolio_empty_before_confirmation(client):
    headers = _student_headers(client, 302)
    resp = client.get("/me/portfolio", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == []


def test_confirmations_require_admin(client):
    resp = client.post("/admin/projects/1/confirmations", json=[])
    assert resp.status_code == 401


def test_confirmation_requires_completed_project(client, monkeypatch):
    student_headers = _student_headers(client, 303)
    admin_headers = _admin_headers(client, monkeypatch)
    project, _application = _apply_and_accept(client, student_headers, admin_headers)
    team = client.get(f"/admin/projects/{project['id']}/team", headers=admin_headers).json()

    response = client.post(
        f"/admin/projects/{project['id']}/confirmations",
        headers=admin_headers,
        json=[{"user_id": team["members"][0]["user"]["id"], "role": "Developer"}],
    )
    assert response.status_code == 400


def test_confirmation_rejects_user_outside_project_team(client, monkeypatch):
    student_headers = _student_headers(client, 304)
    admin_headers = _admin_headers(client, monkeypatch)
    project, _application = _apply_and_accept(client, student_headers, admin_headers)
    client.post(
        f"/admin/projects/{project['id']}/complete",
        headers=admin_headers,
        json={"title": "Result", "description": "Done"},
    )

    response = client.post(
        f"/admin/projects/{project['id']}/confirmations",
        headers=admin_headers,
        json=[{"user_id": 999999, "role": "Developer"}],
    )
    assert response.status_code == 400


def _complete_and_confirm(client, student_headers, admin_headers, project):
    """Drives a project to the state where the student has a real portfolio."""
    resp = client.post(
        f"/admin/projects/{project['id']}/complete",
        headers=admin_headers,
        json={
            "title": "Рабочий прототип бота",
            "description": "Бот запущен и протестирован с реальными данными.",
            "result_url": "https://example.com/demo",
        },
    )
    assert resp.status_code == 200
    team = client.get(f"/admin/projects/{project['id']}/team", headers=admin_headers).json()
    user_id = team["members"][0]["user"]["id"]
    resp = client.post(
        f"/admin/projects/{project['id']}/confirmations",
        headers=admin_headers,
        json=[{"user_id": user_id, "role": "Backend developer", "contribution": "Написал API бота"}],
    )
    assert resp.status_code == 200
    return user_id


def test_public_portfolio_link_and_view(client, monkeypatch):
    student_headers = _student_headers(client, 311)
    admin_headers = _admin_headers(client, monkeypatch)
    project, _application = _apply_and_accept(client, student_headers, admin_headers)
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
    assert body["projects"][0]["role"] == "Backend developer"
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
