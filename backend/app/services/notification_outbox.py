"""Persistent delivery queue for messages that MAX did not accept immediately."""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models.notification import BotNotification
from app.services import max_bot_client

logger = logging.getLogger(__name__)


def queue_failed_notification(*, user_id: int, text: str, buttons: list | None) -> bool:
    with SessionLocal() as db:
        try:
            db.add(BotNotification(user_id=user_id, text=text, buttons=buttons))
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            logger.exception("Could not persist MAX notification (user_id=%s)", user_id)
            return False
    return True


def deliver_pending_notifications(*, limit: int = 50) -> int:
    """Retry due notifications without keeping DB locks during network I/O.

    Rows get a short lease through ``next_attempt_at``. If the worker dies
    after claiming them, another worker retries them when the lease expires.
    """
    now = datetime.now(timezone.utc)
    lease_until = now + timedelta(minutes=5)
    delivered_count = 0
    claimed: list[tuple[int, int, str, list | None]] = []

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
            claimed.append((item.id, item.user.max_user_id, item.text, item.buttons))
            item.next_attempt_at = lease_until
        db.commit()

    for item_id, max_user_id, text, buttons in claimed:
        response = max_bot_client.send_message(
            user_id=max_user_id,
            text=text,
            buttons=buttons,
        )
        attempted_at = datetime.now(timezone.utc)
        with SessionLocal() as db:
            item = db.scalar(
                select(BotNotification)
                .where(BotNotification.id == item_id)
                .with_for_update()
            )
            if item is None or item.status != "pending":
                continue
            item.attempts += 1
            if response is not None:
                item.status = "delivered"
                item.delivered_at = attempted_at
                item.last_error = None
                delivered_count += 1
            else:
                delay = min(3600, 15 * (2 ** min(item.attempts, 8)))
                item.next_attempt_at = attempted_at + timedelta(seconds=delay)
                item.last_error = "MAX API не подтвердил доставку"
            db.commit()
    if claimed:
        logger.info("MAX outbox: delivered %s of %s due messages", delivered_count, len(claimed))
    return delivered_count
