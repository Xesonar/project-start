# Тестирование backend

Тесты используют **отдельную** базу `project_start_test` на том же Postgres,
что поднимает `docker-compose` (`localhost:5432`) — не путать с `project_start`,
которую видит dev/demo-стек через браузер. `tests/conftest.py` чистит все
таблицы перед каждым тестом (`TRUNCATE ... CASCADE`), поэтому направлять его
на `project_start` нельзя: любой прогон тестов сотрёт то, что накликано в
браузере для демонстрации.

## Разовая подготовка

```bash
docker compose up -d db
docker compose exec db psql -U project_start -d project_start -c "CREATE DATABASE project_start_test"
cd backend
source .venv/bin/activate  # или свой способ активации окружения
DATABASE_URL="postgresql+psycopg://project_start:project_start@localhost:5432/project_start_test" \
  alembic upgrade head
```

## Запуск

```bash
cd backend
source .venv/bin/activate
python -m pytest
```

`DATABASE_URL` можно не указывать — `conftest.py` сам подставит адрес
`project_start_test`. Если тестовая БД ещё не создана или не мигрирована,
тесты упадут на первом же обращении к БД — тогда выполните шаги выше.

После добавления новой Alembic-миграции применяйте её к `project_start_test`
так же, как к `project_start`, иначе тесты начнут падать на несуществующих
колонках/таблицах.

## Фронтенд

Логика скоринга навыков (`frontend/src/lib/match.test.mts`) гоняется встроенным
раннером Node 22 (`--experimental-strip-types`) — без vitest/jest, чтобы не
тянуть зависимости ради небольшого набора unit-тестов:

```bash
cd frontend && npm test
```

Тест-файлы исключены из `tsc` (в них node-импорты), их проверяет CI.
