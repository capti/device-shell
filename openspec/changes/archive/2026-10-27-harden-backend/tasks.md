# Tasks

## 1. Конверт ошибок для 5xx

- [x] 1.1 Добавить в `tests/test_errors.py` маршрут, бросающий `RuntimeError`, и тест: `TestClient(app, raise_server_exceptions=False)` получает 500 с `{code: INTERNAL_ERROR, message}` и без стека. Проверка: тест падает на текущем коде.
- [x] 1.2 Зарегистрировать в `app/errors.py` обработчик `Exception` с логированием трейса и ответом `INTERNAL_ERROR`. Проверка: тест 1.1 проходит, `uv run pytest tests/test_errors.py -q` зелёный.
- [x] 1.3 Убедиться, что существующие ответы `AppError`, `HTTPException` и 422 не изменились. Проверка: весь `tests/test_errors.py` и `tests/test_auth_*.py` проходят.

## 2. Origin в production

- [x] 2.1 Добавить в `tests/test_origin.py` тесты: без `Origin` в production — 403 `FORBIDDEN`; без `Origin` в dev — успешный вход; с чужим `Origin` — 403 в обоих режимах. Проверка: production-тест падает на текущем коде.
- [x] 2.2 В `app/middleware.py` отклонять мутацию без `Origin`, когда `settings.is_production`. Проверка: новые тесты 2.1 и весь `tests/test_origin.py` проходят.
- [x] 2.3 Обновить README: в production мутации без `Origin` отклоняются, в dev/test — разрешены. Проверка: текст совпадает с поведением из 2.2.

## 3. Согласованность закрытия выдачи

- [x] 3.1 Добавить в `tests/test_models_checkouts.py` тесты: активная выдача без причины и закрытая с причиной сохраняются; `returned_at` без `closed_reason` и `closed_reason` без `returned_at` отклоняются `IntegrityError`. Проверка: тесты на нелегальные состояния падают до изменения модели.
- [x] 3.2 Добавить CHECK `ck_checkouts_returned_closed_reason` в `app/models/checkouts.py`. Проверка: тесты 3.1 проходят.
- [x] 3.3 Создать Alembic-миграцию с `batch_alter_table` для CHECK и проверить `uv run alembic upgrade head` и `uv run alembic downgrade -1` на чистой базе. Проверка: обе команды завершаются без ошибок.
- [x] 3.4 Дополнить `tests/test_migrations.py` проверками: после upgrade CHECK присутствует, partial unique index `uq_checkouts_active_device` сохранил `returned_at IS NULL`; после downgrade CHECK отсутствует. Проверка: `uv run pytest tests/test_migrations.py -q` зелёный.

## 4. Append-only журнал устройств

- [x] 4.1 Добавить в `tests/test_models_events.py` тесты: `INSERT` события проходит, `UPDATE` и `DELETE` отклоняются `IntegrityError`. Проверка: тесты на `UPDATE`/`DELETE` падают до добавления триггеров.
- [x] 4.2 Повесить DDL триггеров `trg_device_events_no_update` и `trg_device_events_no_delete` на `DeviceEvent.__table__` в `app/models/audit.py`. Проверка: тесты 4.1 проходят через `Base.metadata.create_all`.
- [x] 4.3 Добавить те же триггеры в Alembic-миграцию и удаление в downgrade. Проверка: после `upgrade head` триггеры есть в `sqlite_master`, после `downgrade -1` — нет.
- [x] 4.4 Дополнить `tests/test_migrations.py` проверками наличия триггеров после upgrade и их отсутствия после downgrade. Проверка: `uv run pytest tests/test_migrations.py -q` зелёный.

## 5. Интеграционная проверка

- [x] 5.1 Прогнать `uv run pytest` и `uv run ruff check .`. Проверка: все тесты зелёные, ruff без замечаний.
- [x] 5.2 Прогнать `uv run alembic upgrade head` на пустой базе и проверить, что приложение стартует и `/health` отвечает 200. Проверка: миграция и health-запрос успешны.

## Workflow follow-up

- Выполнить `openspec validate --all --strict` и закоммитить изменение локально.
- После ревью — `openspec archive harden-backend`.
