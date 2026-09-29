from tests.test_max_auth import build_init_data


def test_full_auth_and_profile_flow(client):
    init_data = build_init_data(user={"id": 777, "first_name": "Ира", "last_name": "С."})

    resp = client.post("/auth/max", json={"init_data": init_data})
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/me", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "Ира С."
    assert body["profile"] is None
    assert body["xp"] == 0
    assert body["level"] == 1
    assert body["next_level_xp"] == 100

    resp = client.patch(
        "/me/profile",
        headers=headers,
        json={"specialty": "Разработка", "experience_level": "beginner", "goal": "Найти первый проект"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["profile"]["specialty"] == "Разработка"

def test_auth_without_token_is_rejected(client):
    resp = client.get("/me")
    assert resp.status_code == 401


def test_admin_login_requires_correct_password(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "admin_password", "secret")

    resp = client.post("/admin/login", json={"password": "wrong"})
    assert resp.status_code == 401

    resp = client.post("/admin/login", json={"password": "secret"})
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_admin_login_is_rate_limited(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "admin_password", "secret")
    monkeypatch.setattr(settings, "auth_rate_limit_per_minute", 2)

    assert client.post("/admin/login", json={"password": "wrong"}).status_code == 401
    assert client.post("/admin/login", json={"password": "wrong"}).status_code == 401
    limited = client.post("/admin/login", json={"password": "secret"})
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) >= 1
