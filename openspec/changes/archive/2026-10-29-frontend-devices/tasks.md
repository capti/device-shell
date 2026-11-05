# Tasks

## 1. API-модули

- [x] 1.1 `src/api/devices.ts`: типы `UserBrief`, `DeviceStatus`,
      `DeviceRead`, `DeviceListResponse`, `DeviceEventRead`, `DeviceQuery`;
      функции `fetchDevices`, `fetchDevice`, `createDevice`, `updateDevice`,
      `archiveDevice`, `restoreDevice`, `fetchDeviceHistory` поверх
      `apiGet`/`apiPost`/`apiFetch`. `src/api/users.ts`: `fetchUsers`.
      Проверка: `npm run build` зелёный.

## 2. Список устройств

- [x] 2.1 `src/pages/devices/DevicesListPage.tsx`: таблица из `GET /devices`,
      состояние фильтров в `useSearchParams` (`q`, `status`, `overdue`,
      `mine`, `archived`, `sort`, `page`, `page_size`), поиск с debounce
      300 мс, чипы «Мои»/«Просроченные»/«В ремонте»/«Архив», сортировка по
      инв. №, модели и обновлению, пагинация 25/50/100, пустые состояния
      с кнопками. Проверка: `npm run build`, `npm run lint` зелёные.

- [x] 2.2 Маршруты в `routes.tsx`: `/devices` → список, `/devices/new`,
      `/devices/:id`, `/devices/:id/edit`; заглушка убирается.
      Проверка: `npm run build` зелёный.

## 3. Формы

- [x] 3.1 `src/pages/devices/DeviceFormPage.tsx`: общая форма для создания и
      редактирования на `@mantine/form`, обязательные поля блокируют
      сохранение, выбор владельца только для админа, ошибки 409/422 → тост,
      после успеха переход на карточку (создание) или возврат назад
      (редактирование). Проверка: `npm run build` зелёный.

## 4. Карточка

- [x] 4.1 `src/pages/devices/DeviceCardPage.tsx`: шапка с бейджами состояния,
      владелец/держатель, ожидаемый возврат, характеристики, таймлайн из
      `GET /devices/{id}/history`, кнопки «Редактировать»/«В архив»
      только для владельца и админа.
      Проверка: `npm run build` зелёный.

- [x] 4.2 Архив и восстановление: `Modal` с подтверждением, тост с
      `message` при `409 ACTIVE_CHECKOUT`, при `422 OWNER_REQUIRED` — выбор
      нового владельца с повторной отправкой.
      Проверка: `npm run build` зелёный.

## 5. Проверка и завершение

- [x] 5.1 `openspec validate --all --strict` зелёный (13/13, включая правку
      плейсхолдера Purpose у `frontend-shell`); `npm run build` и
      `npm run lint` зелёные; backend не менялся — `pytest` и `ruff check .`
      зелёные.

- [x] 5.2 Сквозная проверка с запущенным backend: смоук-API по всем путям и
      query-параметрам, которые строит фронт (создание, дубликат 409,
      поиск/фильтры/сортировка/пагинация, история, выдача → архив 409
      `ACTIVE_CHECKOUT`, архив → `409 DEVICE_ARCHIVED` → восстановление),
      затем через Vite-прокси на `:5173`: вход с Origin `:5173` (200/401,
      не 403) и чужой Origin (403). Выявлено: dev требует
      `APP_BASE_URL=http://localhost:5173` — исправлено в `dev.ps1` и README.
      Визуальный просмотр в браузере остаётся за разработчиком.

- [x] 5.3 Локальный коммит этапа:
      `feat(frontend): device list, forms and card`.
