# Tasks

## 1. Дашборд и отчёты (сервис + API)

- [x] 1.1 Тест `tests/test_reports.py::test_dashboard_counts_categories`:
      разброс фикстур (владелец–без выдачи, выданная, ремонт, lost, архив,
      просрочка) → точно эти счётчики. Проверка: тест падает (нет
      `services/reports.py`).
- [x] 1.2 Тест `test_dashboard_top_overdue_ordered`: 7 просрочек разной длины →
      возвращается 5 строк по убыванию дней, каждая с inventory_no, моделью,
      держателем и днями. Проверка: падает.
- [x] 1.3 Тест `test_holders_report_lists_active`: активные и архивные
      устройства → архивные не попадают, держатель у выданного, `сowner` у
      невызданного. Проверка: падает.
- [x] 1.4 Реализовать `app/services/reports.py` (`dashboard_stats`,
      `holders_report`, `overdue_report`) на одном `device_state_query()`;
      схемы в `app/schemas/reports.py`; роутер `app/api/reports.py`
      (`GET /dashboard/stats`, `GET /reports/holders`, `GET /reports/overdue`),
      подключить в `app/main.py`. Проверка: `pytest tests/test_reports.py`
      зелёный.
- [x] 1.5 Тесты доступа: без сессии → 401 на все три роута; обычный `user`
      получает 200. Проверка: зелёный.

## 2. Excel-выгрузка

- [x] 2.1 Тест `tests/test_export.py::test_export_three_sheets`: скачанный
      `.xlsx` открывается `load_workbook`, имена листов «Все устройства»,
      «Просроченные», «История выдач»; заголовок первой строки листа 1
      совпадает со списком колонок. Проверка: падает.
- [x] 2.2 Тест `test_export_respects_filters`: только устройство в статусе
      `repair` попадает на лист 1 при `status=repair`; лист 2 пуст при
      отсутствии просрочек. Проверка: падает.
- [x] 2.3 Тест `test_export_history_period`: выдача закрыта в июне, вторая
      активна → лист 3 содержит закрытую при периоде май–июль, без активной;
      `from_date > to_date` → 422. Проверка: падает.
- [x] 2.4 Реализовать в `services/reports.py` `export_workbook` (openpyxl,
      три листа, колоны D1/D2, даты `ДД.ММ.ГГГГ`, `users_by_id`-кэш) и
      `apixlsx`-роут `GET /reports/export.xlsx` с теми же query-параметрами
      фильтров, что `/devices`. Проверка: `pytest tests/test_export.py`
      зелёный.
- [x] 2.5 Тест совпадения просрочек: множество id с `GET /devices?archived=all&overdue=true`
      == множество из листа «Просроченные» == отчёт `GET /reports/overdue`.
      Проверка: зелёный (инвариант 6 не сломан).

## 3. Контракт и интеграционная проверка

- [x] 3.1 `uv run python -m app.export_openapi`; `pytest tests/test_openapi.py`;
      README дополнен разделом отчётов. Проверка: команды зелёные.
- [x] 3.2 Полный прогон: `pytest -q`, `ruff check .`, `openspec validate
      --all --strict` — всё зелёное.

## 4. Ревью Uncle Bob

- [x] 4.1Coverage → LCOV, затем `crapper --use-existing-coverage`, `dryer app`,
      `mutator --use-existing-coverage` на backend. Проверка: нет SURVIVED
      в новых модулях, CRAP ≤ норм по new функциям; при выживших — новые
      тесты-убийцы и повтор.
