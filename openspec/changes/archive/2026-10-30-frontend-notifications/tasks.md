## 1. API и словарь

- [x] 1.1 `api/notifications.ts`: типы, `fetchNotifications`, `markNotificationRead`,
      `markAllNotificationsRead`.
- [x] 1.2 `lib/notifications.ts`: русские подписи типов и цвета.

## 2. Компонент

- [x] 2.1 `components/NotificationsBell.tsx`: кнопка со счётчиком и Popover.
- [x] 2.2 Список с прокруткой, «Показать ещё», пустое состояние.
- [x] 2.3 Клик: отметить прочитанным и перейти к устройству.
- [x] 2.4 «Прочитать всё», опрос раз в минуту, инвалидация кэша.

## 3. Оболочка

- [x] 3.1 Подключить колокольчик в шапку `AppShell`, обновить README.

## 4. Проверка

- [x] 4.1 `npm run build`, `npm run lint`.
- [x] 4.2 Сквозная проверка чтения и отметок на изолированном бэкенде.
- [x] 4.3 `openspec validate --all --strict`.
