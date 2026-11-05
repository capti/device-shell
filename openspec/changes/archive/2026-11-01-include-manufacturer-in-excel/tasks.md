# Tasks

## 1. Excel-выгрузка

- [x] 1.1 Добавить API-тест, проверяющий производителя перед моделью и значения обоих столбцов на каждом листе; убедиться, что тест падает на текущей выгрузке
- [x] 1.2 Добавить производителя в заголовки и строки всех листов; выполнить `cd backend; uv run pytest tests/test_export.py -q` и убедиться, что тесты проходят
- [x] 1.3 Выполнить `cd backend; uv run ruff check .` и `openspec validate --all --strict`; убедиться, что обе проверки проходят

## Workflow follow-up

- После успешной проверки архивировать change командой `openspec archive include-manufacturer-in-excel`.
