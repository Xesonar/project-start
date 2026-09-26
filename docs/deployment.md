# Деплой на VPS

Для публичного окружения нужен HTTPS-домен. Контейнеры не занимают публичные
`80/443`: перед ними ставится системный nginx, который проксирует по
`server_name`.

## Архитектура на сервере

```
Интернет
  → системный nginx (80/443, общий для всех сервисов на сервере)
      → /api/*  → 127.0.0.1:18085 (backend, наш контейнер)
      → /       → 127.0.0.1:18086 (frontend, наш контейнер)
  → PostgreSQL — без публикации порта наружу, только во внутренней docker-сети проекта
```

`docker-compose.prod.yml` — самостоятельный (не merge-overlay поверх
`docker-compose.yml`) продакшн-конфиг: порты backend/frontend опубликованы
только на `127.0.0.1`, `restart: always`, `VITE_API_BASE_URL=/api`
(относительный путь — тот же домен, что и фронтенд, поэтому CORS в проде не
нужен: nginx работает как единая точка входа).

## Первый деплой / повторное развёртывание

1. Перенести чистый снимок репозитория (без `node_modules`/`.venv`/`.env`):
   ```bash
   git archive HEAD | ssh user@host "tar -x -C ~/project-start"
   ```
2. Создать `~/project-start/.env` на сервере на основе `.env.example`,
   заполнить реальными значениями:
   - `POSTGRES_PASSWORD` — свой, не дефолтный
   - `MAX_BOT_TOKEN` — реальный токен бота
   - `MAX_BOT_WEBHOOK_SECRET` — см. раздел «Бот-меню в чате» ниже
   - `AUTH_RATE_LIMIT_PER_MINUTE` — лимит попыток demo/admin-входа с одного IP
   - `WEBHOOK_RATE_LIMIT_PER_MINUTE` и `WEBHOOK_DEDUP_TTL_SECONDS` — защита webhook от всплесков и повторов
   - `JWT_SECRET`, `ADMIN_PASSWORD` — сгенерировать (`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`)
   - `DEEPSEEK_API_KEY` — рабочий ключ
   - `CORS_ORIGINS=https://<домен>`
   - `VITE_API_BASE_URL=/api`
   - `chmod 600 .env`
3. Поднять стек:
   ```bash
   cd ~/project-start
   sudo docker compose -f docker-compose.prod.yml up -d --build
   ```
   Entrypoint сам применит миграции и seed при старте backend-контейнера.
4. Создать nginx-конфиг сайта (`/etc/nginx/sites-available/<домен>`,
   симлинк в `sites-enabled`) — см. пример ниже — и `sudo nginx -t && sudo
   systemctl reload nginx`.
5. Как только DNS A-запись `<домен> → IP сервера` разошлась:
   ```bash
   sudo certbot --nginx -d <домен>
   ```
   Certbot сам допишет `listen 443 ssl` блок и редирект с 80 на 443.

### Пример nginx-конфига (до certbot, HTTP-only)

```nginx
server {
    listen 80;
    server_name your-domain.example;

    location /api/ {
        proxy_pass         http://127.0.0.1:18085/;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }

    location / {
        proxy_pass         http://127.0.0.1:18086;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

Обратите внимание: `location /api/` проксирует на `http://127.0.0.1:18085/`
(со слэшем на конце) — nginx срезает префикс `/api` при пробросе, поэтому
backend-роуты остаются без префикса (`/auth/max`, а не `/api/auth/max`).

## Обновление (redeploy)

```bash
git archive HEAD | ssh user@host "tar -x -C ~/project-start"
ssh user@host "cd ~/project-start && sudo docker compose -f docker-compose.prod.yml up -d --build"
```

`.env` при этом не трогается (`git archive` не включает untracked файлы).

## Бот-меню в чате (inline-кнопки)

После деплоя кода с `app/api/bot_webhook.py`:

1. Добавить `MAX_BOT_WEBHOOK_SECRET` в серверный `.env` (`chmod 600`), сгенерировав его:
   `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`.
2. Пересобрать и поднять backend: `sudo docker compose -f docker-compose.prod.yml up -d --build backend`.
3. Разово зарегистрировать вебхук в MAX (сам вебхук уже доступен по
   `https://<домен>/api/bot/webhook` через существующий `/api/` location —
   отдельная nginx-настройка не нужна):
   ```bash
   sudo docker compose -f docker-compose.prod.yml exec backend \
     python -m app.bot.setup_webhook https://your-domain.example/api/bot/webhook
   ```
   Скрипт читает `MAX_BOT_TOKEN`/`MAX_BOT_WEBHOOK_SECRET` из окружения контейнера и
   регистрирует переданный публичный URL вида
   `https://your-domain.example/api/bot/webhook`.
4. Проверить в MAX: написать боту `/start` — должно прийти меню с кнопками, редактируемое
   при навигации.

## MAX Mini App и HTTPS

MAX Mini App должен открываться по HTTPS — без сертификата `initData` от
MAX Bridge получить не получится (сам мессенджер не откроет HTTP-страницу
как mini app). Поэтому шаг с certbot — не косметика, а обязательное условие
для реальной проверки внутри MAX.

## На будущее

Для первой передачи можно использовать `git archive | ssh | tar`. После
появления приватного GitHub-репозитория лучше настроить на сервере deploy key и
обновлять зафиксированный commit через `git fetch`/`git checkout`, а затем
пересобирать Compose. Это сохраняет проверяемую связь деплоя с commit hash.
