# Spec Delta

## ADDED Requirements

### Requirement: Единый конверт ошибок в OpenAPI

OpenAPI-схема SHALL описывать все ответы с ошибками (`4xx`, включая `422`) через единую схему `ErrorResponse` с обязательными строковыми полями `code` и `message` и MUST NOT содержать стандартные схемы FastAPI `HTTPValidationError` и `ValidationError`.

#### Scenario: Ответ 422 в схеме использует ErrorResponse

- **WHEN** в OpenAPI-схеме проверяется любой эндпоинт с валидацией параметров или тела запроса
- **THEN** `responses["422"]` ссылается на `#/components/schemas/ErrorResponse`, а `HTTPValidationError` отсутствует в `components.schemas`

#### Scenario: Бизнес-коды ошибок задокументированы в responses

- **WHEN** эндпоинт может вернуть ошибки `401`, `403`, `404`, `405`, `409`, `422` или `429`
- **THEN** в `responses` операции присутствуют соответствующие статусы со ссылкой на `#/components/schemas/ErrorResponse` и перечислением машинных кодов (включая `ACTIVE_CHECKOUT`, `SELF_CHECKOUT`, `HAS_DEVICES`, `FORBIDDEN`)

### Requirement: Схема аутентификации cookie-сессии в OpenAPI

OpenAPI-схема SHALL декларировать в `components.securitySchemes` cookie-схему аутентификации для `qa_session` (`type: "apiKey"`, `in: "cookie"`, `name: "qa_session"`). Защищённые операции SHALL содержать требование `security`, а публичные операции (`/health`, `/auth/login`, `/auth/logout`) MUST NOT требовать `security`.

#### Scenario: Защищённый эндпоинт требует cookie-сессию

- **WHEN** в OpenAPI-схеме проверяется защищённая операция (например, `GET /devices` или `POST /users`)
- **THEN** в операции указано `security` со ссылкой на схему cookie `qa_session`

#### Scenario: Публичный эндпоинт не требует cookie-сессию

- **WHEN** в OpenAPI-схеме проверяются `GET /health`, `POST /auth/login` и `POST /auth/logout`
- **THEN** у этих операций отсутствует поле `security`

### Requirement: Полнота описаний операций в OpenAPI

Каждая операция в OpenAPI-схеме SHALL иметь непустое русскоязычное поле `description`, поясняющее назначение эндпоинта и правила доступа.

#### Scenario: Все операции имеют description

- **WHEN** выгружается OpenAPI-схема приложения
- **THEN** у 100% операций во всех путях заполнено непустое поле `description`
