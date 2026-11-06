# Tasks

## 1. Бэкенд: дашборд только для admin

- [x] 1.1 Добавить в `backend/tests/test_reports.py` проверки доступа:
      user получает 403 на `GET /dashboard/stats` и `GET /dashboard/charts`,
      admin (`register_user(..., role="admin")`) — 200; существующий
      `test_reports_available_to_plain_user` оставить 200 только для
      `/reports/*`. Проверка: `uv run pytest tests/test_reports.py` —
      новые тесты падают (403 ещё нет).
- [x] 1.2 Перевести `read_dashboard` и `read_dashboard_charts` в
      `backend/app/api/reports.py` на `Depends(require_admin)`.
      Проверка: `uv run pytest tests/test_reports.py` — все тесты зелёные,
      включая 401 без сессии из `test_reports_require_authentication`.
- [x] 1.3 Прогнать полный набор проверок бэкенда.
      Проверка: `uv run pytest` и `uv run ruff check .` — без ошибок.

## 2. Фронтенд: скрытие и редирект

- [x] 2.1 Добавить гард в `ProtectedLayout` (`frontend/src/routes.tsx`):
      после загрузки `me()` переход на `/dashboard` с ролью user
      редиректит на `/devices` до рендера `DashboardPage`.
      Проверка: `npm run build` (tsc) проходит; при открытии `/dashboard`
      под обычным пользователем адрес меняется на `/devices`, запросы
      `dashboard-stats`/`dashboard-charts` не уходят.
- [x] 2.2 Скрыть пункт «Дашборд» от роли user: флаг `adminOnly` в
      `NAV_ITEMS` и фильтр по `user.role` в `AppShellFrame`
      (`frontend/src/components/AppShell.tsx`).
      Проверка: `npm run lint` и `npm run build` проходят; под обычным
      пользователем в боковом меню нет «Дашборд», под admin — есть.

## 3. Интеграционная проверка

- [x] 3.1 Прогнать все проверки разом.
      Проверка: `uv run pytest`, `uv run ruff check .`, `npm run build`,
      `npm run lint`, `openspec validate --all --strict` — без ошибок.
- [x] 3.2 Смоук-проверка в dev-режиме (`.\dev.ps1`): login как user —
      нет пункта «Дашборд», прямой `/dashboard` уводит на `/devices`,
      `GET /dashboard/stats` отвечает 403; login как admin — дашборд
      со счётчиками и графиками работает.
      Проверка: перечисленные наблюдения на локальном сервере.

## Workflow follow-up

- Локальный коммит Conventional Commits после завершения (например,
  `feat(restrict dashboard to admin)`).
- `openspec validate --all --strict` перед архивацией, затем
  `openspec archive admin-only-dashboard`.
