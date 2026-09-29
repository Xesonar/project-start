import pytest
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.models.application import Application
from app.models.enums import ApplicationStatus, ProjectStatus
from app.models.project import Project
from app.seed.run_seed import main as run_seed
from app.bot.screens import build_apply_result, build_project_detail
from app.services import max_bot_client
from app.bot import screens
from app.bot import assistant
from app.services import ai_client, bot_memory
from app.bot.setup_webhook import BOT_COMMANDS, UPDATE_TYPES
from tests.test_max_auth import build_init_data


class _FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"success": True}


def _mock_bot_api(monkeypatch):
    calls = []

    def fake_post(url, *, params=None, headers=None, json=None, timeout=None):
        calls.append({"url": url, "params": params, "json": json})
        return _FakeResponse()

    monkeypatch.setattr(max_bot_client.httpx, "post", fake_post)
    monkeypatch.setattr(settings, "max_bot_webhook_secret", "test-webhook-secret")
    monkeypatch.setattr(settings, "max_bot_token", "test-bot-token")
    return calls


def _headers():
    return {"X-Max-Bot-Api-Secret": "test-webhook-secret"}


def test_webhook_rejects_wrong_secret(client, monkeypatch):
    _mock_bot_api(monkeypatch)
    resp = client.post(
        "/bot/webhook",
        json={"update_type": "bot_started", "user": {"user_id": 1}},
        headers={"X-Max-Bot-Api-Secret": "wrong"},
    )
    assert resp.status_code == 401


def test_setup_includes_text_events_and_visible_commands():
    assert "message_created" in UPDATE_TYPES
    assert {item["name"] for item in BOT_COMMANDS} >= {"start", "menu", "projects", "clear"}


def test_update_commands_accepts_max_commands_response(monkeypatch):
    class CommandsResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {"commands": [{"name": "start", "description": "Старт"}]}

    monkeypatch.setattr(max_bot_client.httpx, "patch", lambda **_kwargs: CommandsResponse())
    assert max_bot_client.update_commands([{"name": "start", "description": "Старт"}])


def test_webhook_rejects_missing_secret_when_none_configured(client, monkeypatch):
    monkeypatch.setattr(settings, "max_bot_webhook_secret", "")
    resp = client.post(
        "/bot/webhook",
        json={"update_type": "bot_started", "user": {"user_id": 1}},
        headers={"X-Max-Bot-Api-Secret": "anything"},
    )
    assert resp.status_code == 401


def test_webhook_ignores_malformed_user_id(client, monkeypatch):
    calls = _mock_bot_api(monkeypatch)
    resp = client.post(
        "/bot/webhook",
        json={"update_type": "bot_started", "user": {"user_id": "not-a-number"}},
        headers=_headers(),
    )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert calls == []


def test_bot_started_creates_user_and_sends_home_menu(client, monkeypatch):
    calls = _mock_bot_api(monkeypatch)

    resp = client.post(
        "/bot/webhook",
        json={
            "update_type": "bot_started",
            "chat_id": 123,
            "user": {"user_id": 801, "first_name": "Макс", "last_name": "Тестов"},
        },
        headers=_headers(),
    )
    assert resp.status_code == 200

    db = SessionLocal()
    try:
        user = db.scalar(select(User).where(User.max_user_id == 801))
        assert user is not None
        assert user.name == "Макс Тестов"
    finally:
        db.close()

    assert len(calls) == 1
    assert calls[0]["url"].endswith("/messages")
    assert calls[0]["params"] == {"user_id": 801}
    assert "Найти проект" in str(calls[0]["json"]["attachments"])


def test_message_created_start_opens_home_menu(client, monkeypatch):
    calls = _mock_bot_api(monkeypatch)
    resp = client.post(
        "/bot/webhook",
        json={
            "update_type": "message_created",
            "message": {
                "sender": {"user_id": 810, "first_name": "Студент"},
                "recipient": {"chat_type": "dialog", "chat_id": 810},
                "body": {"mid": "message-start", "text": "/start"},
            },
        },
        headers=_headers(),
    )
    assert resp.status_code == 200
    assert calls[-1]["params"] == {"user_id": 810}
    assert "Найти проект" in str(calls[-1]["json"]["attachments"])


