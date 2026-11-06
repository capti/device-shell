# AGENTS.md

Краткий контекст для ИИ-агентов и разработчиков. Источник требований — OpenSpec
(`openspec/specs/`), `PLAN.md` — справочник и история решений.
Если меняешь поведение системы — сначала change в OpenSpec, потом код.

## OpenSpec

- Спеки: `openspec/specs/<capability>/spec.md` — текущая правда.
- Активные изменения: `openspec/changes/<id>/`.
- Завершённые: `openspec/changes/archive/`.
- Контекст проекта и инварианты: `openspec/config.yaml`.

Workflow:

1. `openspec new change "<id>"` или скилл `openspec-propose`.
2. Заполнить `proposal.md`, `specs/`, `design.md`, `tasks.md`.
3. Реализовать строго по `tasks.md` (скилл `openspec-apply-change`).
4. `openspec validate --all --strict`.
5. `openspec archive <id>`.

Правила:

- Код без утверждённого change не пишем.
- Изменение поведения без изменения спек запрещено.
- `openspec/specs/` руками не правим — только через change и archive.
- Полезные команды: `openspec list --specs`, `openspec show <capability> --type spec`,
  `openspec status --change <id>`, `openspec instructions <artifact> --change <id>`.

## Что это

Сайт для учёта тестовых смартфонов: **за кем закреплён**
(owner) и **у кого сейчас на руках** (holder). Плюс история выдач, отчёты о
состоянии, фото, просрочки, Excel-экспорт и уведомления.

## Стек

- `backend/` — Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2,
  SQLite (WAL). Зависимости через `uv`.
- `frontend/` — Vite 8, React, TypeScript, Mantine, TanStack Query,
  React Router. Пакеты через `npm`.
- Auth: серверные сессии в БД + httpOnly cookie (не JWT).
- Прод: FastAPI раздаёт `frontend/dist` и `/media/*`. Локальный хостинг,
  один процесс, один порт.

## Домен — главное

- `admin` / `user` — **роль доступа** (`users.role`).
- `owner` — владелец устройства (`devices.owner_id`, NOT NULL, всегда один,
  сменяемый). Не роль.
- `holder` — у кого телефон физически сейчас. Определяется активной записью
  `checkouts` (`returned_at IS NULL`); если её нет — держатель = владелец.
- Состояния «на складе» нет: у каждого телефона есть владелец.

## Жёсткие инварианты

Не менять без change в OpenSpec и тестов.

1. Один владелец на устройство, обязателен.
2. Максимум одна активная выдача на устройство (partial unique index).
3. Нельзя выдать самому себе (`holder != owner`).
4. Передача владения текущему holder'у автозакрывает выдачу
   (`closed_reason = ownership_transferred`).
5. Архивировать можно только без активной выдачи → иначе `409 ACTIVE_CHECKOUT`.
   Правило действует и для админа.
6. Просрочка = активная выдача AND `holder != owner` AND
   `expected_return_at < today`. Считается **только на бэке**, одной функцией
   для списка, дашборда, фильтров и Excel.
7. Физического удаления нет: устройства — архив, пользователи — деактивация.
8. Деактивация пользователя отправляет все его устройства в архив. Если у него
   на руках чужие телефоны или у его устройств есть активные выдачи — `409`,
   сначала возврат/передача. Восстановление такого устройства требует нового
   владельца.
9. Каждая мутация пишет `device_events` в той же транзакции.

## Права (кратко)

`user` управляет только своими устройствами и тем, что держит.
`admin` — всё, плюс управление пользователями.
Держатель может сам вернуть телефон и оставить отчёт о состоянии.

## Команды

```powershell
# backend
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
uv run pytest

# frontend
cd frontend
npm install
npm run dev        # :5173, проксирует /api на :8000
npm run build

# всё сразу (Windows): backend + Vite в одном окне, оба с hot reload
.\dev.ps1
```

## Структура

```
backend/app/{main.py, config.py, db.py, models/, schemas/, api/, services/}
backend/alembic/
backend/tests/
frontend/src/{api/, components/, pages/, lib/, routes.tsx}
openspec/{config.yaml, specs/, changes/}
data/{qa.db, media/}
```

