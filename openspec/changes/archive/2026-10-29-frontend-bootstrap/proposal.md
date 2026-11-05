# Proposal

## Why

Backend полностью покрывает спеки (11 capabilities, включая уведомления,
отчёты и Excel), но сайт для команды не существует: фронтенда нет. Это
первый каркасный шаг frontend-этапа по PLAN.md — как `bootstrap-backend`
(B0–B2) был для бэка. Без него остальные экраны некуда складывать, а
команда не может пользоваться системой вовсе.

## What Changes

- **Каркас SPA** в `frontend/`: Vite 8, React, TypeScript, React Router,
  TanStack Query, Mantine (core + hooks). Dev-сервер на :5173 проксирует
  `/api` на :8000.
- **API-клиент** (`src/api/`): `fetch` с `credentials: "include"`, JSON-запросы,
  единая обработка конверта ошибок `{code, message}` — русское сообщение
  показывается тостом (`@mantine/notifications`).
- **Авторизация**: страница `/login`, сессия через `GET /auth/me`
  (TanStack Query), защищённая разметка маршрутов с редиректом на `/login`,
  выход через `POST /auth/logout` и сброс `me`.
- **Оболочка (shell)**: `AppShell` с навигацией — Дашборд, Устройства, Люди,
  Отчёты; разделы, которых ещё нет, показывают экран «в разработке».
  Активный пункт подсвечен по URL.
- **Дашборд**: счётчики из `GET /dashboard/stats` (всего активных, у
  владельцев, выдано, в ремонте, утеряно, в архиве, просрочено) и блок
  «Просроченные» — топ-5 давних просрочек с инв. № , моделью, держателем
  и днями просрочки.
- **Тёмная тема** по умолчанию (M5), интерфейс полностью на русском,
  даты в формате `ДД.ММ.ГГГГ`.

### Assumptions

- SPA-маршруты: `/login`, `/dashboard`, `/devices`, `/people`, `/reports` —
  на текущих спеках UI-URL не определены жёстко, это дельта-предложение
  фиксирует их впервые.
- Токен не хранится нигде: аутентификация только httpOnly-cookie как на бэке.
- Статическая раздача `frontend/dist` через FastAPI (`/` и SPA-fallback) —
  отдельный change после сборки всех экранов, пока dev-only.
- Что НЕ входит: устройства/люди/отчёты/уведомления как рабочие экраны
  (только заглушки), тестирование фронтенда (Vitest/Playwright — отложено),
  фото и Excel-кнопка.

## Capabilities

### New Capabilities

- `frontend-shell`: маршруты SPA, поведение редиректа на вход, оболочка
  с навигацией, дашборд и правила ошибок/языка/дат интерфейса.

### Modified Capabilities

Нет — backend API не меняется.

## Impact

- Новое: `frontend/` (package.json, vite.config.ts, tsconfig, index.html,
  src/{api, components, pages, lib}, routes.tsx), обновление `README.md`
  (раздел frontend: npm install, npm run dev), `.gitignore` корневой
  (`node_modules/`, `dist/`).
- Backend не затрагивается; существующие 11 спек не меняются, добавляется
  дельта новой capability `frontend-shell`.
