## Why

Уведомления полностью реализованы на бэке (`GET /notifications`,
`POST /notifications/{id}/read`, `POST /notifications/read-all` с полем `unread`),
но интерфейс о них не знает: владелец не видит, что его телефон выдали, а админ —
что сотрудник ушёл в архив. Счётчик непрочитанных существует только в API.

## What Changes

- Колокольчик в шапке: кнопка «Уведомления» со счётчиком непрочитанных.
- Выпадающий список своих уведомлений: тип на русском, инвентарный номер,
  автор события и время; непрочитанные выделены.
- Клик по уведомлению отмечает его прочитанным и открывает карточку устройства.
- «Прочитать всё» одним действием, «Показать ещё» для длинного списка.
- Счётчик обновляется опросом раз в минуту и после локальных действий.

## Impact

- Affected specs: `frontend-notifications` (новая), `frontend-shell` (дельта:
  шапка содержит колокольчик).
- Affected code: `frontend/src/api/notifications.ts`,
  `frontend/src/lib/notifications.ts`,
  `frontend/src/components/NotificationsBell.tsx`,
  `frontend/src/components/AppShell.tsx`.
- Бэкенд не меняется.
