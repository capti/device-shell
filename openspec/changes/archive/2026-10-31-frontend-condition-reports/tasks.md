# Tasks

## 1. API и подписи

- [x] 1.1 `src/api/maintenance.ts`: типы `ConditionValue`,
      `ConditionReportRead`, `fetchConditionReports`,
      `createConditionReport`. Проверка: `npm run build`.
- [x] 1.2 `src/api/rotation.ts`: `returnDevice(deviceId, payload)`.
      Проверка: `npm run build`.
- [x] 1.3 `src/lib/condition.ts`: варианты, подписи и цвета состояний.
      Проверка: `npm run lint`.

## 2. Раздел состояния

- [x] 2.1 `src/components/PhotoPicker.tsx`: выбор нескольких файлов, список
      выбранного, ограничение по остатку лимита. Проверка: используется в двух
      окнах.
- [x] 2.2 `src/components/ConditionReports.tsx`: список отчётов с фото и
      пустым состоянием. Проверка: сборка и карточка с отчётами.
- [x] 2.3 Окно «Добавить отчёт»: состояние, флаг, комментарий, фото; создание
      через API и загрузка фото с `report_id`. Проверка: отчёт и фото видны в
      разделе, выдача не закрывается.
- [x] 2.4 Окно «Вернуть»: обязательное состояние, флаг, комментарий, фото;
      после возврата фото прикрепляются к созданному отчёту. Проверка: держатель
      снова владелец, отчёт с фото в списке.

## 3. Карточка и документация

- [x] 3.1 `DeviceCardPage`: запрос отчётов, раздел между фото и историей,
      права владельца/держателя/admin, архив только для чтения.
- [x] 3.2 README: упомянуть раздел состояния в описании карточки.

## 4. Проверка этапа

- [x] 4.1 `npm run build` и `npm run lint` зелёные.
- [x] 4.2 Сквозная проверка с backend: создание отчёта с фото, возврат с фото,
      `NO_ACTIVE_CHECKOUT` при повторном возврате.
- [x] 4.3 Локальный коммит этапа:
      `feat(frontend): condition reports and return with photos`.

## Workflow follow-up

- `openspec archive frontend-condition-reports` после принятия ревью.
- Локальный коммит архива:
  `chore(openspec): archive frontend-condition-reports`.
