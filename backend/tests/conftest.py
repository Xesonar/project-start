import os

# Deliberately a separate database (project_start_test), not the dev/demo one
# (project_start) that docker-compose seeds — this fixture TRUNCATEs every
# table before each test, and pointing it at the demo database wipes
# whatever you've clicked through in the browser. Same Postgres server
# (localhost:5432, the docker-compose `db` service) is fine to reuse; the
# database itself must exist first — see docs/testing.md.
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://project_start:project_start@localhost:5432/project_start_test",
)
# Tests sign initData with this fixed key. Never inherit a developer's real
# bot token from docker-compose's env_file, otherwise auth tests become
# environment-dependent and fail with misleading signature errors.
os.environ["MAX_BOT_TOKEN"] = "test-bot-token"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db.base import Base
from app.db.session import engine
from app.main import app
from app.core.request_guard import request_guard


@pytest.fixture(autouse=True)
def _clean_db():
    request_guard.clear()
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(text(f'TRUNCATE TABLE "{table.name}" CASCADE'))
    yield


@pytest.fixture()
def client():
    return TestClient(app)
