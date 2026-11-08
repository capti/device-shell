# Tasks

## 1. Контрактные тесты OpenAPI (TDD)

- [x] 1.1 Добавить в `backend/tests/test_openapi.py` тесты на четыре аспекта AI-Readiness:
      единая схема `ErrorResponse` в `components.schemas` и отсутствие `HTTPValidationError`/`ValidationError`;
      наличие `securitySchemes.SessionCookie` (`in: "cookie"`, `name: "qa_session"`) и корректная разметка `security` для защищённых и публичных эндпоинтов;
      декларация бизнес-кодов ошибок (`409 ACTIVE_CHECKOUT`, `409 SELF_CHECKOUT`, `409 HAS_DEVICES`, `403 FORBIDDEN`, `401`, `404`, `422`) в `responses`;
      непустой `description` у всех 45 операций.
      Проверка: `uv run pytest tests/test_openapi.py` — новые тесты падают на текущей схеме.

## 2. Реализация схемы безопасности, конверта ошибок и описаний

- [x] 2.1 Перевести `get_current_user` в `backend/app/api/deps.py` на `Security(session_cookie_scheme)` (`APIKeyCookie` с `auto_error=False`).
      Проверка: `uv run pytest tests/test_auth_deps.py tests/test_auth_login.py tests/test_auth_me.py` — зелёные.
- [x] 2.2 Добавить подробные русские docstrings (`description`) для всех 37 операций в `backend/app/api/auth.py`, `users.py`, `devices.py`, `rotation.py`, `maintenance.py`, `notifications.py`, `photos.py` и уточнить существующие в `health.py`, `reports.py`, `audit.py`.
- [x] 2.3 Создать `backend/app/openapi.py` со схемой `ErrorResponse`, таблицей бизнес-ошибок по операциям и функцией `build_openapi(app)`, подключить её в `backend/app/main.py` и перегенерировать `backend/openapi.json` (`uv run python -m app.export_openapi`).
      Проверка: `uv run pytest tests/test_openapi.py` — все тесты зелёные.

## 3. Полное ревью и валидация

- [x] 3.1 Прогнать `openspec validate --all --strict` и полный пайплайн `ub-review` (`ruff`, `pytest` + `coverage`, `crapper`, `dryer`, `mutator`).
      Проверка: все проверки проходят без ошибок, `0 SURVIVED`, `CRAP < 10`, `0` дубликатов `>= 0.8`.
