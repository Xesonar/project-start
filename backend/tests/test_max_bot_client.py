from app.core.config import settings
from app.services import max_bot_client


class _FakeResponse:
    def __init__(self, payload: dict):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def test_answer_callback_rejects_success_false(monkeypatch):
    monkeypatch.setattr(settings, "max_bot_token", "test-token")
    monkeypatch.setattr(
        max_bot_client.httpx,
        "post",
        lambda *args, **kwargs: _FakeResponse({"success": False}),
    )

    assert max_bot_client.answer_callback(callback_id="callback", text="Ответ") is False


def test_subscribe_rejects_success_false(monkeypatch):
    monkeypatch.setattr(settings, "max_bot_token", "test-token")
    monkeypatch.setattr(
        max_bot_client.httpx,
        "post",
        lambda *args, **kwargs: _FakeResponse({"success": False}),
    )

    assert (
        max_bot_client.subscribe(
            webhook_url="https://example.com/bot/webhook",
            secret="secret",
            update_types=["message_callback"],
        )
        is False
    )
