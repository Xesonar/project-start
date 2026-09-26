#!/usr/bin/env bash
set -e

until python -c "from app.db.session import engine; engine.connect()" 2>/dev/null; do
  echo "Waiting for database..."
  sleep 1
done

alembic upgrade head
python -m app.seed.run_seed

exec "$@"