def test_message_created_group_replies_to_chat_without_personal_buttons(client, monkeypatch):
    calls = _mock_bot_api(monkeypatch)
    monkeypatch.setattr(
        ai_client,
        "consult_bot",
        lambda **_kwargs: ai_client.BotConsultation(
            reply="В группе тоже могу подсказать.",
            intent="chat",
            profile={},
            skills=[],
            unknown_skills=[],
        ),
    )
    resp = client.post(
        "/bot/webhook",
        json={
            "update_type": "message_created",
            "message": {
                "sender": {"user_id": 811, "first_name": "Студент"},
                "recipient": {"chat_type": "chat", "chat_id": 9911},
                "body": {"mid": "message-group", "text": "Что посоветуешь новичку?"},
            },
        },
        headers=_headers(),
    )
    assert resp.status_code == 200
    assert calls[-1]["params"] == {"chat_id": 9911}
    assert "attachments" not in calls[-1]["json"]


def test_clear_command_removes_only_current_conversation_memory(client, monkeypatch):
    calls = _mock_bot_api(monkeypatch)
    monkeypatch.setattr(
        ai_client,
        "consult_bot",
        lambda **_kwargs: ai_client.BotConsultation(
            reply="Ответ", intent="chat", profile={}, skills=[], unknown_skills=[]
        ),
    )
    message = {
        "update_type": "message_created",
        "message": {
            "sender": {"user_id": 812, "first_name": "Студент"},
            "recipient": {"chat_type": "dialog", "chat_id": 812},
            "body": {"mid": "message-memory", "text": "Привет"},
        },
    }
    assert client.post("/bot/webhook", json=message, headers=_headers()).status_code == 200
    db = SessionLocal()
    try:
        assert len(bot_memory.recent_messages(db, "user:812")) == 2
    finally:
        db.close()

    message["message"]["body"] = {"mid": "message-clear", "text": "/clear"}
    assert client.post("/bot/webhook", json=message, headers=_headers()).status_code == 200
    db = SessionLocal()
    try:
        assert bot_memory.recent_messages(db, "user:812") == []
    finally:
        db.close()
    assert calls[-1]["params"] == {"user_id": 812}


