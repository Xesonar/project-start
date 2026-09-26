"""One-off script: registers our webhook URL with MAX (POST /subscriptions).

Run once per environment after MAX_BOT_WEBHOOK_SECRET and the public URL
are known, e.g. inside the deployed backend container:
    docker compose -f docker-compose.prod.yml exec backend \
        python -m app.bot.setup_webhook https://your-domain.example/api/bot/webhook
"""

import sys

from app.core.config import settings
from app.services.max_bot_client import subscribe

UPDATE_TYPES = ["bot_started", "message_callback"]


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m app.bot.setup_webhook https://your-domain.example/api/bot/webhook")
        raise SystemExit(1)
    webhook_url = sys.argv[1]

    if not settings.max_bot_token:
        print("MAX_BOT_TOKEN is not set — aborting.")
        raise SystemExit(1)
    if not settings.max_bot_webhook_secret:
        print("MAX_BOT_WEBHOOK_SECRET is not set — aborting.")
        raise SystemExit(1)

    ok = subscribe(webhook_url=webhook_url, secret=settings.max_bot_webhook_secret, update_types=UPDATE_TYPES)
    if ok:
        print(f"Subscribed: {webhook_url}")
    else:
        print("Subscription failed — check logs above.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
