"""Persistent delivery queue for messages that MAX did not accept immediately."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.notification import BotNotification
from app.services import max_bot_client

logger = logging.getLogger(__name__)


def queue_failed_notification(*, user_id: int, text: str, buttons: list | None) -> None:
    with SessionLocal() as db:
        db.add(BotNotification(user_id=user_id, text=text, buttons=buttons))
        db.commit()


def deliver_pending_notifications(*, limit: int = 50) -> int:
    """Retries due notifications; exponential backoff is capped at one hour."""
    now = datetime.now(timezone.utc)
    delivered_count = 0
    with SessionLocal() as db:
        pending = list(
            db.scalars(
                select(BotNotification)
                .where(
                    BotNotification.status == "pending",
                    BotNotification.next_attempt_at <= now,
                )
                .order_by(BotNotification.created_at)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        for item in pending:
            response = max_bot_client.send_message(
                user_id=item.user.max_user_id,
                text=item.text,
                buttons=item.buttons,
            )
            item.attempts += 1
            if response is not None:
                item.status = "delivered"
                item.delivered_at = now
                item.last_error = None
                delivered_count += 1
            else:
                delay = min(3600, 15 * (2 ** min(item.attempts, 8)))
                item.next_attempt_at = now + timedelta(seconds=delay)
                item.last_error = "MAX API не подтвердил доставку"
        db.commit()
    if pending:
        logger.info("MAX outbox: delivered %s of %s due messages", delivered_count, len(pending))
    return delivered_count
