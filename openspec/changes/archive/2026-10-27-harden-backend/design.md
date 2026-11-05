# Design

## Context

См. `proposal.md` — Why. Текущее состояние, важное для решений:

- `app/errors.py` регистрирует обработчики для `AppError`, `StarletteHTTPException`
  и `RequestValidationError`; для `Exception` обработчика нет, поэтому ответ
  формирует `ServerErrorMiddleware` как `text/plain`.
- `app/middleware.py` проверяет `Origin` только если заголовок присутствует;
  `settings.is_production` уже существует, но не используется.
- `checkouts.closed_reason` ограничен списком значений, но не связан с
  `returned_at`. SQLite не умеет добавлять CHECK через `ALTER TABLE`.
- `device_events` не имеет триггеров; тесты создают схему через
  `Base.metadata.create_all`, а production — через Alembic.

## Goals / Non-Goals

**Goals:**

- Любой необработанный 5xx отдаёт `{code, message}` и пишет трейс в лог.
- В production мутация без `Origin` невозможна, в dev/test — по-прежнему
  возможна.
- Несогласованная выдача не сохраняется ни через ORM, ни через прямой SQL.
- `UPDATE`/`DELETE` по `device_events` отклоняются самой SQLite.
- Схема из моделей и схема из миграции совпадают по ограничениям и триггерам.

**Non-Goals:**

- Новые эндпоинты и коды ошибок, кроме `INTERNAL_ERROR`.
- Изменение frontend и текстов сообщений.
- Очистка исторических данных и массовые операции с аудитом.
- Проверка `Origin` для GET/HEAD.

## Decisions

### 1. Обработчик `Exception` вместо собственного middleware

`register_exception_handlers` добавляет `@app.exception_handler(Exception)`.
Starlette передаёт такой обработчик в `ServerErrorMiddleware`, который стоит
внешним слоем, поэтому JSON получится и для ошибок в роутах, и для ошибок в
пользовательском middleware. Трейс пишется через `logger.exception`, клиенту
уходит только `INTERNAL_ERROR` и «Внутренняя ошибка сервера».

Альтернатива — свой middleware с `try/except` — отклонена: дублирует Starlette,
легко получить двойной ответ и потерять порядок middleware.

Тест использует `TestClient(app, raise_server_exceptions=False)` и маршрут,
который бросает `RuntimeError`.

### 2. Отсутствие `Origin` проверяется только в production

В `dispatch`:

- `Origin` отсутствует и `settings.is_production` → 403 `FORBIDDEN`;
- `Origin` отсутствует в dev/test → запрос проходит;
- `Origin` есть и не совпадает с `APP_BASE_URL` → 403, как сейчас.

Режим берётся из `app_env`, а не из отдельного флага: это уже существующая
настройка, и один источник правды лучше второго переключателя. Тесты
переключают `settings.app_env` через `monkeypatch` и проверяют оба режима.

Альтернатива — требовать `Origin` всегда — отклонена: сломала бы curl, CLI и
тесты в dev, где CSRF-риск закрыт SameSite=Lax и локальным запуском.

### 3. CHECK на `checkouts` через batch-миграцию

В модель добавляется:

```sql
CHECK (
  (returned_at IS NULL AND closed_reason IS NULL)
  OR (returned_at IS NOT NULL AND closed_reason IS NOT NULL)
)
```

SQLite не поддерживает `ALTER TABLE ... ADD CONSTRAINT`, поэтому миграция
использует `op.batch_alter_table("checkouts")` с пересозданием таблицы.
Существующий тест `test_migrations.py` уже проверяет, что partial unique index
`uq_checkouts_active_device` с `returned_at IS NULL` выжил после upgrade; его
дополняем проверкой нового CHECK и триггеров.

Несогласованные строки в старой базе приведут к ошибке миграции. Это осознанно:
данные должны быть исправлены вручную, а не «нормализованы» догадкой (нельзя
придумать дату возврата или причину закрытия). На текущем этапе production-базы
ещё нет.

Альтернатива — проверка только в сервисах — отклонена: прямой SQL и будущие
ручки обойдут её, а инвариант должен быть невозможен на уровне БД.

### 4. Append-only через SQLite-триггеры в модели и миграции

Два триггера:

```sql
CREATE TRIGGER trg_device_events_no_update
BEFORE UPDATE ON device_events
BEGIN SELECT RAISE(ABORT, 'device_events is append-only'); END;

CREATE TRIGGER trg_device_events_no_delete
BEFORE DELETE ON device_events
BEGIN SELECT RAISE(ABORT, 'device_events is append-only'); END;
```

SQL вешается на `DeviceEvent.__table__` через `event.listen(..., "after_create",
DDL(...))`, чтобы `Base.metadata.create_all` в тестах создавал те же гарантии,
что и Alembic в production. Миграция создаёт триггеры явно и удаляет их в
downgrade. Alembic не умеет автогенерировать триггеры, поэтому это единственное
место, где SQL дублируется; имена триггеров фиксированы и проверяются тестом
миграции.

Альтернатива — триггеры только в миграции — отклонена: тестовая схема
расходилась бы с production, и тесты «зеленели» бы без защиты. Альтернатива —
запрет только на уровне сервисов — отклонена: не выполняет требование
`audit-log` о запрете на уровне БД.

### 5. Порядок миграции

1. Пересоздать `checkouts` с CHECK.
2. Создать триггеры `device_events`.

Downgrade — в обратном порядке: удалить триггеры, затем пересоздать
`checkouts` без CHECK.

## Risks / Trade-offs

- **Batch-пересоздание `checkouts` может потерять индексы или их `WHERE`** →
  тест миграции проверяет SQL partial unique index после upgrade; downgrade
  также прогоняется в тесте.
- **Несогласованные старые строки заблокируют миграцию** → ожидаемо; перед
  раскаткой сделать бэкап `data/qa.db`, при ошибке исправить строки вручную.
- **Триггеры мешают массовой очистке событий** → это и есть цель; для dev-базы
  допустимо удалить базу и накатить миграции заново.
- **Production-клиенты без `Origin` получат 403** → задокументировать в README;
  браузерный frontend всегда отправляет `Origin` на мутациях.
- **`Exception`-обработчик не перехватывает ошибки вне ASGI-стека** → для этого
  приложения таких путей нет; трейсы и так попадут в лог процесса.
