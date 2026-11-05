# Tasks

## 1. Backend: агрегаты

- [x] 1.1 `backend/app/schemas/reports.py`: схемы `TurnoverPoint`,
      `OverdueBucket`, `DashboardCharts`.
- [x] 1.2 `backend/app/services/reports.py`: `dashboard_charts(db)` —
      выдачи/возвраты по месяцам за последние 12 месяцев (включая текущий,
      локальные месяцы, месяцы без событий с нулями) и корзины просрочки
      1–7 / 8–14 / 15–30 / 31+ через `days_overdue` и
      `device_state_query`.
- [x] 1.3 `backend/app/api/reports.py`: `GET /dashboard/charts` с той же
      зависимостью сессии, что у `/dashboard/stats`.
- [x] 1.4 Тесты в `backend/tests/`: наполнение за 12 месяцев и нули между
      месяцами; попадание возврата в месяц возврата; корзины (включая 31+ и
      пустой случай — четыре нуля); 401 без сессии.

## 2. Frontend: графики

- [x] 2.1 Зависимость `@mantine/charts` (версия синхронна с `@mantine/core`).
- [x] 2.2 `frontend/src/api/reports.ts`: типы и `fetchDashboardCharts` →
      `GET /dashboard/charts`.
- [x] 2.3 `DashboardPage.tsx`: блок из трёх графиков — BarChart динамики
      (мес. подписи по-русски), DonutChart состояния парка из счётчиков,
      BarChart корзин просрочки; локальный Alert при ошибке графиков; пустое
      состояние у динамики; мобильная раскладка.
- [x] 2.4 `npm run build` и `npm run lint` зелёные.

## 3. Проверка этапа

- [x] 3.1 `uv run pytest` и `uv run ruff check .` зелёные.
- [x] 3.2 `openspec validate --all --strict` зелёный.
- [x] 3.3 Сквозная проверка: на дашборде три графика, данные совпадают с
      отчётом «Просроченные» и счётчиками.
- [x] 3.4 Локальные коммиты: `feat(backend): dashboard charts aggregation`,
      `feat(frontend): dashboard charts`.

## Workflow follow-up

- `openspec archive dashboard-charts` после принятия ревью.
