# Tasks

## 1. Каркас

- [x] 1.1 Проверить, что общественного change нет: `openspec list`,
      backend зелёный — пропускной шаг, изменений нет.
- [x] 1.2 Создать `frontend/` через `npm create vite@latest frontend --
      --template react-ts`; поставить `@mantine/core @mantine/hooks
      @mantine/notifications @mantine/form @tanstack/react-query
      react-router-dom`. Добавить в корневой `.gitignore`:
      `frontend/node_modules/`, `frontend/dist/`. Проверка:
      `npm run build` зелёный на каркасе.
- [x] 1.3 `vite.config.ts`: прокси `/api` → `http://localhost:8000`;
      `index.html` — `<html lang="ru">` и тёмная палитра по умолчанию;
      шрифт-провайдер не добавляем (системный). Проверка: `npm run dev`
      открывает пустую страницу в браузере.

## 2. API-клиент и авторизация

- [x] 2.1 `src/api/client.ts`: `apiFetch` — JSON, `credentials: "include"`,
      конверт ошибок → `ApiError(code, message)`, сетевая ошибка → общее
      «Ошибка сети. Повторите попытку»; коллбек 401 → redirect `/login`
      (кроме `/auth/login`, `/auth/me`, `/auth/logout`).
      `src/lib/format.ts`: `formatDate(iso)` → `ДД.ММ.ГГГГ`.
      Проверка: `npm run build` зелёный.
- [x] 2.2 `src/api/auth.ts`: `login`, `logout`, `me`; `src/api/reports.ts`:
      `fetchStats`. Страница `/login` (Mantine-форма, показ `message` при
      `UNAUTHORIZED`). Проверка: `npm run build` зелёный.
- [x] 2.3 `main.tsx`: MantineProvider с тёмной темой (defaultColorScheme =
      "dark"), Notifications, QueryClientProvider (staleTime 15s,
      retry false); `routes.tsx` с `ProtectedRoute` (redirect с сохранением
      `state.from`). Проверка: `npm run build` зелёный.

## 3. Оболочка, дашборд, заглушки

- [x] 3.1 `components/AppShell.tsx`: шапка (название «QA Тестовые
      устройства», ФИО из `me`, «Выйти»), боковая навигация с четырьмя
      пунктами маршрутов; активный подсвечен по `useLocation`.
      `dashboard/stats` на `/dashboard`: 7 стат-карточек по подписям
      дизайна + таблица «Просроченные» (5 строк или «Нет просроченных
      возвратов»); заглушки `/devices`, `/people`, `/reports`. Ошибки
      API → `showNotification`. Проверка: `npm run build` зелёный.
- [x] 3.2 Сквозная проверка: backend с тест-админом (`app.cli.py
      create-admin`), `npm run dev` — вручную: редирект неавторизованного
      на `/login`, вход, счётчики, «Выйти». Проверка: сценарии спеки
      выполняются.
- [x] 3.3 README: раздел «Frontend» — `npm install`, `npm run dev` (:5173
      проксирует `/api`), `npm run build`; скриншоты не нужны.
      Проверка: раздел читается, команды совпадают с реальностью.

## 4.воркафлоу-завершение

- [x] 4.1 `openspec validate --all --strict`; ruff не затрагивается
      (нет backend-изменений). Проверка: зелёное.
- [x] 4.2 Локальный коммит этапа: `feat(frontend): bootstrap Vite app with
      auth and dashboard (B8/todo)`.