## Правила для ИИ

- Любая правка кода пишется вместе со скиллом `ub-mode`
  (`.skills/ub-mode/SKILL.md`): сначала *Make it Work*, потом *Make it Right*,
  затем *Practice*.
- `ub-mode` не отменяет OpenSpec и правила этого файла. При конфликте
  действуют OpenSpec и `AGENTS.md`: например, push — только по отдельной
  просьбе, правило «Push to the main line» из скилла автоматически не
  применяется.
- Ревью изменения включает тесты, линтер и прогон `crapper`, `dryer` и
  `mutator` (см. «Ревью»).

## Ревью

Помимо `pytest`, `ruff` и `openspec validate --all --strict`, ревью проходит
через три инструмента Uncle Bob:

| Инструмент | Что проверяет |
|---|---|
| `crapper` | цикломатическую сложность и CRAP-оценку функций |
| `dryer` | структурные дубли кода |
| `mutator` | выживаемость тестов: убивают ли они мутации |

Инструменты ставятся **вне проекта**, в `D:\repos`: клоны `crapper`, `dryer`,
`mutator` и общий venv `D:\repos\.qa-tools-venv`. В проект они не попадают,
их артефакты (`.metrics/`, `target/`) не коммитятся.

```powershell
$py = "D:\repos\.qa-tools-venv\Scripts\python.exe"
$env:PYTHONIOENCODING = "utf-8"   # справка crapper содержит «CC²», cp1251 падает
cd backend

# LCOV собираем сами: на Windows инструменты ищут .venv/bin/python
uv run --with coverage python -m coverage run --source=app -m pytest -q
uv run --with coverage python -m coverage lcov -o target/coverage/python/lcov.info

& $py -m crapper --use-existing-coverage
& $py -m dryer app
$test = "`"$PWD\.venv\Scripts\python.exe`" -m pytest -x -q"
& $py -m mutator --use-existing-coverage --test-command $test app
```

Как читать результаты:

- `SURVIVED` у `mutator` — реальный пробел в тестах: мутация не ломает ни один
  тест.
- `UNCOVERED` на продолжениях многострочных выражений — ложное срабатывание
  LCOV: покрытие отмечает только первую строку выражения.
- `crapper` с высоким CRAP при низкой сложности указывает на пробел покрытия,
  а не на необходимость рефакторинга.

## Git

- Репозиторий локальный, ветка `main`. Пушить только по отдельной просьбе.
- После каждого завершённого этапа (change, блока задач, крупного шага) —
  локальный коммит. Не оставлять готовую работу незакоммиченной.
- Сообщение — Conventional Commits на английском, тело можно на русском:
  `feat(backend): bootstrap backend B0-B2`.
- Перед коммитом: `openspec validate --all --strict` при изменении спек,
  `uv run pytest` и `uv run ruff check .` — при изменении backend.
- В коммит не попадают `data/`, `.env`, `.venv/`, `*.db` — они в `.gitignore`.

## Конвенции

- UI на русском, код и идентификаторы — на английском.
- Бизнес-логика только в `services/`; роуты тонкие, БД из роутов не трогать.
- Схема БД меняется только через Alembic-миграцию.
- Даты в API — ISO 8601, в UI — `ДД.ММ.ГГГГ`.
- Ошибки API: JSON `{code, message}`, `message` на русском.
- Новый инвариант — новый тест в `backend/tests/`.

## Подводные камни

- Partial unique index в SQLite задаётся через `sqlite_where`, иначе
  уникальность активной выдачи не сработает.
- `overdue` нельзя считать на фронте или в шаблоне.
- Фото лежат в `data/media/`, бэкапить вместе с `qa.db`.
- При `409` фронт показывает понятное сообщение, а не «ошибка сервера».

## Чего не делать

- Не добавлять поля и статусы, ломающие инварианты выше.
- Не хранить пароли от Google/Apple-аккаунтов телефонов — только пометку,
  какие аккаунты настроены.
- Не делать саморегистрацию и email-восстановление пароля.
- Не удалять записи истории и аудита.
