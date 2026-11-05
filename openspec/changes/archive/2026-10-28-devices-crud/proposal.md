# Proposal

## Why

Фундамент и авторизация готовы, но приложение пока не умеет работать с главным
объектом — устройством. Без карточки, списка и архива нельзя ни завести парк
телефонов, ни реализовать владение, выдачи и отчёты. Это следующий шаг backend
(B3) и основа для всех остальных change'ей.

## What Changes

- API устройств: `GET /devices` (серверный поиск, фильтры, сортировка,
  пагинация), `POST /devices`, `GET /devices/{id}`, `PATCH /devices/{id}`.
- Архив: `POST /devices/{id}/archive` и `POST /devices/{id}/restore` с запретом
  архивации при активной выдаче (`409 ACTIVE_CHECKOUT`) и правилом «архивное
  устройство только для чтения».
- Автогенерация инвентарного номера `QA-PH-NNN`, проверка уникальности
  инвентарного номера, IMEI и serial с ответом `409` и понятным кодом ошибки.
- Вычисляемое состояние устройства на бэкенде: `holder` = держатель активной
  выдачи или владелец, `overdue` по единому выражению; список и карточка
  используют один и тот же код.
- Права: `user` создаёт устройство только себе, редактирует и архивирует только
  своё; `admin` — любое. Держатель чужих устройств появится вместе с выдачами.
- История устройства: `device_events` на каждую мутацию (`created`, `updated`,
  `owner_changed`, `archived`, `restored`) и `GET /devices/{id}/history`.
- Явный отказ от физического удаления: `DELETE /devices/{id}` отвечает `405`.
- Тесты на все затронутые инварианты, `openapi.json` обновляется.

### Out of Scope

- Выдачи, возвраты, передачи, смена владельца и статуса `repair`/`lost` — B4
  (`checkout-lifecycle`, `device-ownership`).
- Управление пользователями сверх выбора владельца при создании — B5.
- Уведомления, отчёты, Excel, фото, дашборд и frontend.
- Изменения схемы БД: все нужные поля и ограничения уже есть в миграциях.

## Capabilities

### New Capabilities

Нет.

### Modified Capabilities

Нет. Изменение реализует уже описанное поведение из `device-inventory`
(карточка, уникальность, поиск, архив, восстановление, read-only архив),
`device-ownership` (владелец при создании), `access-control` (права `user` и
`admin` на устройства) и `audit-log` (события и таймлайн). Требования не
меняются, поэтому в `.openspec.yaml` установлен `skip_specs: true`.

## Impact

- Новые файлы: `backend/app/api/devices.py`, `backend/app/schemas/devices.py`,
  `backend/app/services/devices.py`, `backend/app/services/device_state.py`,
  тесты `backend/tests/test_devices_*.py`.
- Правки: `backend/app/main.py` (роутер), `backend/openapi.json`, `README.md`.
- Затрагиваемые спеки: `device-inventory`, `device-ownership`, `access-control`,
  `audit-log`.
- Схема БД и зависимости не меняются.
