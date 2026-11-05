# Tasks

## 1. Страница профиля

- [x] 1.1 `frontend/src/pages/profile/ProfilePage.tsx`: убрать инлайн-блок
      «Смена пароля» (`Divider`, заголовок, `ChangePasswordForm`), добавить
      кнопку «Сменить пароль» в шапке страницы.
- [x] 1.2 `ChangePasswordModal`: та же форма в Mantine `Modal` (`centered`,
      заголовок «Смена пароля») с кнопкой «Отмена»; после успеха — тост и
      закрытие окна; ошибки сервера остаются в окне, ввод сохраняется.

## 2. Проверка этапа

- [x] 2.1 `npm run build` и `npm run lint` зелёные.
- [x] 2.2 Сквозная проверка: кнопка открывает окно, короткий пароль и
      несовпадение подтверждения блокируют отправку, неверный текущий пароль →
      422 `INVALID_PASSWORD` в окне, верный → пароль меняется, окно
      закрывается, новый пароль работает для входа.
- [x] 2.3 `openspec validate --all --strict` зелёный.
- [x] 2.4 Локальный коммит: `feat(frontend): change password in modal on
      profile page`.

## Workflow follow-up

- `openspec archive profile-password-modal` после принятия ревью.
- Локальный коммит архива: `chore(openspec): archive profile-password-modal`.
