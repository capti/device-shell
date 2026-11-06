# QA Test Staff

Сайт для учёта тестовых смартфонов: за кем закреплён
телефон (владелец), у кого он сейчас на руках (держатель), история выдач,
отчёты о состоянии, ремонты, фото, просрочки, Excel-экспорт и уведомления.

Как запускать: **нужна разработка** — по [SETUP.md](SETUP.md) (установка,
dev-режим, тесты, бэкап); **нужен Docker** — по [DOCKER.md](DOCKER.md)
(сборка образа, один контейнер, вход под администратором).

Реализованы backend и frontend: учёт устройств и сотрудников, оборот,
уведомления, аудит, фото и отчёты, Excel-экспорт, дашборд с графиками.
Текущие требования и инварианты определены в OpenSpec
(`openspec/specs/`); `PLAN.md` — справочник и история решений.

## Стек

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2,
  SQLite (WAL), зависимости через [uv](https://docs.astral.sh/uv/).
- Frontend: Vite 8, React, TypeScript, React Router, TanStack Query, Mantine.
- Авторизация: серверные сессии в БД + httpOnly cookie.

## Frontend

SPA на Vite + React + Mantine (тёмная тема, русский интерфейс). В dev-режиме
`:5173` проксирует `/api` на `:8000`, поэтому backend должен быть запущен.

```powershell
cd frontend
npm install
npm run dev      # http://localhost:5173
npm run build    # production-сборка в frontend/dist
```

Из корня проекта `.\dev.ps1` запускает backend и Vite одной командой: оба
процесса с горячей перезагрузкой, браузер открывается сам.

В production FastAPI раздаёт `frontend/dist` вместе с API и `/media/*` с одного
порта: файлы отдаются как есть, на навигацию браузера — `index.html`. Настройте
reverse proxy с HTTPS и направляйте в backend все пути — API идут по корневым
путям, без `/api`. Запуск в Docker — в [DOCKER.md](DOCKER.md), вариант без
Docker — в [SETUP.md](SETUP.md).

В dev браузер открывает сайт на `:5173`, поэтому мутации приходят с Origin
`http://localhost:5173`, а проверка Origin сверяет его с `APP_BASE_URL`
(по умолчанию `http://localhost:8000`). Запускайте проект из корня через
`.\dev.ps1` — он поднимает backend и Vite и задаёт
`APP_BASE_URL=http://localhost:5173` для dev-режима. Если поднимаете backend
вручную, передайте эту переменную сами:

```powershell
$env:APP_BASE_URL = "http://localhost:5173"
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

Экраны: `/login` (вход), `/dashboard` (счётчики, просрочки и графики),
`/devices` — список, создание/редактирование и карточка устройства
(характеристики, владелец и держатель, фотографии, состояние, журнал
ремонтов, история, архив; из карточки телефон выдаётся и передаётся дальше,
отправляется в ремонт и возвращается из него, помечается утерянным и
возвращается из утери);
После успешного входа браузер выполняет полную навигацию на исходную страницу.
Это не скрывает запрос входа от пользователя DevTools: логин и пароль передаются
в теле `POST /auth/login`. HTTPS защищает их при передаче по сети, но не от
просмотра в браузере самого пользователя.

Шапка всех разделов показывает уведомления со счётчиком непрочитанных:
клик по записи открывает карточку устройства.

`/people` — справочник сотрудников со счётчиками устройств (admin создаёт,
правит, деактивирует сотрудников и сбрасывает пароли);
`/reports` — отчёты «у кого что» и «просроченные», выгрузка Excel за период;
`/me` — профиль «Мои»: устройства во владении и на руках, смена собственного
пароля (имя в шапке и пункт «Мои» в навигации ведут сюда).

## Backend

### Первый запуск

```powershell
cd backend
uv sync
uv run alembic upgrade head
uv run python -m app.cli create-admin --username admin --full-name "Иван Иванов"
cd ..
.\dev.ps1
```

Пароль администратора команда запросит интерактивно (или передайте
`--password`, если запускаете в автоматизированном окружении).

Проверка:

```powershell
Invoke-RestMethod http://localhost:8000/health
# status version
# ------ -------
# ok     0.1.0
```

Из корня проекта `.\dev.ps1` запускает backend вместе с Vite — оба с горячей
перезагрузкой, флаг `-BackendOnly` оставляет только backend.

### Мониторинг с Gatus

Gatus запускается отдельным процессом и проверяет `/health` backend раз в минуту,
включая состояние БД. Для установки требуется Go:

```powershell
go install github.com/TwiN/gatus/v5@latest
```

Убедитесь, что каталог Go `bin` находится в `PATH` (по умолчанию
`$env:USERPROFILE\go\bin`). Запустите backend, затем из корня проекта:

```powershell
.\start-gatus.ps1
```

Панель доступна только на этой машине: http://localhost:8081. История проверок
сохраняется в `data/gatus.db`; уведомления во внешние каналы не настроены.

Настройки читаются из `backend/.env` (пример — `backend/.env.example`).
Основные переменные:

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `DATABASE_URL` | `sqlite:///<проект>/data/qa.db` | Подключение к БД |
| `DATA_DIR` | `<проект>/data` | Каталог данных и media |
| `APP_BASE_URL` | `http://localhost:8000` | Origin приложения для проверки мутаций |
| `SESSION_TTL_DAYS` | `7` | Срок сессии от последней активности |
| `COOKIE_SECURE` | `false` | `true` при работе по HTTPS |
| `APP_ENV` | `development` | Окружение |

### Тесты и проверки

```powershell
cd backend
uv run pytest
uv run ruff check .
```

Ревью backend дополнительно включает инструменты Uncle Bob — `crapper`
(сложность), `dryer` (дубли) и `mutator` (выживаемость тестов). Команды и
трактовка результатов — в `AGENTS.md`, раздел «Ревью».

### OpenAPI

```powershell
cd backend
uv run python -m app.export_openapi
```

Файл `backend/openapi.json` создаётся из живого приложения.

### Устройства

Все эндпоинты требуют действующую сессию (`401` без cookie).

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/devices` | Список с поиском, фильтрами, сортировкой и пагинацией |
| `POST` | `/devices` | Создание; пустой инвентарный номер получает `QA-PH-NNN` |
| `GET` | `/devices/{id}` | Карточка с владельцем, держателем и просрочкой |
| `PATCH` | `/devices/{id}` | Правка карточки (владелец или admin) |
| `POST` | `/devices/{id}/archive` | В архив, только без активной выдачи |
| `POST` | `/devices/{id}/restore` | Из архива; тело необязательно |
| `GET` | `/devices/{id}/history` | События устройства, новые сверху |
| `POST` | `/devices/{id}/checkout` | Выдача другому сотруднику |
| `POST` | `/devices/{id}/return` | Возврат с фиксацией состояния |
| `POST` | `/devices/{id}/transfer` | Передача другому держателю |
| `POST` | `/devices/{id}/owner` | Смена владельца |
| `POST` | `/devices/{id}/status` | `lost` и возврат из `lost` |
| `GET` | `/devices/{id}/checkouts` | История выдач, новые сверху |
| `GET` | `/devices/{id}/repairs` | Журнал ремонтов, новые сверху |
| `POST` | `/devices/{id}/repairs` | Отправить устройство в ремонт |
| `POST` | `/devices/{id}/repairs/{repair_id}/finish` | Завершить ремонт |
| `GET` | `/devices/{id}/condition-reports` | Отчёты о состоянии |
| `POST` | `/devices/{id}/condition-reports` | Оставить отчёт о состоянии |
| `DELETE` | `/devices/{id}` | Всегда `405`: физического удаления нет |

Параметры `GET /devices`: `q` (инв. №, IMEI, serial, модель, бренд, ФИО
владельца или держателя), `status` (`active|repair|lost`), `owner_id`,
`holder_id`, `overdue`, `mine`, `archived` (`false` по умолчанию, `true`,
`all`), `sort` (`inventory_no`, `model`, `updated_at`, с `-` для убывания),
`page`, `page_size` (по умолчанию 25, максимум 100).

Тело `POST /devices/{id}/restore` необязательно:
`{"owner_id": 3, "status": "repair"}`. Новый владелец обязателен, если прежний
деактивирован; статус по умолчанию `active`.

Коды ошибок устройств: `DEVICE_NOT_FOUND`, `REPAIR_NOT_FOUND` (404);
`INVENTORY_TAKEN`, `IMEI_TAKEN`, `SERIAL_TAKEN`, `ACTIVE_CHECKOUT`,
`ALREADY_ARCHIVED`, `NOT_ARCHIVED`, `DEVICE_ARCHIVED`, `DEVICE_UNAVAILABLE`,
`ALREADY_CHECKED_OUT`, `SELF_CHECKOUT`, `NO_ACTIVE_CHECKOUT`, `SAME_HOLDER`,
`REPAIR_ALREADY_FINISHED`, `INVALID_STATUS_TRANSITION` (409);
`OWNER_INACTIVE`, `OWNER_REQUIRED`, `HOLDER_INACTIVE`, `COMMENT_REQUIRED`,
`VALIDATION_ERROR` (422); `FORBIDDEN` (403).

### Оборот устройства

- `POST /devices/{id}/checkout` — тело `{"holder_id": 2,
  "expected_return_at": "2026-11-11", "condition_out": "ok",
  "comment_out": "..."}`. Владелец или admin. Дату можно не указывать: по
  умолчанию +14 дней. Выдать самому себе нельзя (`SELF_CHECKOUT`), повторно —
  тоже (`ALREADY_CHECKED_OUT`), архивное/`repair`/`lost` — `DEVICE_ARCHIVED`
  или `DEVICE_UNAVAILABLE`.
- `POST /devices/{id}/return` — тело `{"condition_in": "scratches",
  "comment_in": "...", "requires_repair": false}`. Держатель, владелец или
  admin. Состояние обязательно, отчёт создаётся вместе с закрытием выдачи.
- `POST /devices/{id}/transfer` — тело `{"holder_id": 3,
  "condition_in": "ok", "comment": "..."}`. Держатель, владелец или admin.
  Прежняя выдача закрывается с причиной `transferred`, открывается новая.
- `POST /devices/{id}/owner` — тело `{"owner_id": 3}`. Владелец или admin.
  Если новый владелец — текущий держатель, выдача закрывается автоматически
  (`ownership_transferred`).
- `POST /devices/{id}/status` — тело `{"status": "lost"}` или
  `{"status": "active", "comment": "где нашёлся"}`. Возврат из `lost` требует
  комментарий (`COMMENT_REQUIRED`).
- `POST /devices/{id}/repairs` — тело `{"service": "Сервис",
  "description": "Замена экрана", "cost": 12000, "comment": "..."}`.
  Владелец или admin, только без активной выдачи. Устройство получает статус
  `repair`. Завершение — `POST /devices/{id}/repairs/{repair_id}/finish` с
  необязательными `returned_at` и `comment`.
- `POST /devices/{id}/condition-reports` — тело `{"condition": "ok",
  "requires_repair": false, "comment": "..."}`. Держатель, владелец или
  admin; отчёт не закрывает выдачу и не меняет статус устройства.

События оборота попадают в `GET /devices/{id}/history`: `checked_out`,
`returned`, `transferred`, `checkout_closed`, `owner_changed`,
`condition_reported`, `repair_started`, `repair_finished`, `status_changed`.

### Сотрудники

Чтение справочника доступно любому авторизованному, изменения — только admin.

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/users` | Список со счётчиками; по умолчанию только активные |
| `GET` | `/users/{id}` | Карточка сотрудника со счётчиками |
| `POST` | `/users` | Создание сотрудника (admin) |
| `PATCH` | `/users/{id}` | ФИО, контакты и роль (admin) |
| `POST` | `/users/{id}/deactivate` | Деактивация с автоархивом устройств |
| `POST` | `/users/{id}/activate` | Возврат доступа |
| `POST` | `/users/{id}/password` | Сброс пароля администратором |
| `DELETE` | `/users/{id}` | Всегда `405`: физического удаления нет |
| `POST` | `/auth/change-password` | Смена собственного пароля |

`GET /users?include_inactive=true` показывает и деактивированных — для
админского справочника. Селекторы владельца и держателя используют список по
умолчанию и не предлагают уволенных.

Счётчики в ответе: `devices_owned` — все устройства во владении, включая
архивные; `devices_held` — устройства на руках по активным выдачам. Логин
после создания не меняется: это идентификатор входа.

Деактивация архивирует все неархивные устройства сотрудника в одной
транзакции (событие `archived`, `payload.reason = "owner_deactivated"`),
статусы `repair`/`lost` сохраняются. Если его устройство сейчас у коллеги или
у него на руках чужой телефон, ответ — `409 HAS_DEVICES` со списком
инвентарных номеров в сообщении. Последнего активного admin нельзя
разжаловать или деактивировать (`409 LAST_ADMIN`).

Сброс пароля администратором не требует старого пароля; длина — от 8
символов. Смена своего пароля требует `current_password`; сессии при этом не
отзываются.

Коды ошибок сотрудников: `USER_NOT_FOUND` (404); `USERNAME_TAKEN`,
`ALREADY_INACTIVE`, `ALREADY_ACTIVE`, `LAST_ADMIN`, `HAS_DEVICES` (409);
`WEAK_PASSWORD`, `INVALID_PASSWORD`, `VALIDATION_ERROR` (422); `FORBIDDEN`
(403); `METHOD_NOT_ALLOWED` (405).

### Уведомления

Лента событий: смена владельца, архив/восстановление, `lost`/ремонт, выдача,
возврат, отчёт о состоянии, просрочка выдачи и события учётных записей
(деактивация, смена роли, сброс пароля). Просрочка материализуется при чтении
списка. У каждого свой ленточного инвентарного номера свой контекст.

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/notifications` | Список с пагинацией и счётчиком `unread` |
| `POST` | `/notifications/{id}/read` | Отметить одно прочитанным |
| `POST` | `/notifications/read-all` | Прочитать всё, `{"updated": N}` |

Параметры `GET /notifications`: `page`, `page_size` (до 100), `unread_only`.
Ответ: `{items, total, page, page_size, unread}` — только свои уведомления;
`404 NOTIFICATION_NOT_FOUND` на чужом или неизвестном `id`. Просроченные
уведомления держатся 90 дней с момента создания. Типы: `owner_changed`,
`device_archived`, `device_restored`, `device_lost`, `requires_repair`,
`device_checked_out`, `device_returned`, `condition_reported`,
`checkout_overdue`, `user_deactivated`, `role_changed`, `password_reset`.

### Аудит

Два журнала для администратора: события устройств и попытки входа. Оба
append-only — изменения и удаление строк запрещены на уровне БД (триггеры),
поэтому история хранится бессрочно.

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/audit/events` | События устройств: тип, автор, время, payload |
| `GET` | `/audit/logins` | Попытки входа: время, логин, исход, причина, IP, user-agent |

`GET /audit/events` фильтруется по `device_id`, `from_at`, `to_at`; без фильтров
отдаёт последние 30 дней. Границы дат включительны (00:00–23:59:59 локального
времени). Ответ — `{events, total}`.

`GET /audit/logins` пишет каждую попытку входа — успешную и неуспешную — со
временем, введённым логином, исходом, причиной отказа (`invalid_credentials`,
`inactive_user`, `rate_limited`), IP и user-agent. Запись создаётся отдельной
сессией БД, поэтому переживает откат транзакции при `401`/`429`. Фильтры:
`from_at`, `to_at`, `success`, `username`; ответ ограничен `limit` (по умолчанию
200, максимум 1000), а `total` остаётся полным числом подходящих записей. Оба
журнала доступны только admin; для `user` — `403 FORBIDDEN`.

### Отчёты и Excel

Дашборд, отчёты «у кого что» и «просроченные» и выгрузка Excel доступны
любому авторизованному сотруднику. Просрочка везде одна — из `device_state`
(инвариант 6).

| Метод | Путь | Назначение |
|---|---|---|
| `GET` | `/dashboard/stats` | Счётчики (`counters`) и топ-5 давних просрочек |
| `GET` | `/dashboard/charts` | Данные графиков дашборда |
| `GET` | `/reports/holders` | «У кого что»: устройство — владелец — держатель |
| `GET` | `/reports/overdue` | Просроченные: выдача, срок, дней просрочки |
| `GET` | `/reports/export.xlsx` | Excel: «Все устройства», «Просроченные», «История выдач» |

`GET /reports/export.xlsx` принимает те же параметры фильтров, что
`GET /devices` (`q`, `status`, `owner_id`, `holder_id`, `overdue`, `mine`,
`archived`), плюс период истории `from_date`/`to_date` (ISO-даты, по умолчанию
с начала года по сегодня). На листах с устройствами производитель указан
отдельной колонкой перед моделью.


```powershell
# Вход: пароль запрашивается без эха в консоль и не сохраняется в исходнике.
$securePassword = Read-Host "Пароль" -AsSecureString
$password = [System.Net.NetworkCredential]::new("", $securePassword).Password
$loginBody = @{ username = "admin"; password = $password } | ConvertTo-Json
Invoke-RestMethod -Method Post http://localhost:8000/auth/login `
  -ContentType "application/json" `
  -Body $loginBody `
  -SessionVariable session
# Создание устройства
Invoke-RestMethod -Method Post http://localhost:8000/devices `
  -ContentType "application/json" `
  -Body '{"brand":"Samsung","model":"Galaxy S23"}' `
  -WebSession $session
Invoke-RestMethod "http://localhost:8000/devices?q=galaxy" -WebSession $session
```

### Обслуживание

- Схема меняется только миграциями: `uv run alembic revision --autogenerate -m "..."`,
  затем `uv run alembic upgrade head`.
- Откат в dev: `uv run alembic downgrade base` и удаление `data/qa.db`.
- Файлы базы и фото лежат в `data/` — бэкапить нужно весь каталог.
- Восстановить пароль через email нельзя: пароль задаёт администратор при
  создании или сбрасывает через `POST /users/{id}/password`. Свой пароль
  пользователь меняет в `POST /auth/change-password`.

### Бэкап и восстановление

`backup.ps1` (или `uv run python -m app.cli backup`) копирует базу и `media` в
`data/backups/qa-backup-<дата>_<время>/`. Копия базы снимается через SQLite
backup API, поэтому режим WAL её не портит. Хранятся 14 последних копий,
более старые удаляются сразу после создания новой.

```powershell
# копия вручную, лимит хранения по умолчанию — 14
.\backup.ps1
uv run python -m app.cli backup --keep 14

# восстановление: сначала остановить uvicorn
uv run python -m app.cli restore data/backups/qa-backup-2026-10-30_02-00-00 --yes
```

Планировщик Windows: задача «Ежедневно», действие
`powershell -ExecutionPolicy Bypass -File <путь>\backup.ps1`. Каталог
`data/backups/` лежит рядом с базой, поэтому его нужно включать в бэкап машины.
Проверку восстановления делают вручную раз в квартал (R5).

### Логи

Приложение пишет JSON-строки в stderr: `timestamp` (UTC), `level`, `logger`,
`message` и поля события. Для каждого HTTP-запроса есть `method`, `path`,
`status_code`, `duration_ms`; сбой пишется уровнем ERROR с трейсбеком в поле
`exception`. Тело запроса, cookie и заголовок `Authorization` не логируются.

```powershell
# уровень: DEBUG, INFO (по умолчанию), WARNING, ERROR
$env:LOG_LEVEL = "WARNING"
uv run uvicorn app.main:app --port 8000
```

Вывод идёт в stderr; если нужен файл, перенаправьте поток при запуске или
настройте перенаправление в задаче Планировщика.

## Важные ограничения

- **Ровно один процесс uvicorn.** Не запускайте `uvicorn --workers 2`:
  SQLite сериализует записи, а rate limit попыток входа хранится в памяти
  процесса. Для локального хостинга этого достаточно.
- **Время хранится в локальном поясе сервера** (naive datetime). Просрочка
  считается по локальной дате. При переезде сервера в другой часовой пояс
  данные придётся пересчитывать.
- **Origin мутаций** проверяется по `APP_BASE_URL`. В production мутация без
  заголовка `Origin` тоже отклоняется с `403`; в dev/test такие запросы
  разрешены для curl и тестов. Если приложение открывается по другому адресу,
  обновите переменную.
- Ошибки API всегда возвращаются как `{"code": "...", "message": "..."}`;
  `message` на русском.
- Физического удаления устройств и пользователей нет: только архив и
  деактивация.

## Инварианты и их тесты

Список инвариантов — `openspec/config.yaml`. Каждый закреплён тестом в
`backend/tests/`; при изменении правила сначала меняется спека, затем тест.

| # | Инвариант | Где закреплён |
|---|---|---|
| 1 | У устройства ровно один владелец, обязателен | `test_models_devices.py`, `test_devices_create.py` |
| 2 | Не более одной активной выдачи (partial unique index) | `test_models_checkouts.py`, `test_checkouts.py` |
| 3 | Нельзя выдать устройство самому себе | `test_checkouts.py::test_self_checkout_is_rejected`, `test_transfer.py` |
| 4 | Передача владения держателю закрывает выдачу (`ownership_transferred`) | `test_owner_change.py` |
| 5 | Архив только без активной выдачи → `409 ACTIVE_CHECKOUT` | `test_devices_archive.py` |
| 6 | Просрочка считается только на бэкенде одной функцией | `test_device_state.py`, `test_export.py::test_overdue_matches_everywhere` |
| 7 | Физического удаления нет (архив, деактивация, append-only события) | `test_devices_update.py::test_physical_delete_is_forbidden`, `test_models_events.py` |
| 8 | Деактивация отправляет устройства в архив, при выдачах → 409 | `test_users_deactivate.py` |
| 9 | Каждая мутация пишет `device_events` в той же транзакции | `test_device_state.py::test_record_event_rolls_back_with_transaction` |
| 10 | Архивное устройство read-only до восстановления | `test_devices_update.py`, `test_status.py`, `test_photos.py`, `test_condition_reports.py` |
| 11 | Выдача запрещена для `repair`/`lost` и архивных | `test_checkouts.py::test_repair_and_lost_devices_are_unavailable` |
| 12 | Последнего активного admin нельзя разжаловать или деактивировать | `test_users_admin.py`, `test_users_deactivate.py` |

## Структура backend

```
backend/app/{main.py, config.py, db.py, errors.py, middleware.py, clock.py,
             cli.py, logs.py, spa.py, entrypoint.py}
backend/app/models/     # SQLAlchemy-модели
backend/app/schemas/    # Pydantic-схемы
backend/app/api/        # тонкие роуты и зависимости
backend/app/services/   # бизнес-логика
backend/alembic/        # миграции
backend/tests/          # pytest
```
