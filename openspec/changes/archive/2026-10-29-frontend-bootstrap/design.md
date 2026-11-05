# Design

## Каркас

Сборка руками `npm create vite@latest frontend -- --template react-ts`
(Vite 8, React 19, TS) + зависимости: `@mantine/core @mantine/hooks
@mantine/notifications @mantine/form @tanstack/react-query
react-router-dom`. В `index.html` — `<html lang="ru">`. `tsconfig`
по шаблону Vite; scripts: `dev`, `build` (`tsc -b && vite build`),
`preview`. `vite.config.ts`: `server.proxy['/api'] → http://localhost:8000`
(`changeOrigin: false`, cookie на том же origin — сессии работают в dev).

Структура — как в AGENTS.md:

```
frontend/src/
  api/client.ts      fetch-обёртка: JSON, credentials, конверт ошибок
  api/auth.ts        login/logout/me
  api/reports.ts     dashboard/stats
  lib/format.ts      formatDate → ДД.ММ.ГГГГ
  lib/QueryProvider  TanStack Query статусер (queryClient)
  pages/LoginPage.tsx, DashboardPage.tsx, PlaceholderPage.tsx
  components/AppShell.tsx   навигация + logout
  routes.tsx         дерево маршрутов + ProtectedRoute
  main.tsx, App.tsx
```

## Сессия и защита маршрутов

`useMeQuery` оборачивает `GET /auth/me` (TanStack Query, `retry: false`).
`ProtectedRoute`: пока `me` в статусе pending — полноэкранный loader;
ошибка 401 → `<Navigate to="/login" state={{ from: location }} />`.
После успешного логина возврат на `state.from ?? /dashboard`.
401 в любом запросе внутри client-обёртки — тот же redirect
(событие через callback в модуль `api/client.ts`, слушает
`QueryProvider`). Данные `me` — шапка: ФИО и роль, кнопка «Выйти».

## Дашборд

`useQuery` `dashboard/stats`; `staleTime: 15s`, polling не нужен тут.
Счётчики — грид из 7 стат-карточек, подписи на русском
(`total_active` → «Активно», `with_owners` → «У владельцев», `checked_out`
→ «Выдано», `in_repair` → «В ремонте», `lost` → «Утеряно», `archived`
→ «В архиве», `overdue` → «Просрочено»). «Просроченные» — таблица
топ-5 из `top_overdue` (инв. № → `inventory_no`, модель, держатель →
`holder.full_name`, дни → `days_overdue`); пусто → «Нет просроченных
возвратов».

## Ошибки и уведомления

`@mantine/notifications` в тёмной теме. `api/client.ts` бросает
`ApiError(code, message)`. Любое потребительское место (логин, дашборд)
ловит `ApiError`/`unknown` и показывает `showNotification({ color: "red",
message: ... })`; в `client.ts` 401, кроме `/auth/me`, включает redirect
на `/login`. Ничего об сетевой ошибке не JSON-конверт: «Ошибка сети».

## Стартовая верификация

Завершение: `npm run build` проходит на чистой папке; `npm run dev` +
запущенный backend в HEAD → вручную проверяемы сценарии входа из спеки
(вход/редирект/выход — визуально пользователем). Unit-тесты на фронт
в этом change нет: partnership-Vitest отложен (см. proposal), риск
смягчается тем, что логика фронтенда в этом change — тонкая
обёртка над API.
