import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

from app.core.config import settings


class InitDataError(Exception):
    pass


def _parse_init_data(init_data: str) -> dict[str, str]:
    pairs = parse_qsl(init_data, keep_blank_values=True)
    if not pairs:
        raise InitDataError("empty init data")
    keys = [key for key, _value in pairs]
    if len(keys) != len(set(keys)):
        raise InitDataError("duplicate init data field")
    return dict(pairs)


def _build_check_string(fields: dict[str, str]) -> str:
    items = sorted((k, v) for k, v in fields.items() if k != "hash")
    return "\n".join(f"{k}={v}" for k, v in items)


def _compute_signature(check_string: str, bot_token: str) -> str:
    # Algorithm per dev.max.ru/docs/webapps/validation (structurally identical to
    # Telegram Mini Apps): secret = HMAC_SHA256(key="WebAppData", msg=bot_token),
    # signature = HMAC_SHA256(key=secret, msg=check_string).
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    return hmac.new(secret_key, check_string.encode(), hashlib.sha256).hexdigest()


def validate_init_data(init_data: str) -> dict:
    """Validates MAX Mini App initData and returns the embedded user payload.

    Raises InitDataError on any failure (bad signature, expired, malformed).
    """
    if not settings.max_bot_token.strip():
        raise InitDataError("MAX bot token is not configured")

    fields = _parse_init_data(init_data)

    received_hash = fields.get("hash")
    if not received_hash:
        raise InitDataError("missing hash")

    check_string = _build_check_string(fields)
    expected_hash = _compute_signature(check_string, settings.max_bot_token)
    if not hmac.compare_digest(expected_hash, received_hash):
        raise InitDataError("signature mismatch")

    auth_date = fields.get("auth_date")
    if not auth_date or not auth_date.isdigit():
        raise InitDataError("missing auth_date")
    age_seconds = time.time() - int(auth_date)
    if age_seconds > settings.max_init_data_max_age_seconds or age_seconds < -60:
        raise InitDataError("init data expired")

    user_raw = fields.get("user")
    if not user_raw:
        raise InitDataError("missing user")
    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        raise InitDataError("invalid user payload") from exc

    if not isinstance(user, dict):
        raise InitDataError("invalid user payload")
    if "id" not in user:
        raise InitDataError("user payload missing id")
    try:
        user_id = int(user["id"])
    except (TypeError, ValueError) as exc:
        raise InitDataError("invalid user id") from exc
    if isinstance(user["id"], bool) or user_id <= 0:
        raise InitDataError("invalid user id")
    user["id"] = user_id

    return user
