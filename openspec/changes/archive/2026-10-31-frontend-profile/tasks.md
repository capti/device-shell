# Tasks

## 1. API-слой

- [x] 1.1 `frontend/src/api/profile.ts`: тип `PasswordChangePayload` и
      `changePassword(current, new)` → `POST /auth/change-password` (204).
- [x] 1.2 `frontend/src/api/devices.ts`: добавить `owner_id` и `holder_id` в
      `DeviceQuery` и в `buildQuery`.

## 2. Страница профиля

- [x] 2.1 `frontend/src/pages/profile/ProfilePage.tsx`: два блока «Владею
      (закреплено)» (`owner_id=me`) и «На руках сейчас» (`holder_id=me`) —
      таблицы со ссылками на карточку, пустые состояния.
- [x] 2.2 Компонент `ChangePasswordForm`: текущий, новый, подтверждение;
      блокировка отправки при коротком пароле или несовпадении подтверждения;
      `INVALID_PASSWORD` и прочие ошибки бэка под полем, ввод сохраняется;
      тост и очистка формы при успехе.

## 3. Маршрутизация и оболочка

- [x] 3.1 `frontend/src/routes.tsx`: маршрут `/me` внутри `ProtectedLayout`.
- [x] 3.2 `frontend/src/components/AppShell.tsx`: имя пользователя в шапке —
      ссылка на `/me`; пункт «Мои» в боковой навигации.

## 4. Проверка этапа

- [x] 4.1 `npm run build` и `npm run lint` зелёные.
- [x] 4.2 Сквозная проверка с запущенным backend: оба блока отдают свои
      устройства, смена пароля с неверным текущим → 422 `INVALID_PASSWORD` под
      полем, с верным → пароль меняется и новый работает для входа.
- [x] 4.3 README: упомянуть экран «Мои» в разделе про frontend.
- [x] 4.4 Локальный коммит этапа: `feat(frontend): profile page with password
      change`.

## Workflow follow-up

- `openspec archive frontend-profile` после принятия ревью.
- Локальный коммит архива: `chore(openspec): archive frontend-profile`.
