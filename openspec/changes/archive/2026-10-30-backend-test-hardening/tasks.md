# Tasks

## 1. Сверка инвариантов с тестами

- [x] 1.1 Пройти по 12 инвариантам из `openspec/config.yaml` и сопоставить
      каждому существующий тест. Проверка: для каждого пункта назван файл и
      тест; отсутствующие покрытия выписаны.
- [x] 1.2 Добавить тесты для инвариантов без покрытия (если такие найдутся).
      Проверка: все 12 инвариантов закрыты существующими тестами —
      `test_models_*`, `test_checkouts.py`, `test_devices_archive.py`,
      `test_users_deactivate.py`, `test_device_state.py` и др.; новых тестов
      не потребовалось.

## 2. README: карта инвариантов

- [x] 2.1 Раздел «Инварианты и их тесты» в README: таблица «инвариант → файл
      теста». Проверка: каждая строка ссылается на существующий файл в
      `backend/tests/`.

## 3. OpenAPI

- [x] 3.1 `test_openapi_contains_report_endpoints` в `test_openapi.py`:
      `/dashboard/stats`, `/reports/holders`, `/reports/overdue`,
      `/reports/export.xlsx`. Проверка: `uv run pytest backend/tests/test_openapi.py`
      зелёный.
- [x] 3.2 Перегенерация `backend/openapi.json` и проверка отсутствия
      расхождений. Проверка: после `uv run python -m app.export_openapi`
      `git diff` по файлу пуст — выгрузка соответствует коду.

## 4. Проверка этапа

- [x] 4.1 `uv run pytest`, `uv run ruff check .`,
      `openspec validate --all --strict` зелёные.
- [x] 4.2 Локальный коммит этапа: `test(backend): invariant map, OpenAPI guard (B10)`.

## Workflow follow-up

- `openspec archive backend-test-hardening` после принятия ревью.
- Локальный коммит архива: `chore(openspec): archive backend-test-hardening`.
