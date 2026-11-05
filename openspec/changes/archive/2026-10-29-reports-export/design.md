# Design

## Данные

Все чтения строятся на одном `device_state_query()` из `services/device_state`:
он даёт `holder_id` (coalesce активной выдачи на `owner_id`), `checkout_id`,
`expected_return_at` и булев `overdue` по инварианту 6. Отчёты и Excel не имеют
своих формул дат — это единственное место, где объявляется просрочка.

Категории дашборда считаются одним проходом по строкам state-запроса
(модель + статус + флаг архива + флаг выдачи + флаг просрочки):

| Категория | Условие |
|---|---|
| total_active | `archived_at IS NULL` |
| with_owners | `archived_at IS NULL` AND `checkout_id IS NULL` |
| checked_out | `archived_at IS NULL` AND `checkout_id IS NOT NULL` |
| in_repair | `status = 'repair'` AND `archived_at IS NULL` |
| lost | `status = 'lost'` AND `archived_at IS NULL` |
| archived | `archived_at IS NOT NULL` |
| overdue | `overdue = 1` (по всему парку, без условия архива — активная выдача в архиве невозможна) |

## Слои

- `services/reports.py`: `dashboard_stats`, `holders_report`,
  `overdue_report`, `export_workbook`. Чистая сборка строк; Excel-книга
  строится в открытую через openpyxl и возвращается как `Workbook`.
- `api/reports.py`: тонкие роуты, `StreamingResponse`/byte-обёртка для xlsx,
  `Content-Disposition: attachment; filename="qa-export-ГГГГММДД.xlsx"`.

## Формат Excel

- Лист 1 «Все устройства»: колонки D1 — инв. №, модель, ОС, владелец, держатель,
  статус, дата выдачи, ожидаемый возврат, просрочка. Фильтры — те же параметры,
  что `GET /devices` (переиспользуем `DeviceListParams` и условия
  `search_condition`/`scope_conditions`/`archived_conditions` из `devices`, без
  пагинации и сортировки — полнота важнее порядка).
- Лист 2 «Просроченные»: инв. №, модель, владелец, держатель, дата выдачи,
  ожидаемый возврат, дней просрочки.
- Лист 3 «История выдач»: за `from_date`/`to_date` (ISO-даты в запросе,
  по умолчанию 1 января текущего года по сегодня): инв. №, модель,
  держатель, дата выдачи, дата возврата, closed_reason, комментарий закрытия.
- Данные о людях — один `users_by_id`-подход: словарь `id → full_name`,
  чтобы N устройств не делали N запросов по пользователю.

## Проверки

- Просрочка: состав листа 2 == отчёт `/reports/overdue` == `GET
  /devices?archived=all&overdue=true` — тест сравнивает множества id.
- Top-5: при 7 просроченных устройствах возвращается 5, отсортированных по
  длительности.
- Фильтр экспорта: устройство «в ремонте» остаётся единственным на листе 1
  при `status=repair`.
- Даты: `from_date > to_date` → 422 VALIDATION_ERROR (Pydantic `model_validator`).
- Доступ: без сессии 401; обычный `user` получает файл 200.
- Читаемость xlsx: тест открывает скачанные байты через `load_workbook` и
  сверяет заголовки и одну строку данных.
