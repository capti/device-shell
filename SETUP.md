# Установка и запуск

Инструкция для чистой машины. Подробности по API и обслуживанию — в `README.md`,
правила разработки — в `AGENTS.md`.

## Что нужно поставить

| Инструмент | Версия | Зачем |
|---|---|---|
| Python | 3.12 | backend |
| [uv](https://docs.astral.sh/uv/) | актуальная | зависимости backend |
| Node.js | 20.19+ или 22.12+ | frontend (Vite 8) |
| npm | входит в Node | пакеты frontend |
| PowerShell | 5.1+ | `dev.ps1`, `backup.ps1` |

После установки зависимостей приложение не обращается к внешним сервисам и
работает без интернета. Для первичной установки `uv` и `npm` скачивают пакеты.

## Первая установка

```powershell
# 1. Клонировать репозиторий и перейти в него
cd D:\repos

# 2. Backend: зависимости и схема БД
cd qa-test-staff\backend
uv sync
uv run alembic upgrade head

# 3. Первый администратор (пароль спросит интерактивно)
uv run python -m app.cli create-admin --username admin --full-name "Иван Иванов"

# 4. Настройки (необязательно: работают значения по умолчанию)
Copy-Item .env.example .env

# 5. Frontend: зависимости
cd ..\frontend
npm install
```

База `data/qa.db` и каталог фото `data/media/` создаются автоматически.

## Запуск в разработке

Нужны **два процесса**: backend на `:8000` и Vite dev-сервер на `:5173`.

```powershell
# Терминал 1 — backend (из корня проекта)
.\dev.ps1

# Терминал 2 — frontend
cd frontend
npm run dev
```

Открывайте сайт на **http://localhost:5173** — Vite проксирует `/api` на
backend, cookie сессии работают на том же origin.

`dev.ps1` сам выставляет `APP_BASE_URL=http://localhost:5173`. Если backend
запускаете вручную — задайте эту переменную сами, иначе проверка Origin
отклонит мутации с `403`:

```powershell
$env:APP_BASE_URL = "http://localhost:5173"
cd backend
uv run uvicorn app.main:app --reload --port 8000
```

Проверка, что backend жив:

```powershell
Invoke-RestMethod http://localhost:8000/health
# status version
# ------ -------
# ok     0.1.0
```

## Сборка frontend

```powershell
cd frontend
npm run build    # tsc + vite build → frontend/dist
npm run lint     # oxlint
```

Backend раздаёт `/media/*`, API и собранный SPA из `frontend/dist`, если каталог
сборки существует: настоящие файлы отдаются как есть, а на навигацию браузера
(`Accept: text/html`) — `index.html`. В dev каталога обычно нет — фронтенд
поднимает Vite на `:5173`. Для production настройте reverse proxy с HTTPS и
направляйте в FastAPI **все** пути: API идут по корневым путям (без `/api`),
`/media/*` — фото, остальное — SPA. `npm run preview` предназначен для
локальной проверки сборки, а не для production-хостинга. Готовый вариант —
запуск в Docker по инструкции [DOCKER.md](DOCKER.md).

При работе по HTTPS установите `COOKIE_SECURE=true`. Путь входа отправляет
логин и пароль в теле `POST /auth/login`: текущий пользователь браузера может
увидеть этот запрос в DevTools. Перезагрузка страницы после входа не скрывает
его; HTTPS защищает передачу по сети, но не содержимое DevTools на устройстве
самого пользователя.

## Тесты и проверки

```powershell
cd backend
uv run pytest
uv run ruff check .
```

## Бэкап

```powershell
# из корня проекта: копия data/qa.db + data/media в data/backups/, хранится 14 копий
.\backup.ps1
```

Для ежедневного бэкапа создайте задачу Планировщика Windows: действие
`powershell -ExecutionPolicy Bypass -File <путь>\backup.ps1`. Восстановление:

```powershell
# сначала остановить uvicorn
cd backend
uv run python -m app.cli restore data/backups/qa-backup-<дата>_<время> --yes
```

## Частые проблемы

- **`403` на любое действие** — проверка Origin: backend должен знать адрес
  фронтенда в `APP_BASE_URL` (в dev это `http://localhost:5173`).
- **`401` на API** — нет действующей сессии, войдите на `/login`.
- **Пароль виден в DevTools** — это ожидаемое поведение браузера для запроса
  входа. Не отправляйте пароль по HTTP через сеть; используйте HTTPS вне
  локальной разработки. Скрыть запрос от владельца браузера нельзя.
- **`uv: command not found`** — установите uv (`pip install uv` или
  `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`).
- **Ошибка git «dubious ownership»** —
  `git config --global --add safe.directory D:/repos/qa-test-staff`.
- **Не запускайте `uvicorn --workers 2`** — SQLite и in-memory rate limit
  рассчитаны на один процесс.
- **Пароль не восстанавливается по email** — его сбрасывает админ через
  `/people` (или `POST /users/{id}/password`).
