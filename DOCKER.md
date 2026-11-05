# Запуск в Docker

Один контейнер на всё: FastAPI отдаёт API, `/media` и собранный SPA
(`frontend/dist`) с одного порта. Данные — база, фото, бэкапи — лежат на
хосте в `./data` и переживают пересоздание контейнера.

## Требования

- Docker Desktop (или Docker Engine) с Compose v2: `docker compose version`.
- Доступ в интернет при сборке (пакеты npm и Python качаются в образ).
- Сборка идёт из корня репозитория — контекст сборки задан в
  `docker-compose.yml`.

## Первый запуск

```powershell
# 1. Если каталог data/ уже содержит базу разработки — уберите её в сторону.
#    Иначе контейнер подхватит старую базу, и пароль ниже не сработает.
Rename-Item data data-dev-backup

# 2. Сборка образа и запуск
docker compose build
docker compose up -d
```

Первый старт прогоняет миграции и создаёт администратора из переменных
`ADMIN_*` — в логе видно `admin_created`:

```powershell
docker compose logs app | Select-String admin
```

## Учётная запись администратора

| | |
|---|---|
| Адрес | http://localhost:8000 |
| Логин | `admin` |
| Пароль | `Admin12345` |

Заданы в `docker-compose.yml` (`ADMIN_USERNAME`, `ADMIN_PASSWORD`,
`ADMIN_FULL_NAME`). В отсутствие `ADMIN_PASSWORD` администратор не создаётся.

Пароль создаётся **один раз** при первом старте и дальше не меняется:
`docker compose up` с другим `ADMIN_PASSWORD` существующий аккаунт не
перезапишет. Смените его после первого входа: шапка → «Мои» → смена пароля.

Если база не пустая (в ней уже есть логин `admin` с другим паролем),
создайте нового администратора:

```powershell
docker compose exec app python -m app.cli create-admin --username admin2 `
  --full-name "Новый Администратор" --password "НовыйПароль1"
```

## Проверка

```powershell
docker compose ps            # STATUS: Up (healthy)
docker compose logs -f app   # JSON-логи: admin_created / admin_unchanged, запросы
curl.exe http://127.0.0.1:8000/health
# {"status":"ok","version":"0.1.0","database":"ok"}
```

Сайт открывается в браузере: **http://localhost:8000**.

Два момента, из-за которых обычно «не работает»:

- **Адрес должен совпадать с `APP_BASE_URL`** (по умолчанию
  `http://localhost:8000`). Открыли сайт как `http://127.0.0.1:8000` — вход
  пройдёт, а любое действие отклонится с `403 Недопустимый источник запроса`.
  Приведите `APP_BASE_URL` к реальному адресу и перезапустите контейнер.
- **`curl` без `Accept: text/html` на неизвестный путь получит JSON-404** —
  SPA отдаётся браузерной навигации. Проверка:
  `curl.exe -H "Accept: text/html" http://localhost:8000/`.

## Переменные окружения

| Переменная | По умолчанию | Назначение |
|---|---|---|
| `ADMIN_USERNAME` | `admin` | Логин создаваемого администратора |
| `ADMIN_PASSWORD` | `Admin12345` (в compose) | Пароль; без него администратор не создаётся |
| `ADMIN_FULL_NAME` | `Администратор` | ФИО администратора |
| `APP_BASE_URL` | `http://localhost:8000` | Адрес сайта: по нему сверяется Origin мутаций |
| `APP_ENV` | `production` | В `production` мутации без Origin отклоняются с `403` |
| `COOKIE_SECURE` | `false` | `true` при работе по HTTPS |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `TZ` | `Europe/Moscow` (в compose) | Пояс контейнера: по нему считаются просрочка и границы отчётов |
| `PORT` / `HOST` | `8000` / `0.0.0.0` | Порт и интерфейс uvicorn |
| `SESSION_TTL_DAYS` | `7` | Срок жизни сессии от последней активности |

`DATABASE_URL` и `DATA_DIR` задавать не нужно: база, фото и бэкапи лежат в
`/app/data` (это `./data` на хосте).

Проверить пояс контейнера: `docker compose exec app date`.

## Данные и бэкапы

`./data` на хосте — это `qa.db`, `media/`, `backups/`. Каталог нужно
бэкапить целиком, как и в обычной установке.

```powershell
# копия: data/backups/qa-backup-<дата>_<время>/, хранится 14 последних
docker compose exec app python -m app.cli backup

# восстановление: сначала остановить контейнер
docker compose stop
docker compose run --rm app python -m app.cli restore /app/data/backups/qa-backup-<дата>_<время> --yes
docker compose start
```

## Обновление и остановка

```powershell
docker compose build && docker compose up -d   # данные в ./data не трогаются
docker compose down                            # остановить и убрать контейнер
```

## HTTPS и другой адрес

За reverse proxy (Caddy, nginx, Traefik):

1. `APP_BASE_URL=https://qa.example.internal` — иначе все действия падают
   с `403`.
2. `COOKIE_SECURE=true`.
3. Проксируйте **все** пути на контейнер: API идут корневыми путями (без
   `/api`), `/media/*` — фото, остальное — SPA. Отдельный статический сервер
   не нужен.

## Частые проблемы

- **`403 Недопустимый источник запроса` на любое действие** — адрес в
  браузере не совпадает с `APP_BASE_URL` (типично: `127.0.0.1` вместо
  `localhost`). Или из скрипта не передан заголовок
  `-H "Origin: http://localhost:8000"`: в `production` Origin обязателен.
- **Пароль `Admin12345` не подходит** — контейнер подключил существующую
  базу из `./data`, где уже есть администратор с другим паролем. См. раздел
  «Учётная запись администратора».
- **`401` на API** — нет действующей сессии, войдите на `/login`.
- **`docker compose ps` → `unhealthy`** — смотрите `docker compose logs app`:
  обычно упали миграции или недоступна БД.
- **`permission denied` на `./data`** — контейнер работает от пользователя
  `qa` (uid 1000): на Linux выполните `chown -R 1000:1000 data`.
- **Просрочка «не наступает» или наступает рано** — проверьте `TZ`
  контейнера: дата «сегодня» берётся из локального времени процесса.

## Ограничения

- Ровно один процесс uvicorn в контейнере: масштабирование
  (`--scale app=2`) не применяется — SQLite и rate limit попыток входа
  рассчитаны на один процесс.
- Время хранится в локальном поясе контейнера (naive datetime); при смене
  `TZ` существующие данные пересчитывать не нужно, но границы отчётов
  сместятся.
- Пароли от Google/Apple-аккаунтов телефонов в систему не вносятся — только
  пометка, какие аккаунты настроены.
