import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api import admin, applications, auth, bot_webhook, portfolio, projects, submissions, teams, users
from app.core.config import settings
from app.db.session import get_db
from app.services.notification_outbox import deliver_pending_notifications

_outbox_stop = threading.Event()


def _outbox_worker() -> None:
    while not _outbox_stop.wait(settings.notification_retry_seconds):
        try:
            deliver_pending_notifications()
        except Exception:
            # A retry worker must never stop the API process. The next tick
            # retries the same persisted rows.
            continue


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if settings.app_env.lower() in {"production", "prod"}:
        _outbox_stop.clear()
        threading.Thread(target=_outbox_worker, daemon=True, name="max-outbox").start()
    try:
        yield
    finally:
        _outbox_stop.set()


app = FastAPI(title="Старт API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(projects.router)
app.include_router(applications.router)
app.include_router(teams.router)
app.include_router(admin.router)
app.include_router(portfolio.router)
app.include_router(submissions.router)
app.include_router(bot_webhook.router)


@app.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "База данных недоступна") from exc
    return {"status": "ok"}
