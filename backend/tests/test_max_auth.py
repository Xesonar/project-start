import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.core.config import settings
from app.services.max_auth import InitDataError, validate_init_data

BOT_TOKEN = "test-bot-token"


def build_init_data(*, user: dict, auth_date: int | None = None, bad_signature: bool = False) -> str:
    fields = {
        "user": json.dumps(user, separators=(",", ":")),
        "auth_date": str(auth_date if auth_date is not None else int(time.time())),
        "query_id": "abc123",
    }
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    signature = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    if bad_signature:
        signature = "0" * 64
    fields["hash"] = signature
    return urlencode(fields)


@pytest.fixture(autouse=True)
def _bot_token(monkeypatch):
    monkeypatch.setattr(settings, "max_bot_token", BOT_TOKEN)
    monkeypatch.setattr(settings, "max_init_data_max_age_seconds", 3600)


def test_valid_init_data_returns_user():
    init_data = build_init_data(user={"id": 42, "first_name": "Аня"})
    user = validate_init_data(init_data)
    assert user["id"] == 42
    assert user["first_name"] == "Аня"


def test_tampered_signature_is_rejected():
    init_data = build_init_data(user={"id": 42}, bad_signature=True)
    with pytest.raises(InitDataError, match="signature mismatch"):
        validate_init_data(init_data)


def test_expired_auth_date_is_rejected():
    init_data = build_init_data(user={"id": 42}, auth_date=int(time.time()) - 7200)
    with pytest.raises(InitDataError, match="expired"):
        validate_init_data(init_data)


def test_missing_hash_is_rejected():
    with pytest.raises(InitDataError, match="missing hash"):
        validate_init_data(urlencode({"user": json.dumps({"id": 1})}))


def test_missing_user_is_rejected():
    fields = {"auth_date": str(int(time.time()))}
    check_string = "\n".join(f"{k}={v}" for k, v in sorted(fields.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()
    with pytest.raises(InitDataError, match="missing user"):
        validate_init_data(urlencode(fields))


def test_empty_bot_token_is_rejected(monkeypatch):
    monkeypatch.setattr(settings, "max_bot_token", "")
    init_data = build_init_data(user={"id": 42})
    with pytest.raises(InitDataError, match="not configured"):
        validate_init_data(init_data)


def test_duplicate_fields_are_rejected():
    init_data = build_init_data(user={"id": 42})
    with pytest.raises(InitDataError, match="duplicate"):
        validate_init_data(f"{init_data}&user=%7B%22id%22%3A43%7D")


@pytest.mark.parametrize("user", [["id"], {"id": "not-a-number"}, {"id": 0}, {"id": True}])
def test_invalid_user_shape_or_id_is_rejected(user):
    init_data = build_init_data(user=user)
    with pytest.raises(InitDataError, match="invalid user"):
        validate_init_data(init_data)
