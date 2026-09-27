from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api import admin, applications, auth, bot_webhook, portfolio, projects, teams, users
from app.core.config import settings
from app.db.session import get_db

app = FastAPI(title="Старт API")

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
app.include_router(bot_webhook.router)


@app.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Database is unavailable") from exc
    return {"status": "ok"}
