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


def test_consult_bot_parses_structured_intent_and_profile_patch(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"reply":"Подберу проекты.","intent":"recommendations",'
                                '"profile":{"goal":"Первый проект"},'
                                '"skills":[{"name":"React","rating":3}],'
                                '"unknown_skills":["Clojure"]}'
                            )
                        }
                    }
                ]
            }

    monkeypatch.setattr(ai_client.httpx, "post", lambda *args, **kwargs: FakeResponse())
    result = ai_client.consult_bot(
        text="Хочу первый проект, знаю React",
        history=[],
        platform_context={"open_projects": []},
        is_private=True,
    )
    assert result is not None
    assert result.intent == "recommendations"
    assert result.profile == {"goal": "Первый проект"}
    assert result.skills == [{"name": "React", "rating": 3}]


def test_consult_bot_drops_profile_data_in_group(monkeypatch):
    monkeypatch.setattr(settings, "deepseek_api_key", "test-key")

    class FakeResponse:
        def raise_for_status(self):
            pass

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": (
                                '{"reply":"Привет!","intent":"profile",'
                                '"profile":{"goal":"Скрытая цель"},'
                                '"skills":[{"name":"React","rating":4}]}'
                            )
                        }
                    }
                ]
            }

    monkeypatch.setattr(ai_client.httpx, "post", lambda *args, **kwargs: FakeResponse())
    result = ai_client.consult_bot(
        text="Я знаю React",
        history=[],
        platform_context={"open_projects": []},
        is_private=False,
    )
    assert result is not None
    assert result.profile == {}
    assert result.skills == []
