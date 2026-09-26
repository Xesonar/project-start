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
