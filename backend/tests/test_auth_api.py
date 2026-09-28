from tests.test_max_auth import build_init_data
import pytest
from pydantic import ValidationError

from app.core.config import Settings


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


def test_demo_auth_works_without_max(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "demo_mode", True)
    resp = client.post("/auth/demo")
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = client.get("/me", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"]  # demo student has a human-readable name
    assert body["profile"] is not None  # profile pre-filled -> instant recommendations
    assert body["profile"]["experience_level"] == "beginner"


def test_demo_auth_is_idempotent(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "demo_mode", True)
    first = client.post("/auth/demo").json()["access_token"]
    second = client.post("/auth/demo").json()["access_token"]
    # Same demo user, two separate sessions
    assert first != second
    assert client.get("/me", headers={"Authorization": f"Bearer {first}"}).status_code == 200


def test_demo_auth_isolates_browser_sessions(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "demo_mode", True)
    first = client.post("/auth/demo", json={"session_id": "browser-session-one"})
    second = client.post("/auth/demo", json={"session_id": "browser-session-two"})
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text

    first_user = client.get(
        "/me",
        headers={"Authorization": f"Bearer {first.json()['access_token']}"},
    ).json()
    second_user = client.get(
        "/me",
        headers={"Authorization": f"Bearer {second.json()['access_token']}"},
    ).json()
    assert first_user["id"] != second_user["id"]


def test_demo_auth_can_be_disabled(client, monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "demo_mode", False)
    resp = client.post("/auth/demo")
    assert resp.status_code == 403


def test_production_requires_explicit_demo_acknowledgement():
    with pytest.raises(ValidationError, match="ALLOW_PRODUCTION_DEMO"):
        Settings(
            _env_file=None,
            app_env="production",
            jwt_secret="x" * 48,
            admin_password="safe-password",
            demo_mode=True,
            allow_production_demo=False,
        )
