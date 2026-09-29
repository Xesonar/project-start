"""Thin client for the MAX Bot API (platform-api2.max.ru).

Same resilience philosophy as ai_client.py: a bot-chat hiccup must never
break the underlying action it's attached to (e.g. accepting an
application). send_message/answer_callback/edit_message log and swallow
errors, returning bool success rather than raising, so callers can choose
to ignore the result for best-effort notifications.
"""

import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_TIMEOUT_SECONDS = 8.0


def _auth_headers() -> dict:
    # Query-param token passing is no longer supported by MAX (verified
    # against the real API) — the bot token goes in the Authorization
    # header, unprefixed (not "Bearer <token>").
    return {"Authorization": settings.max_bot_token}


def send_message(
    *,
    text: str,
    user_id: int | None = None,
    chat_id: int | None = None,
    buttons: list[list[dict]] | None = None,
) -> dict | None:
    """Send a message to exactly one private user or MAX group chat."""
    if (user_id is None) == (chat_id is None):
        raise ValueError("send_message needs exactly one of user_id or chat_id")
    body: dict = {"text": text}
    if buttons:
        body["attachments"] = [{"type": "inline_keyboard", "payload": {"buttons": buttons}}]
    recipient = {"user_id": user_id} if user_id is not None else {"chat_id": chat_id}

    try:
        response = httpx.post(
            f"{settings.max_bot_api_base_url}/messages",
            params=recipient,
            headers=_auth_headers(),
            json=body,
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        logger.exception("MAX send_message failed (recipient=%s)", recipient)
        return None


def answer_callback(*, callback_id: str, text: str, buttons: list[list[dict]] | None = None) -> bool:
    """Responds to a button click by editing the message it was attached
    to in place (see dev.max.ru POST /answers — no separate PUT needed)."""
    message: dict = {"text": text}
    if buttons:
        message["attachments"] = [{"type": "inline_keyboard", "payload": {"buttons": buttons}}]

    try:
        response = httpx.post(
            f"{settings.max_bot_api_base_url}/answers",
            params={"callback_id": callback_id},
            headers=_auth_headers(),
            json={"message": message},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("success") is not True:
            logger.error(
                "MAX answer_callback returned success=false (callback_id=%s): %s",
                callback_id,
                payload,
            )
            return False
        return True
    except Exception:
        logger.exception("MAX answer_callback failed (callback_id=%s)", callback_id)
        return False


def subscribe(*, webhook_url: str, secret: str, update_types: list[str]) -> bool:
    try:
        response = httpx.post(
            f"{settings.max_bot_api_base_url}/subscriptions",
            headers=_auth_headers(),
            json={"url": webhook_url, "update_types": update_types, "secret": secret},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("success") is not True:
            logger.error("MAX webhook subscription returned success=false: %s", payload)
            return False
        logger.info("MAX webhook subscription response: %s", payload)
        return True
    except Exception:
        logger.exception("MAX webhook subscription failed")
        return False


def update_commands(commands: list[dict[str, str]]) -> bool:
    """Publish slash commands in the MAX client, replacing the previous set."""
    try:
        response = httpx.patch(
            f"{settings.max_bot_api_base_url}/me/commands",
            headers=_auth_headers(),
            json={"commands": commands},
            timeout=_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
        # Unlike /subscriptions, PATCH /me/commands returns the resulting
        # commands array rather than a SimpleQueryResult on the live API.
        # Accept both documented response shapes and reject only an explicit
        # failure or a malformed success response.
        if payload.get("success") is False:
            logger.error("MAX update_commands returned success=false: %s", payload)
            return False
        if payload.get("success") is True or isinstance(payload.get("commands"), list):
            return True
        logger.error("MAX update_commands returned unexpected payload: %s", payload)
        return False
    except Exception:
        logger.exception("MAX update_commands failed")
        return False
