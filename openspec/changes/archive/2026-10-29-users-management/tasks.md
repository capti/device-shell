# Tasks

## 1. Схемы и чтение справочника

- [x] 1.1 Описать `app/schemas/users.py`: `UserCreate`, `UserUpdate`,
  `PasswordReset`, `PasswordChange`, `UserRead` со счётчиками
  `devices_owned`/`devices_held` и `extra="forbid"`; проверить, что
  `username` в `UserUpdate` даёт `422`
- [x] 1.2 Добавить в `app/services/users.py` выборку сотрудников с двумя
  агрегатами (владение включая архив, активные выдачи) и `include_inactive`;
  проверить тестами счётчики: архивное устройство входит в «владеет», чужое
  устройство на руках — в «на руках»
- [x] 1.3 Реализовать `GET /users` и `GET /users/{id}` в
  `app/api/users.py`, подключить роутер в `app/main.py`; проверить тестами,
  что по умолчанию деактивированных нет, `include_inactive=true` их
  показывает, карточка отдаёт те же счётчики, неизвестный id — `404
  USER_NOT_FOUND`, без сессии — `401`

## 2. Создание и редактирование

- [x] 2.1 Реализовать `POST /users` (admin) поверх `create_user`; проверить
  тестами `201`, дубликат username — `409 USERNAME_TAKEN`, короткий пароль —
  `422 WEAK_PASSWORD`, `user` — `403`
- [x] 2.2 Добавить общий помощник «последний активный admin» и реализовать
  `PATCH /users/{id}` для ФИО, контактов и роли; проверить тестами сохранение
  полей, `422` на пустое ФИО, `403` для `user`, `404` для неизвестного id и
  `409 LAST_ADMIN` при разжаловании последнего админа

## 3. Деактивация и активация

- [x] 3.1 Реализовать `POST /users/{id}/deactivate`: проверки
  `ALREADY_INACTIVE`, `LAST_ADMIN`, `HAS_DEVICES`, затем архив всех неархивных
  устройств с событием `archived` и `is_active = False` в одной транзакции;
  проверить тестом, что устройства получили `archived_at`, статусы не
  изменились, события видны в истории, а вход деактивированному закрыт
- [x] 3.2 Проверить тестами оба случая `HAS_DEVICES`: устройство владельца на
  руках у коллеги и чужое устройство на руках у деактивируемого; в сообщении
  есть инвентарные номера
- [x] 3.3 Реализовать `POST /users/{id}/activate`; проверить тестами возврат
  доступа, сохранение устройств в архиве, `409 ALREADY_ACTIVE` при повторной
  активации и `403` для `user`

## 4. Пароли

- [x] 4.1 Реализовать `POST /users/{id}/password` (admin, от 8 символов,
  `204`); проверить тестами вход с новым паролем, `422 WEAK_PASSWORD`, `403`
  для `user` и `404` для неизвестного id
- [x] 4.2 Реализовать `POST /auth/change-password` с проверкой текущего
  пароля; проверить тестами успех, `422 INVALID_PASSWORD` при неверном
  текущем, `422 WEAK_PASSWORD` при коротком новом и `401` без сессии

## 5. Запрет удаления

- [x] 5.1 Реализовать `DELETE /users/{id}` с ответом `405` и сообщением о
  деактивации; проверить тестом и отсутствие параметров тела

## 6. Интеграция и документация

- [x] 6.1 Добавить тест в `test_openapi.py` на новые пути `/users`,
  `/users/{user_id}`, `/users/{user_id}/deactivate`, `/users/{user_id}/activate`,
  `/users/{user_id}/password`, `/auth/change-password`; выгрузить
  `backend/openapi.json`
- [x] 6.2 Обновить `README.md`: таблица эндпоинтов `/users`, права, коды
  ошибок (`USER_NOT_FOUND`, `ALREADY_INACTIVE`, `ALREADY_ACTIVE`, `LAST_ADMIN`,
  `HAS_DEVICES`, `WEAK_PASSWORD`, `INVALID_PASSWORD`), сброс и смена пароля
- [x] 6.3 Прогнать `uv run pytest` и `uv run ruff check .` — всё зелёное
- [x] 6.4 Прогнать `crapper`, `dryer` и `mutator` по инструкции из
  `AGENTS.md`, устранить выжившие мутации и дубли, зафиксировать результат
  (crapper: максимум CRAP 6.0; dryer: дублей нет; mutator: 157 killed,
  0 survived, score 100%)

## Workflow follow-up

- Прогнать `openspec validate --all --strict`.
- Сделать локальный коммит с сообщением в формате Conventional Commits.
- Архивировать change после ревью: `openspec archive users-management`.
