# Proposal

## Why

Аудит AI-Readiness закоммиченной OpenAPI-схемы (`backend/openapi.json`) выявил четыре пробела контракта, мешающих ИИ-агентам и внешним инструментам корректно вызывать API и обрабатывать отказы без чтения исходного кода:

1. **Несовпадение схемы ошибок в OpenAPI с реальным конвертом API**: FastAPI по умолчанию генерирует в `responses["422"]` стандартную схему `HTTPValidationError` (`{"detail": [...]}`), хотя глобальный обработчик в `backend/app/errors.py` перехватывает все ошибки (включая 422) и возвращает единый конверт `{"code": "...", "message": "..."}`.
2. **Отсутствие бизнес-кодов ошибок (`401`, `403`, `404`, `405`, `409`, `422`, `429`) в `responses`**: ни одна из 45 операций не декларировала в OpenAPI коды бизнес-ошибок (`409 ACTIVE_CHECKOUT`, `409 SELF_CHECKOUT`, `409 HAS_DEVICES`, `403 FORBIDDEN` и др.).
3. **Не описана схема аутентификации (`securitySchemes`)**: в `components` отсутствовала схема для cookie-сессии (`qa_session`), поэтому из `openapi.json` не было видно, какие эндпоинты требуют сессионную cookie, а какие публичны (`/health`, `/auth/login`, `/auth/logout`).
4. **Низкое покрытие описаниями (`description`)**: подробные описания были заполнены только у 8 из 45 операций (17.8%).

## What Changes

- **Схема единого конверта ошибок (`ErrorResponse`)**: в `components.schemas` добавляется модель `ErrorResponse` (`{code, message}`), стандартные `HTTPValidationError` и `ValidationError` исключаются из схемы, а все ответы `4xx` (включая `422`) ссылаются на `#/components/schemas/ErrorResponse`.
- **Декларация бизнес-кодов ошибок в `responses`**: для всех операций в OpenAPI декларируются возможные HTTP-статусы отказов (`401`, `403`, `404`, `405`, `409`, `422`, `429`) с указанием машинных кодов (`ACTIVE_CHECKOUT`, `SELF_CHECKOUT`, `HAS_DEVICES`, `FORBIDDEN`, `UNAUTHORIZED`, `SESSION_EXPIRED`, `USER_INACTIVE` и др.).
- **Схема аутентификации `SessionCookie` (`securitySchemes`)**: зависимость `get_current_user` использует `APIKeyCookie(name=settings.session_cookie_name, auto_error=False)`, благодаря чему в `components.securitySchemes` появляется `SessionCookie` (`in: "cookie"`, `name: "qa_session"`), все 42 защищённых операции помечаются `security: [{"SessionCookie": []}]`, а публичные операции (`/health`, `/auth/login`, `/auth/logout`) остаются без требования `security`.
- **Стопроцентное покрытие описаниями (`description`)**: все 45 операций получают подробные русские описания назначения, требуемых прав и ключевых инвариантов.
- **Обновление `backend/openapi.json` и тестов**: перегенерация `backend/openapi.json` и расширение `backend/tests/test_openapi.py` проверками всех четырёх аспектов контракта.

## Capabilities

### New Capabilities

- (нет)

### Modified Capabilities

- `api-schema`: ADDED требования к описанию единого конверта ошибок `ErrorResponse`, схемы аутентификации `securitySchemes` для cookie `qa_session`, бизнес-кодов ошибок в `responses` и полноте `description` у всех операций.

## Impact

- `backend/app/openapi.py` — сборка и обогащение OpenAPI-контракта (`ErrorResponse`, `responses`, удаление `HTTPValidationError`/`ValidationError`).
- `backend/app/main.py` — подключение кастомного генератора `openapi` в `create_app()`.
- `backend/app/api/deps.py` — декларация `APIKeyCookie` (`SessionCookie` для `qa_session`) в `get_current_user`.
- `backend/app/api/*.py` — русские docstrings (`description`) для всех 45 операций.
- `backend/openapi.json` — перегенерированная схема.
- `backend/tests/test_openapi.py` — тесты на `ErrorResponse`, отсутствие `HTTPValidationError`, `securitySchemes`, бизнес-коды ошибок и 100% покрытие `description`.

## Не входит в изменение

- Runtime-поведение обработчиков ошибок (`backend/app/errors.py`), бизнес-логика в `backend/app/services/*`, коды и тексты ошибок в ответах сервера не меняются.
- Схема БД, миграции Alembic и фронтенд не затрагиваются.
- Механизм сессий и формат cookie `qa_session` в рантайме остаются прежними.
