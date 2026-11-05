# Tasks

## 1. Формат и настройка

- [x] 1.1 `backend/app/logs.py`: `JsonFormatter` (timestamp UTC, level, logger,
      message, поля `extra`, трейсбек в `exception`) и `configure_logging()`,
      который снимает только свой обработчик. Проверка: тесты форматтера —
      `uv run pytest backend/tests/test_logging.py`.
- [x] 1.2 `backend/app/config.py`: настройка `log_level` (по умолчанию
      `INFO`). Проверка: тест на фильтрацию по уровню.
- [x] 1.3 `create_app()` вызывает `configure_logging()`. Проверка: тест на
      повторную настройку без дублей.

## 2. Логи запросов

- [x] 2.1 `RequestLogMiddleware` в `backend/app/middleware.py`: `method`,
      `path`, `status_code`, `duration_ms`; подключён в `main.py` внешним по
      отношению к проверке Origin. Проверка: тесты на 200, 404 и 403.
- [x] 2.2 Сбой запроса: ERROR с трейсбеком, ответ остаётся 500. Проверка: тест
      с падающим обработчиком.
- [x] 2.3 Секреты не логируются: в `extra` нет тела, cookie и заголовков.
      Проверка: тест на вход с паролем — пароля и `authorization` в логах нет.

## 3. Документация и проверка

- [x] 3.1 README: как читать логи, `LOG_LEVEL`, куда идёт вывод.
- [x] 3.2 `uv run pytest`, `uv run ruff check .`,
      `openspec validate --all --strict` зелёные.
- [x] 3.3 Ревью `crapper`, `dryer`, `mutator` по новому коду: покрытие 100%,
      дублей нет; выжившие мутанты закрыты тестами на служебные поля,
      кириллицу и границы длительности запроса.
- [x] 3.4 Локальный коммит: `feat(backend): structured JSON logging (B9)`.

## Workflow follow-up

- `openspec archive structured-logging` после принятия ревью.
- Локальный коммит архива: `chore(openspec): archive structured-logging`.
