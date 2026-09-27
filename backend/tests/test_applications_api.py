from tests.test_max_auth import build_init_data


def _login(client, max_user_id: int) -> dict:
    init_data = build_init_data(user={"id": max_user_id, "first_name": "Студент"})
    resp = client.post("/auth/max", json={"init_data": init_data})
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _first_project_with_role(client, headers):
    from app.seed.run_seed import main as run_seed

    run_seed()
    project = client.get("/projects").json()[0]
    detail = client.get(f"/projects/{project['id']}").json()
    return detail, detail["roles"][0]["id"]


def test_apply_to_project_and_list_my_applications(client):
    headers = _login(client, 111)
    project, role_id = _first_project_with_role(client, headers)

    resp = client.post(
        f"/projects/{project['id']}/applications",
        headers=headers,
        json={"project_role_id": role_id, "message": "Хочу участвовать"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "pending"
    assert body["project_role"]["id"] == role_id

    resp = client.get("/me/applications", headers=headers)
    assert resp.status_code == 200
    apps = resp.json()
    assert len(apps) == 1
    assert apps[0]["project"]["id"] == project["id"]


def test_duplicate_application_for_same_role_is_rejected(client):
    headers = _login(client, 112)
    project, role_id = _first_project_with_role(client, headers)

    client.post(
        f"/projects/{project['id']}/applications", headers=headers, json={"project_role_id": role_id}
    )
    resp = client.post(
        f"/projects/{project['id']}/applications", headers=headers, json={"project_role_id": role_id}
    )
    assert resp.status_code == 409


def test_application_to_role_from_another_project_is_rejected(client):
    headers = _login(client, 113)
    from app.seed.run_seed import main as run_seed

    run_seed()
    projects = client.get("/projects").json()
    other_project_detail = client.get(f"/projects/{projects[1]['id']}").json()
    other_role_id = other_project_detail["roles"][0]["id"]

    resp = client.post(
        f"/projects/{projects[0]['id']}/applications",
        headers=headers,
        json={"project_role_id": other_role_id},
    )
    assert resp.status_code == 400


def test_apply_without_auth_is_rejected(client):
    from app.seed.run_seed import main as run_seed

    run_seed()
    project = client.get("/projects").json()[0]
    resp = client.post(f"/projects/{project['id']}/applications", json={"project_role_id": 1})
    assert resp.status_code == 401


def test_student_can_withdraw_pending_application_and_apply_again(client):
    headers = _login(client, 114)
    project, role_id = _first_project_with_role(client, headers)
    created = client.post(
        f"/projects/{project['id']}/applications",
        headers=headers,
        json={"project_role_id": role_id, "message": "Первый отклик"},
    ).json()

    withdrawn = client.delete(f"/me/applications/{created['id']}", headers=headers)
    assert withdrawn.status_code == 204
    applications = client.get("/me/applications", headers=headers).json()
    assert applications[0]["status"] == "withdrawn"

    reapplied = client.post(
        f"/projects/{project['id']}/applications",
        headers=headers,
        json={"project_role_id": role_id, "message": "Передумал, хочу участвовать"},
    )
    assert reapplied.status_code == 201, reapplied.text
    assert reapplied.json()["id"] == created["id"]
    assert reapplied.json()["status"] == "pending"
    assert reapplied.json()["message"] == "Передумал, хочу участвовать"


def test_student_cannot_withdraw_another_students_application(client):
    owner_headers = _login(client, 115)
    stranger_headers = _login(client, 116)
    project, role_id = _first_project_with_role(client, owner_headers)
    created = client.post(
        f"/projects/{project['id']}/applications",
        headers=owner_headers,
        json={"project_role_id": role_id},
    ).json()

    response = client.delete(f"/me/applications/{created['id']}", headers=stranger_headers)
    assert response.status_code == 404


def test_withdraw_is_idempotent(client):
    headers = _login(client, 117)
    project, role_id = _first_project_with_role(client, headers)
    created = client.post(
        f"/projects/{project['id']}/applications",
        headers=headers,
        json={"project_role_id": role_id},
    ).json()

    assert client.delete(f"/me/applications/{created['id']}", headers=headers).status_code == 204
    assert client.delete(f"/me/applications/{created['id']}", headers=headers).status_code == 204
