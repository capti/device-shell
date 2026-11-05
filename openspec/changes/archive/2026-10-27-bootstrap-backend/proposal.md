# Proposal

## Why

Кода в проекте нет. Прежде чем реализовывать домен — устройства, владение,
выдачи — нужен фундамент: запускаемый каркас backend, схема БД с заложенными
инвариантами и рабочая авторизация. Без него каждый следующий change начинался
бы с повторного создания одной и той же инфраструктуры.

## What Changes

- **B0 — каркас:** `backend/` с `uv`, настройки через `.env`, подключение к
  SQLite с WAL, фабрика приложения, `GET /health`, единый формат ошибок,
  `dev.ps1`.
- **B1 — схема данных:** SQLAlchemy-модели всех таблиц из `PLAN.md`, Alembic с
  первой миграцией, partial unique index на активную выдачу, CLI-команда
  создания администратора.
- **B2 — авторизация:** вход и выход, серверные сессии в httpOnly cookie,
  `GET /auth/me`, зависимости `get_current_user` и `require_admin`, ограничение
  попыток входа, проверка Origin на мутациях.
- Тесты на схему и авторизацию, выгрузка `backend/openapi.json`.

### Out of Scope

- CRUD устройств, владение, выдачи, отчёты о состоянии, ремонты, уведомления и
  Excel — отдельные changes.
- Управление пользователями сверх создания администратора.
- Frontend, визуальный стиль, фото и раздача media.
- Наполнение демо-данными.

## Capabilities

### New Capabilities

Нет.

### Modified Capabilities

Нет. Это изменение реализует уже описанное поведение из `access-control`
(вход, сессии, роли, rate limit, проверка Origin) без изменения требований,
поэтому в `.openspec.yaml` установлен `skip_specs: true`.

## Impact

- Новые каталоги `backend/`, `data/`; файлы `.env.example`, `dev.ps1`.
- Зависимости backend: FastAPI, SQLAlchemy, Alembic, Pydantic Settings,
  argon2, pytest, httpx, ruff.
- Frontend и существующие спеки не затрагиваются.
- После изменения `uv run uvicorn app.main:app` поднимает приложение, а
  `alembic upgrade head` создаёт схему.
