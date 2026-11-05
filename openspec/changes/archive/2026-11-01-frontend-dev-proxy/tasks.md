# Tasks

## 1. API-слой

- [x] 1.1 `frontend/src/api/client.ts`: `API_BASE` (`import.meta.env.DEV ?
      '/api' : ''`) и хелпер `apiUrl(path)`; `apiFetch` строит URL через
      `apiUrl`. Проверка: `npm run build`.
- [x] 1.2 `frontend/src/api/reports.ts`: `exportUrl()` возвращает URL через
      `apiUrl`.

## 2. Dev-прокси

- [x] 2.1 `frontend/vite.config.ts`: запись `'/media' → http://localhost:8000`
      без rewrite (фотоустройств).

## 3. Проверка этапа

- [x] 3.1 `npm run build` и `npm run lint` зелёные.
- [x] 3.2 Сквозная проверка через :5173 с запущенным backend: `POST
      /api/auth/login` (admin) → 200 и cookie, `GET /api/auth/me` → 200,
      `GET /api/devices` → 200; запрос `/auth/login` без префикса больше не
      используется клиентом.
- [x] 3.3 Локальный коммит этапа: `fix(frontend): call backend through /api
      prefix in dev`.

## Workflow follow-up

- `openspec archive frontend-dev-proxy` после принятия ревью.
- Локальный коммит архива: `chore(openspec): archive frontend-dev-proxy`.
