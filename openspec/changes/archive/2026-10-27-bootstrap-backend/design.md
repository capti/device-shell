# Design

## Context

Спеки baseline готовы, кода нет. `access-control` описывает вход, сессии, роли,
rate limit и проверку Origin. Стек зафиксирован в `openspec/config.yaml`.
См. `proposal.md` — Why.

## Goals / Non-Goals

**Goals:**

- Запускаемый backend с `/health` и единым форматом ошибок.
- Полная схема БД со всеми инвариантами, наложенными на уровне SQLite.
- Рабочая авторизация и зависимости прав, готовые для доменных роутов.

**Non-Goals:**

- Доменные эндпоинты устройств, владения, выдач и отчётов.
- Управление пользователями, кроме создания первого администратора.
- Frontend, media, Excel, уведомления.

## Decisions

### 1. Синхронный SQLAlchemy вместо async

**Решение:** sync-сессии SQLAlchemy 2.0, `uvicorn` в один процесс.

**Почему:** SQLite всё равно сериализует записи, а async добавляет
`aiosqlite`, отдельный event loop и усложняет тесты без выигрыша при 300
устройствах и 50 пользователях.

**Альтернатива:** async SQLAlchemy — оправдана только при переходе на Postgres
и нескольких воркерах.

### 2. SQLite в режиме WAL и с включёнными внешними ключами

**Решение:** на каждом соединении выполнять `PRAGMA journal_mode=WAL`,
`PRAGMA foreign_keys=ON`, `PRAGMA busy_timeout=5000`.

**Почему:** WAL позволяет читать во время записи, `foreign_keys` обязателен,
иначе SQLite молча игнорирует `ON DELETE RESTRICT`, а `busy_timeout` убирает
случайные `database is locked`.

### 3. Alembic с первого коммита

**Решение:** никакого `create_all`; схема создаётся только
`alembic upgrade head`.

**Почему:** миграции нужны с первой таблицы, иначе первая же правка схемы
потребует ручной синхронизации окружений.

### 4. Непрозрачный токен сессии, хеш в БД

**Решение:** `secrets.token_urlsafe(32)` в cookie `qa_session`; в таблице
`sessions` хранится SHA-256 от токена, срок 7 дней, продление при активности.

**Почему:** утечка БД не даёт готовых токенов; отзыв сессии — удаление строки,
без чёрных списков JWT.

**Альтернатива:** JWT — не позволяет мгновенный отзыв без дополнительного
хранилища.

### 5. argon2id для паролей

**Решение:** `argon2-cffi`, параметры по умолчанию библиотеки.

**Почему:** рекомендован OWASP, устойчив к GPU-перебору, не требует настройки
соли.

### 6. Единый конверт ошибок

**Решение:** исключение `AppError(code, message, status)` и обработчик, который
возвращает `{"code": "...", "message": "..."}`; ошибки валидации Pydantic и
`HTTPException` приводятся к тому же виду.

**Почему:** фронтенд различает ситуации по `code`, а не по тексту; сообщения
остаются на русском.

### 7. Rate limit в памяти процесса

**Решение:** скользящее окно по ключу `ip + username`: 5 попыток в минуту,
блокировка 15 минут.

**Почему:** один процесс и локальный хостинг; внешнее хранилище не нужно.
Ограничение сбрасывается при рестарте — для внутреннего инструмента приемлемо.

### 8. Проверка Origin отдельным middleware

**Решение:** для методов POST/PATCH/PUT/DELETE middleware сравнивает
`Origin` с `APP_BASE_URL`; отсутствующий Origin допускается только для
не-браузерных клиентов в dev.

**Почему:** `SameSite=Lax` уже блокирует большинство CSRF, но явная проверка
дешевле, чем полноценные CSRF-токены.

### 9. Фабрика приложения, роутеры и сервисы

**Решение:** `create_app()` в `main.py`, роутеры в `api/`, бизнес-логика в
`services/`, модели в `models/`, схемы Pydantic в `schemas/`.

**Почему:** соответствует конвенции «роуты тонкие»; доменные change будут
добавлять сервисы, не трогая каркас.

### 10. Наивное локальное время сервера

**Решение:** все даты хранятся как naive datetime в локальном времени сервера.

**Почему:** один сервер, один часовой пояс; сравнение просрочки идёт по
локальной дате. Смещения и UTC-конвертация не нужны.

**Риск:** при переезде сервера в другой пояс данные придётся пересчитывать.

## Схема данных

| Таблица | Ключевые поля и ограничения |
|---|---|
| `users` | `username` UNIQUE, `password_hash`, `role` CHECK (admin/user), `is_active` |
| `sessions` | `token_hash` UNIQUE, `expires_at`, `last_seen_at`, FK `user_id` |
| `devices` | `inventory_no` UNIQUE, `owner_id` NOT NULL, `status` CHECK (active/repair/lost), `archived_at`; UNIQUE `imei` и `serial_no`, где значение не NULL |
| `checkouts` | FK `device_id`, `user_id`, `returned_at`; UNIQUE partial index `(device_id) WHERE returned_at IS NULL` |
| `condition_reports` | `condition` CHECK (ok/scratches/damaged/not_working), `requires_repair` |
| `repairs` | `sent_at`, `returned_at`, `service`, `description`, `cost` |
| `device_photos` | `file_path`, `thumb_path`, FK `report_id` (nullable) |
| `device_events` | `type`, `payload` JSON, `actor_id`, append-only |
| `notifications` | `recipient_id`, `type`, `device_id`, `read_at`; индекс `(recipient_id, read_at)` |

## Risks / Trade-offs

- **SQLite блокирует запись при конкуренции** → WAL, `busy_timeout`, один
  процесс uvicorn; при росте — переезд на Postgres отдельным change.
- **Partial unique index не виден ORM** → отдельный тест, который проверяет
  IntegrityError при второй активной выдаче.
- **Rate limit сбрасывается при рестарте** → принято для внутреннего
  инструмента; при необходимости вынести в БД.
- **Наивное локальное время** → переезд сервера в другой часовой пояс потребует
  миграции данных; фиксируем в README.
- **Один воркер** → нельзя запускать `uvicorn --workers 2`; фиксируем в README и
  `dev.ps1`.

## Migration Plan

1. `cd backend && uv sync` — зависимости.
2. `uv run alembic upgrade head` — схема.
3. `uv run python -m app.cli create-admin` — первый администратор.
4. `uv run uvicorn app.main:app --port 8000` — проверка `/health` и входа.
5. Откат в dev: `uv run alembic downgrade base` + удаление `data/qa.db`.

## Open Questions

Нет: всё, что влияет на объём и задачи, решено выше.