def test_webhook_and_mini_app_share_max_name(client, monkeypatch):
    """The bot and Mini App must resolve the same MAX user and real name."""
    _mock_bot_api(monkeypatch)
    resp = client.post(
        "/bot/webhook",
        json={
            "update_type": "bot_started",
            "user": {"user_id": 804, "first_name": "Максим", "last_name": "Тестов"},
        },
        headers=_headers(),
    )
    assert resp.status_code == 200

    init_data = build_init_data(
        user={"id": 804, "first_name": "Максим", "last_name": "Тестов"}
    )
    auth = client.post("/auth/max", json={"init_data": init_data})
    assert auth.status_code == 200
    me = client.get(
        "/me",
        headers={"Authorization": f"Bearer {auth.json()['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["name"] == "Максим Тестов"

    db = SessionLocal()
    try:
        users = list(db.scalars(select(User).where(User.max_user_id == 804)))
        assert len(users) == 1
    finally:
        db.close()


def test_message_callback_routes_to_my_applications(client, monkeypatch):
    calls = _mock_bot_api(monkeypatch)

    resp = client.post(
        "/bot/webhook",
        json={
            "update_type": "message_callback",
            "callback": {
                "callback_id": "cb-1",
                "payload": "a",
                "user": {"user_id": 802, "first_name": "Студент"},
            },
        },
        headers=_headers(),
    )
    assert resp.status_code == 200
    assert len(calls) == 1
    assert calls[0]["url"].endswith("/answers")
    assert calls[0]["params"] == {"callback_id": "cb-1"}
    assert "Пока нет откликов" in calls[0]["json"]["message"]["text"]


def test_duplicate_callback_is_processed_once(client, monkeypatch):
    calls = _mock_bot_api(monkeypatch)
    payload = {
        "update_type": "message_callback",
        "callback": {
            "callback_id": "cb-duplicate",
            "payload": "a",
            "user": {"user_id": 805, "first_name": "Студент"},
        },
    }

    first = client.post("/bot/webhook", json=payload, headers=_headers())
    second = client.post("/bot/webhook", json=payload, headers=_headers())

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == {"ok": True, "duplicate": True}
    assert len(calls) == 1


def test_failed_callback_can_be_retried(client, monkeypatch):
    _mock_bot_api(monkeypatch)
    original_route = screens.route
    attempts = 0

    def fail_once(*args, **kwargs):
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise RuntimeError("temporary failure")
        return original_route(*args, **kwargs)

    monkeypatch.setattr(screens, "route", fail_once)
    payload = {
        "update_type": "message_callback",
        "callback": {
            "callback_id": "cb-retry",
            "payload": "a",
            "user": {"user_id": 807, "first_name": "Студент"},
        },
    }
    with pytest.raises(RuntimeError):
        client.post("/bot/webhook", json=payload, headers=_headers())

    retried = client.post("/bot/webhook", json=payload, headers=_headers())
    assert retried.status_code == 200
    assert retried.json() == {"ok": True}
    assert attempts == 2


def test_max_delivery_failure_returns_502_and_allows_retry(client, monkeypatch):
    _mock_bot_api(monkeypatch)
    attempts = 0

    def answer_once(**kwargs):
        nonlocal attempts
        attempts += 1
        return attempts > 1

    monkeypatch.setattr(max_bot_client, "answer_callback", answer_once)
    payload = {
        "update_type": "message_callback",
        "callback": {
            "callback_id": "cb-delivery-retry",
            "payload": "a",
            "user": {"user_id": 808, "first_name": "Студент"},
        },
    }
    failed = client.post("/bot/webhook", json=payload, headers=_headers())
    retried = client.post("/bot/webhook", json=payload, headers=_headers())

    assert failed.status_code == 502
    assert retried.status_code == 200
    assert attempts == 2


def test_message_callback_apply_creates_application(client, monkeypatch):
    run_seed()
    calls = _mock_bot_api(monkeypatch)

    db = SessionLocal()
    try:
        from app.models.project import Project
        from app.models.enums import ProjectStatus

        project = db.scalar(
            select(Project).where(Project.status == ProjectStatus.open).order_by(Project.id.desc())
        )
        role_id = project.roles[0].id
    finally:
        db.close()

    resp = client.post(
        "/bot/webhook",
        json={
            "update_type": "message_callback",
            "callback": {
                "callback_id": "cb-2",
                "payload": f"apply:{project.id}:{role_id}",
                "user": {"user_id": 803, "first_name": "Студент"},
            },
        },
        headers=_headers(),
    )
    assert resp.status_code == 200
    assert "отправлен" in calls[0]["json"]["message"]["text"]

    db = SessionLocal()
    try:
        app_row = db.scalar(select(Application).where(Application.project_id == project.id))
        assert app_row is not None
    finally:
        db.close()


def test_bot_allows_reapplying_after_rejection(client):
    run_seed()
    db = SessionLocal()
    try:
        project = db.scalar(
            select(Project)
            .where(Project.status == ProjectStatus.open)
            .order_by(Project.id.desc())
        )
        user = User(max_user_id=806, name="Студент")
        db.add(user)
        db.commit()
        db.refresh(user)
        role = project.roles[0]

        first_text, _ = build_apply_result(db, user, project.id, role.id)
        assert "отправлен" in first_text
        application = db.scalar(
            select(Application).where(
                Application.user_id == user.id,
                Application.project_id == project.id,
                Application.project_role_id == role.id,
            )
        )
        application.status = ApplicationStatus.rejected
        application.decision_note = "Нужно уточнить опыт"
        db.commit()

        _detail_text, buttons = build_project_detail(db, user, project.id, 0)
        payloads = [button.get("payload") for row in buttons for button in row]
        assert f"apply:{project.id}:{role.id}" in payloads

        repeated_text, _ = build_apply_result(db, user, project.id, role.id)
        assert "отправлен" in repeated_text
        latest = db.scalar(
            select(Application)
            .where(
                Application.user_id == user.id,
                Application.project_id == project.id,
                Application.project_role_id == role.id,
            )
            .order_by(Application.created_at.desc(), Application.id.desc())
        )
        assert latest.id != application.id
        assert latest.status == ApplicationStatus.pending
        assert application.status == ApplicationStatus.rejected
        assert application.decision_note == "Нужно уточнить опыт"
    finally:
        db.close()


def test_ai_profile_patch_merges_explicit_fields_and_known_skills(client):
    run_seed()
    user = User(max_user_id=899, name="Студент")
    db = SessionLocal()
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        consultation = ai_client.BotConsultation(
            reply="",
            intent="chat",
            profile={"preferred_role": "Frontend developer", "goal": "Собрать портфолио"},
            skills=[{"name": "React", "rating": 3}],
            unknown_skills=["Clojure"],
        )
        changed = assistant._merge_profile(db, user, consultation)
        db.refresh(user)
        assert "preferred_role" in changed
        assert user.profile.goal == "Собрать портфолио"
        assert any(item.skill.name == "React" and item.rating == 3 for item in user.skills)
        assert "Clojure" in user.profile.about
    finally:
        db.close()
