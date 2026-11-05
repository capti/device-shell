# Tasks

## 1. API-слой

- [x] 1.1 `frontend/src/api/rotation.ts`: `changeStatus(deviceId, payload)` с
      телом `{status, comment?}` → `DeviceRead`. Проверка: `npm run build`.

## 2. Диалоги статуса

- [x] 2.1 `frontend/src/components/StatusDialogs.tsx`: окно «Потерян» —
      подтверждение с необязательным комментарием; окно «Найден» —
      обязательный комментарий, кнопка заблокирована при пустом поле.
- [x] 2.2 Ошибки: 422 `COMMENT_REQUIRED` — под полем, ввод сохраняется;
      `INVALID_STATUS_TRANSITION` / `DEVICE_ARCHIVED` — тост с текстом бэка и
      закрытие окна.

## 3. Карточка и документация

- [x] 3.1 `DeviceCardPage`: кнопки в шапке — «Потерян» при `active`,
      «Найден» при `lost`, только для `canManage` и без архива; `onMutated`
      обновляет устройство и историю.
- [x] 3.2 README: упомянуть отметку об утере и возврат из утери.

## 4. Проверка этапа

- [x] 4.1 `npm run build` и `npm run lint` зелёные,
      `openspec validate --all --strict` зелёный.
- [x] 4.2 Сквозная проверка с запущенным backend: `active` → `lost` (200,
      событие в истории), повторный `lost` → 409
      `INVALID_STATUS_TRANSITION`, `lost` → `active` без комментария → 422
      `COMMENT_REQUIRED`, с комментарием → 200, выдача утерянного → 409
      `DEVICE_UNAVAILABLE`.
- [x] 4.3 Локальный коммит этапа: `feat(frontend): mark device lost and
      return it from the card`.

## Workflow follow-up

- `openspec archive frontend-device-status` после принятия ревью.
- Локальный коммит архива: `chore(openspec): archive frontend-device-status`.
