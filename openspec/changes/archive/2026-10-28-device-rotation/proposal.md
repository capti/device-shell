# Proposal

## Why

Карточка, список и архив устройств готовы (B3), но телефон пока нельзя ни
выдать, ни вернуть, ни передать другому владельцу. Без оборота система не
решает главную задачу — показывать, у кого телефон на руках и не просрочен ли
возврат. Это следующий шаг backend (B4): владение, выдача, возврат, передача,
статусы, отчёты о состоянии и журнал ремонтов.

## What Changes

- Смена владельца: `POST /devices/{id}/owner` — владелец или admin; новый
  владелец обязан быть активным; передача текущему держателю автозакрывает
  выдачу с причиной `ownership_transferred`.
- Выдача: `POST /devices/{id}/checkout` — владелец или admin, запрет выдачи
  самому себе (`409 SELF_CHECKOUT`), повторной выдачи
  (`409 ALREADY_CHECKED_OUT`), архивного (`409 DEVICE_ARCHIVED`) и
  недоступного устройства (`409 DEVICE_UNAVAILABLE`); дата возврата по
  умолчанию +14 дней, дата в прошлом — 422.
- Возврат: `POST /devices/{id}/return` — держатель, владелец или admin;
  закрывает выдачу причиной `returned`, пишет состояние и создаёт отчёт о
  состоянии в той же транзакции; без активной выдачи —
  `409 NO_ACTIVE_CHECKOUT`.
- Передача между держателями: `POST /devices/{id}/transfer` — держатель,
  владелец или admin; закрывает прежнюю выдачу причиной `transferred` и
  открывает новую на другого сотрудника одной транзакцией.
- История выдач устройства: `GET /devices/{id}/checkouts`.
- Статусы: `POST /devices/{id}/status` для `lost` и возврата из `lost` с
  обязательным комментарием; `repair` меняется только через журнал ремонтов.
- Журнал ремонтов: `GET|POST /devices/{id}/repairs` и
  `POST /devices/{id}/repairs/{repair_id}/finish`; в ремонт нельзя отправить
  устройство с активной выдачей (`409 ACTIVE_CHECKOUT`), из ремонта нельзя
  выдать (`409 DEVICE_UNAVAILABLE`).
- Отчёты о состоянии без фото: `GET|POST /devices/{id}/condition-reports`;
  отчёт доступен держателю, владельцу и admin, флаг `requires_repair` не меняет
  статус устройства.
- События `device_events` на каждую мутацию: `owner_changed`, `checked_out`,
  `returned`, `transferred`, `checkout_closed`, `condition_reported`,
  `repair_started`, `repair_finished`, `status_changed`.
- Тесты на все затронутые инварианты; `openapi.json` и `README.md`
  обновляются.

### Out of Scope

- Уведомления о выдаче, возврате, смене владельца, утере и запросе ремонта —
  B6 (`notifications`). Триггеры появятся вместе с API уведомлений, чтобы не
  писать их дважды.
- Фотографии отчётов, превью и раздача `/media/*` — B8.
- Управление пользователями (`/users`) и дашборд — B5.
- Excel-экспорт, дашборд, просрочка как отдельная ручка — B7.
- Физическое удаление записей, изменение схемы БД и миграции: все нужные
  таблицы и ограничения уже есть.

## Capabilities

### New Capabilities

Нет.

### Modified Capabilities

- `device-inventory`: добавляется требование о переводе устройства в `lost` и
  возврате из `lost` с обязательным комментарием (PLAN C7, ранее в спеке не
  было). Остальное поведение уже описано.

Остальные требования реализуются как есть, без изменения текста:
`checkout-lifecycle` (выдача, одна активная выдача, дата возврата, возврат,
закрытие владельцем, передача, держатель, просрочка, запрет выдачи
недоступных), `device-ownership` (смена владельца, автозакрытие выдачи),
`repair-journal` (отправка, завершение, запрет оборота, история),
`condition-reports` (отчёт, отчёт без возврата, состояние при возврате, флаг
ремонта), `access-control` (права держателя), `audit-log` (события и
таймлайн).

## Impact

- Новые файлы: `backend/app/schemas/rotation.py`,
  `backend/app/schemas/maintenance.py`, `backend/app/services/checkouts.py`,
  `backend/app/services/ownership.py`, `backend/app/services/maintenance.py`,
  `backend/app/services/condition_reports.py`, `backend/app/api/rotation.py`,
  `backend/app/api/maintenance.py`, тесты `backend/tests/test_checkout*.py`,
  `test_return.py`, `test_transfer.py`, `test_owner_change.py`,
  `test_status.py`, `test_repairs.py`, `test_condition_reports.py`.
- Правки: `backend/app/services/device_state.py` (поиск активной выдачи),
  `backend/app/services/devices.py` (запрет правки архивного устройства
  остаётся; используется общий помощник), `backend/app/main.py` (роутеры),
  `backend/openapi.json`, `README.md`.
- Затрагиваемые спеки: `checkout-lifecycle`, `device-ownership`,
  `repair-journal`, `condition-reports`, `access-control`, `audit-log`,
  `device-inventory`.
- Схема БД и зависимости не меняются, миграции не нужны.
