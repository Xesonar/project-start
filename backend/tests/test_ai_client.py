import httpx
import pytest

from app.core.config import settings
from app.services import ai_client


def test_returns_none_without_api_key(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "")
    assert ai_client.explain_recommendations("profile", [{"project_id": 1}]) is None


def test_returns_none_with_no_candidates(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")
    assert ai_client.explain_recommendations("profile", []) is None


def test_returns_none_on_request_failure(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")

    def raise_timeout(*args, **kwargs):
        raise httpx.ConnectTimeout("boom")

    monkeypatch.setattr(ai_client.httpx, "post", raise_timeout)
    result = ai_client.explain_recommendations("profile", [{"project_id": 1, "title": "X"}])
    assert result is None


def test_parses_valid_response(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"items": [{"project_id": 1, "reason": "Подходит по навыкам"}]}'
                        }
                    }
                ]
            }

    monkeypatch.setattr(ai_client.httpx, "post", lambda *a, **kw: FakeResponse())
    result = ai_client.explain_recommendations("profile", [{"project_id": 1, "title": "X"}])
    assert result == [{"project_id": 1, "reason": "Подходит по навыкам"}]


def test_drops_project_ids_not_in_candidates(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"items": [{"project_id": 999, "reason": "X"}]}'
                        }
                    }
                ]
            }

    monkeypatch.setattr(ai_client.httpx, "post", lambda *a, **kw: FakeResponse())
    result = ai_client.explain_recommendations("profile", [{"project_id": 1, "title": "X"}])
    assert result is None
