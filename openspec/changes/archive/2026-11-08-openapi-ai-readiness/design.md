# Design

## Context

- В `backend/app/errors.py` зарегистрированы глобальные обработчики `AppError`, `StarletteHTTPException`, `RequestValidationError` и `Exception`, которые возвращают единый JSON-конверт `{"code": "...", "message": "..."}` для всех ошибок, включая `422`.
- Однако FastAPI при генерации `app.openapi()` ничего не знает об обработчике `RequestValidationError` и по умолчанию вставляет в каждую операцию с параметрами/телом `responses["422"] -> HTTPValidationError` (`{"detail": [...]}`).
- В `backend/app/api/deps.py` токен сессии читался вручную через `request.cookies.get(settings.session_cookie_name)`, поэтому FastAPI не добавлял `securitySchemes` в `components` и `security` в защищённые операции.
- Только 8 из 45 route-функций имели docstrings, которые FastAPI переносит в `operation["description"]`.

## Goals / Non-Goals

**Goals:**

- Полное соответствие OpenAPI-схемы реальному контракту ошибок `{code, message}` (`ErrorResponse`).
- Явная декларация бизнес-кодов ошибок (`401`, `403`, `404`, `405`, `409`, `422`, `429`) в `responses` операций.
- Автоматическая генерация `securitySchemes.SessionCookie` (`in: "cookie"`, `name: "qa_session"`) и `security` на всех защищённых эндпоинтах через зависимость `get_current_user`.
- 100% покрытие всех 45 операций подробными `description` на русском языке.
- Соблюдение ограничений `crapper` (`CRAP < 10`), `dryer` (без дублирования словарей по 10 файлам роутеров) и `mutator` (`0 SURVIVED`).

**Non-Goals:**

- Изменение runtime-ответов API, кодов или сообщений об ошибках.
- Изменение логики аутентификации и хранения сессий.

## Decisions

### D1. Декларация `APIKeyCookie` в `get_current_user`

В `backend/app/api/deps.py` вводится:
```python
session_cookie_scheme = APIKeyCookie(
    name=settings.session_cookie_name,
    scheme_name="SessionCookie",
    description="Сессионная httpOnly cookie (`qa_session`), устанавливаемая при входе через `POST /auth/login`.",
    auto_error=False,
)
```
`get_current_user` получает `token: str | None = Security(session_cookie_scheme)`.
- При `auto_error=False` при отсутствии cookie FastAPI передаёт `None` в `get_current_user`, где по-прежнему выбрасывается `AppError("UNAUTHORIZED", "Требуется вход в систему", 401)`.
- FastAPI автоматически включает `SessionCookie` в `components.securitySchemes` и проставляет `security: [{"SessionCookie": []}]` ровно тем 42 операциям, которые зависят от `get_current_user` или `require_admin`. Публичные `/health`, `/auth/login`, `/auth/logout` остаются без `security`.

### D2. Централизованное обогащение OpenAPI-схемы в `backend/app/openapi.py`

Вместо дублирования громоздких словарей `responses={...}` в декораторах 45 эндпоинтов вводится модуль `backend/app/openapi.py`:
- Определяет Pydantic-модель `ErrorResponse(code: str, message: str)` и регистрирует её в `components.schemas.ErrorResponse`.
- Удаляет `HTTPValidationError` и `ValidationError` из `components.schemas`.
- Для каждой операции с `security` автоматически добавляет ответ `401` (`UNAUTHORIZED`, `SESSION_EXPIRED`, `USER_INACTIVE`).
- Для каждой операции с `422` заменяет ссылку `HTTPValidationError` на `#/components/schemas/ErrorResponse` с описанием кодов валидации.
- Применяет декларативную таблицу специфичных статусов и бизнес-кодов ошибок (`401`, `403`, `404`, `405`, `409`, `422`, `429`) по операциям (`ACTIVE_CHECKOUT`, `SELF_CHECKOUT`, `HAS_DEVICES`, `FORBIDDEN` и др.), используя единый референс `#/components/schemas/ErrorResponse`.
- Подключается в `create_app()` (`backend/app/main.py`) через `app.openapi = lambda: build_openapi(app)`.

### D3. Docstrings на всех 45 эндпоинтах

Во всех файлах `backend/app/api/*.py` каждая route-функция снабжается информативным русским docstring'ом, который FastAPI использует как `description` операции в OpenAPI.

## Risks / Trade-offs

- [Рассинхрон закоммиченного `backend/openapi.json` при будущих правках] → существующий тест `test_committed_schema_matches_app` и новые контрактные тесты в `backend/tests/test_openapi.py` гарантируют обнаружение любого расхождения при запуске `pytest`.
