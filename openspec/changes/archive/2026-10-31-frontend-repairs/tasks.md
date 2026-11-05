# Tasks

## 1. API-слой

- [x] 1.1 `frontend/src/api/repairs.ts`: тип `RepairRead`,
      `fetchRepairs(deviceId)`, `startRepair(deviceId, payload)`,
      `finishRepair(deviceId, repairId, payload)`.
      Проверка: `npm run build` — типы сходятся с ответом бэка.

## 2. Раздел «Ремонты»

- [x] 2.1 `frontend/src/components/RepairsJournal.tsx`: таблица записей
      (дата отправки, возврата, сервис, описание, стоимость, комментарий,
      автор), бейдж «В ремонте» для незакрытой записи, пустое состояние
      «Ремонтов не было». Проверка: сборка.
- [x] 2.2 Модалка «Отправить в ремонт»: сервис, описание, стоимость,
      комментарий; кнопка только для владельца/admin на неархивном `active`;
      ошибки `ACTIVE_CHECKOUT`/`DEVICE_UNAVAILABLE` тостом.
- [x] 2.3 Модалка «Завершить ремонт»: дата возврата (по умолчанию сегодня) и
      комментарий; 422 по дате — под полем, ввод сохраняется;
      `REPAIR_ALREADY_FINISHED` — тост и перезапрос списка.

## 3. Карточка и документация

- [x] 3.1 `DeviceCardPage`: запрос `['device-repairs', id]`, раздел
      «Ремонты» между «Состояние» и «История», `onMutated` обновляет
      ремонты вместе с остальным.
- [x] 3.2 README: в описании карточки упомянуть журнал ремонтов.

## 4. Проверка этапа

- [x] 4.1 `npm run build` и `npm run lint` зелёные,
      `openspec validate --all --strict` зелёный.
- [x] 4.2 Сквозная проверка с запущенным backend: выданное устройство →
      409 `ACTIVE_CHECKOUT`, свободное → запись создаётся и статус
      `repair`, завершение → `active`, повторное завершение → 409
      `REPAIR_ALREADY_FINISHED`, дата раньше отправки → 422.
- [x] 4.3 Локальный коммит этапа: `feat(frontend): repair journal in device
      card`.

## Workflow follow-up

- `openspec archive frontend-repairs` после принятия ревью.
- Локальный коммит архива: `chore(openspec): archive frontend-repairs`.
