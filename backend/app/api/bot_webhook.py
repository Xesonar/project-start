import logging
import hmac

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.bot import assistant, screens
from app.bot.payload import decode
from app.core.config import settings
from app.core.request_guard import client_ip, request_guard, stable_event_key
from app.db.session import get_db
from app.services import max_bot_client
from app.services.user_upsert import upsert_max_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["bot"])


def _extract_user(body: dict) -> dict | None:
    """MAX puts `user` at different nesting per update type — top-level for
    bot_started, nested under `callback` for message_callback (verified
    against the max-bot-api-client-go struct tags, since dev.max.ru's own
    prose docs don't spell this out)."""
    update_type = body.get("update_type")
    if update_type == "message_callback":
        return (body.get("callback") or {}).get("user")
    if update_type == "message_created":
        return (body.get("message") or {}).get("sender")
    return body.get("user")


def _message_context(body: dict) -> tuple[bool, int | None, str | None]:
    """Return private/group scope, destination chat id, and text for a message event."""
    message = body.get("message") or {}
    recipient = message.get("recipient") or {}
    chat_type = recipient.get("chat_type")
    is_private = chat_type in {None, "dialog"}
    raw_chat_id = recipient.get("chat_id")
    try:
        chat_id = int(raw_chat_id) if raw_chat_id is not None else None
    except (TypeError, ValueError):
        chat_id = None
    text = (message.get("body") or {}).get("text")
    return is_private, chat_id, text if isinstance(text, str) else None


@router.post("/bot/webhook")
def bot_webhook(
    body: dict,
    request: Request,
    db: Session = Depends(get_db),
    x_max_bot_api_secret: str | None = Header(default=None),
) -> dict:
    if not settings.max_bot_webhook_secret or not x_max_bot_api_secret or not hmac.compare_digest(
        x_max_bot_api_secret, settings.max_bot_webhook_secret
    ):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный секрет вебхука")

    request_guard.enforce_rate(
        f"max-webhook:{client_ip(request)}",
        limit=settings.webhook_rate_limit_per_minute,
        window_seconds=60,
    )

    update_type = body.get("update_type")
    max_user = _extract_user(body)
    if not max_user or max_user.get("user_id") is None:
        return {"ok": True}

    try:
        max_user_id = int(max_user["user_id"])
    except (TypeError, ValueError):
        logger.warning("Ignoring MAX update with malformed user_id")
        return {"ok": True}
    if max_user_id <= 0:
        logger.warning("Ignoring MAX update with non-positive user_id")
        return {"ok": True}

    event_key = stable_event_key(body)
    if not request_guard.first_event(
        event_key,
        ttl_seconds=settings.webhook_dedup_ttl_seconds,
    ):
        logger.info("Ignoring duplicate MAX update")
        return {"ok": True, "duplicate": True}

    try:
        user = upsert_max_user(
            db,
            max_user_id=max_user_id,
            first_name=max_user.get("first_name") or max_user.get("name"),
            last_name=max_user.get("last_name"),
            username=max_user.get("username"),
        )

        if update_type == "bot_started":
            text, buttons = screens.build_home(db, user)
            delivered = max_bot_client.send_message(
                user_id=user.max_user_id, text=text, buttons=buttons
            )
            if delivered is None:
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    "MAX API временно недоступен",
                )
            return {"ok": True}

        if update_type == "message_callback":
            callback = body.get("callback") or {}
            callback_id = callback.get("callback_id")
            raw_payload = callback.get("payload") or ""
            if callback_id:
                is_private, _chat_id, _text = _message_context(body)
                if is_private:
                    text, buttons = screens.route(db, user, decode(raw_payload))
                else:
                    text = "Личные действия доступны в диалоге с ботом. Напиши мне напрямую."
                    buttons = None
                delivered = max_bot_client.answer_callback(
                    callback_id=callback_id, text=text, buttons=buttons
                )
                if not delivered:
                    raise HTTPException(
                        status.HTTP_502_BAD_GATEWAY,
                        "MAX API временно недоступен",
                    )
            return {"ok": True}

        if update_type == "message_created":
            is_private, chat_id, message_text = _message_context(body)
            if not message_text or not message_text.strip():
                response_text = "Пока я понимаю только текстовые сообщения. Напиши вопрос или /help."
                buttons = [[screens._HOME_BUTTON]] if is_private else None
            else:
                response_text, buttons = assistant.handle_text(
                    db,
                    user=user,
                    text=message_text,
                    is_private=is_private,
                    chat_id=chat_id,
                )
            delivered = max_bot_client.send_message(
                user_id=user.max_user_id if is_private else None,
                chat_id=chat_id if not is_private else None,
                text=response_text,
                buttons=buttons,
            )
            if delivered is None:
                raise HTTPException(
                    status.HTTP_502_BAD_GATEWAY,
                    "MAX API временно недоступен",
                )
            return {"ok": True}

        return {"ok": True}
    except Exception:
        db.rollback()
        request_guard.forget_event(event_key)
        raise
