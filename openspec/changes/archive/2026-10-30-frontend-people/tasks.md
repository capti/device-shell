## 1. API-клиент

- [x] 1.1 `api/users.ts`: `createUser`, `updateUser`, `deactivateUser`,
      `activateUser`, `resetUserPassword` и payload-типы.

## 2. Страница

- [x] 2.1 `pages/people/PeoplePage.tsx`: таблица со счётчиками, ролью, статусом.
- [x] 2.2 Клиентский поиск и переключатель «показывать деактивированных» для admin.
- [x] 2.3 `UserFormModal`: создание и правка (логин только для чтения при правке).
- [x] 2.4 `PasswordModal`: сброс пароля с проверкой 8 символов.
- [x] 2.5 Диалог деактивации с предупреждением и показом `HAS_DEVICES`.
- [x] 2.6 Маршрут `/people` вместо заглушки, обновление README.

## 3. Проверка

- [x] 3.1 `npm run build`, `npm run lint`.
- [x] 3.2 Сквозная проверка мутаций справочника на изолированном бэкенде.
- [x] 3.3 `openspec validate --all --strict`.
