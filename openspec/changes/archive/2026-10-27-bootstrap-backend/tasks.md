# Tasks

## 1. Каркас backend (B0)

- [x] 1.1 Создать `backend/pyproject.toml` с зависимостями (fastapi, uvicorn,
  sqlalchemy, alembic, pydantic-settings, argon2-cffi, python-multipart,
  openpyxl, pillow, pytest, httpx, ruff) и проверить, что `uv sync` создаёт
  `.venv` без ошибок
- [x] 1.2 Добавить `app/config.py` на `pydantic-settings` и `.env.example`
  (`DATABASE_URL`, `DATA_DIR`, `SESSION_TTL_DAYS`, `COOKIE_SECURE`,
  `APP_BASE_URL`, `APP_ENV`); проверить
  `uv run python -c "from app.config import settings; print(settings.database_url)"`
- [x] 1.3 Реализовать `app/db.py`: движок, sessionmaker, `PRAGMA journal_mode=WAL`,
  `foreign_keys=ON`, `busy_timeout=5000`; проверить тестом, что
  `PRAGMA journal_mode` возвращает `wal`
- [x] 1.4 Создать `app/main.py` с `create_app()` и `GET /health`, отдающим
  `{"status": "ok", "version": ...}`; проверить тестом `tests/test_health.py`
- [x] 1.5 Реализовать единый конверт ошибок `{code, message}` для `AppError`,
  `HTTPException` и ошибок валидации; проверить тестом, что 404 и 422 возвращают
  нужную структуру
- [x] 1.6 Добавить `dev.ps1`, запускающий `uv run uvicorn app.main:app --reload
  --port 8000`; проверить, что скрипт поднимает сервер и `/health` отвечает 200
- [x] 1.7 Добавить `.gitignore` (`data/`, `.venv/`, `__pycache__/`, `.env`,
  `*.db`) и проверить, что `data/qa.db` не попадает в `git status`

## 2. Схема данных и миграции (B1)

- [x] 2.1 Описать модели `users` и `sessions` (username UNIQUE, role CHECK,
  is_active, token_hash UNIQUE, expires_at); проверить тестом создание
  пользователя и сессии
- [x] 2.2 Описать модель `devices` с `owner_id NOT NULL`, `status` CHECK,
  `archived_at` и UNIQUE-индексами на `inventory_no`, `imei`, `serial_no`;
  проверить тестом, что дубликат инвентарного номера даёт IntegrityError
- [x] 2.3 Описать модель `checkouts` и partial unique index
  `(device_id) WHERE returned_at IS NULL`; проверить тестом, что вторая активная
  выдача вызывает IntegrityError, а закрытая — нет
- [x] 2.4 Описать модели `condition_reports`, `repairs`, `device_photos`
  (включая nullable `checkout_id` и `report_id`); проверить тестом создание
  отчёта с фото и записи ремонта
- [x] 2.5 Описать модели `device_events` (append-only, JSON payload) и
  `notifications` с индексом `(recipient_id, read_at)`; проверить тестом
  создание события и уведомления
- [x] 2.6 Инициализировать Alembic, подключить модели к `env.py` и создать
  первую миграцию; проверить `uv run alembic upgrade head` и
  `uv run alembic downgrade base`
- [x] 2.7 Добавить CLI-команду `python -m app.cli create-admin` (username, ФИО,
  пароль); проверить, что она создаёт активного admin и отклоняет дубликат
  username
- [x] 2.8 Проверить тестами все ограничения схемы: UNIQUE `inventory_no`,
  UNIQUE `imei`/`serial_no` при непустых значениях, внешние ключи, partial index

## 3. Авторизация и сессии (B2)

- [x] 3.1 Реализовать хеширование и проверку пароля на argon2id; проверить
  тестом, что верный пароль проходит, неверный — нет, и хеш не содержит пароль
- [x] 3.2 Реализовать сервис сессий: создание, валидация по хешу токена,
  продление при активности, отзыв; проверить тестами все четыре операции
- [x] 3.3 Реализовать `POST /auth/login` с установкой httpOnly cookie;
  проверить тестом успешный вход и 401 при неверном пароле
- [x] 3.4 Реализовать `POST /auth/logout` с удалением сессии и очисткой cookie;
  проверить тестом, что повторный запрос с той же cookie даёт 401
- [x] 3.5 Реализовать `GET /auth/me`; проверить тестом, что возвращается профиль
  без `password_hash`
- [x] 3.6 Добавить зависимости `get_current_user` и `require_admin`; проверить
  тестами 401 без сессии и 403 для user на админском эндпоинте-заглушке
- [x] 3.7 Реализовать rate limit 5 попыток в минуту и блокировку на 15 минут;
  проверить тестом, что шестая попытка возвращает 429
- [x] 3.8 Реализовать middleware проверки Origin для POST/PATCH/PUT/DELETE;
  проверить тестом, что чужой Origin даёт 403, а свой — проходит
- [x] 3.9 Настроить выгрузку `backend/openapi.json`; проверить, что файл
  создаётся и содержит эндпоинты `/auth/login`, `/auth/me`, `/health`

## 4. Интеграция

- [x] 4.1 Прогнать `uv run pytest` — все тесты зелёные
- [x] 4.2 Прогнать `uv run ruff check .` — без ошибок
- [x] 4.3 Описать в README запуск backend, создание администратора, ограничение
  «один воркер uvicorn» и хранение времени в локальном поясе; проверить, что
  команды из README выполняются как написано
- [x] 4.4 Ручная проверка: создать админа, войти, вызвать `/auth/me`, выйти —
  проверить, что все шаги проходят на чистой БД

## Workflow follow-up

- Архивировать change после проверки: `openspec archive bootstrap-backend`.
- Убедиться, что `skip_specs: true` не изменил основные спеки.
