# Spec Delta

## ADDED Requirements

### Requirement: Доступ к дашборду

Эндпоинты дашборда `GET /dashboard/stats` и `GET /dashboard/charts` SHALL
отдавать данные только пользователям с ролью admin; пользователь с ролью
user SHALL получать на них `403 FORBIDDEN`.

#### Scenario: Админ запрашивает статистику

- **WHEN** admin вызывает `GET /dashboard/stats`
- **THEN** система отвечает 200 и возвращает счётчики дашборда

#### Scenario: Обычный пользователь запрашивает статистику

- **WHEN** user вызывает `GET /dashboard/stats`
- **THEN** система отвечает 403 с кодом `FORBIDDEN` и не возвращает данные

#### Scenario: Обычный пользователь запрашивает графики

- **WHEN** user вызывает `GET /dashboard/charts`
- **THEN** система отвечает 403 с кодом `FORBIDDEN` и не считает агрегаты

#### Scenario: Запрос без сессии

- **WHEN** запрос приходит без действующей сессии
- **THEN** система отвечает 401 независимо от роли
