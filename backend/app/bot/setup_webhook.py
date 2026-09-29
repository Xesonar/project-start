"""One-off script: registers our webhook URL with MAX (POST /subscriptions).

Run once per environment after MAX_BOT_WEBHOOK_SECRET and the public URL
are known, e.g. inside the deployed backend container:
    docker compose -f docker-compose.prod.yml exec backend \
        python -m app.bot.setup_webhook https://your-domain.example/api/bot/webhook
"""

import sys

from app.core.config import settings
from app.services import max_bot_client

UPDATE_TYPES = ["bot_started", "message_callback", "message_created"]
BOT_COMMANDS = [
    {"name": "start", "description": "Открыть главное меню"},
    {"name": "menu", "description": "Главное меню"},
    {"name": "projects", "description": "Открытые проекты"},
    {"name": "applications", "description": "Мои отклики"},
    {"name": "team", "description": "Моя команда"},
    {"name": "profile", "description": "Мой профиль"},
    {"name": "admin", "description": "Открыть админку"},
    {"name": "clear", "description": "Очистить контекст диалога"},
    {"name": "help", "description": "Помощь"},
]


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

    subscribed = max_bot_client.subscribe(
        webhook_url=webhook_url,
        secret=settings.max_bot_webhook_secret,
        update_types=UPDATE_TYPES,
    )
    commands_updated = max_bot_client.update_commands(BOT_COMMANDS)
    if subscribed and commands_updated:
        print(f"Subscribed and commands updated: {webhook_url}")
    else:
        print("Subscription or command setup failed — check logs above.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
