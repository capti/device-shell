# Tasks

## 1. Guard-тест

- [x] 1.1 `backend/tests/test_openapi.py`: тест сверяет закоммиченный
      `backend/openapi.json` с `create_app().openapi()`, при расхождении
      подсказывает `python -m app.export_openapi`.
      Проверка: на устаревшей схеме тест падает, после перегенерации — проходит.

## 2. Перегенерация

- [x] 2.1 `python -m app.export_openapi`: в схеме появились `/audit/events`
      с параметрами `device_id`, `from_at`, `to_at`.
      Проверка: guard-тест проходит, `git diff` по файлу — только
      `/audit/events` и `/health`.

## 3. Документация ответа /health

- [x] 3.1 Модель `HealthStatus` (`status` и `database` как `Literal`) и
      `responses={200, 503}` в декораторе: схема ответа снова описана,
      рантайм не тронут.
      Проверка: в `openapi.json` у `/health` есть оба ответа со ссылкой на
      `HealthStatus`; `tests/test_health.py` зелёный.

## 4. Проверка

- [x] 4.1 `uv run pytest` (406 passed) и `uv run ruff check .` — зелёные.
- [x] 4.2 `openspec validate --all --strict` — без ошибок.
