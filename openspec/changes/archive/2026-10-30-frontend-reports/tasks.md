## 1. API

- [x] 1.1 `api/reports.ts`: типы отчётов, `fetchHoldersReport`,
      `fetchOverdueReport`, `exportUrl`.

## 2. Страница

- [x] 2.1 `pages/reports/ReportsPage.tsx`: вкладки и обе таблицы, пустые состояния.
- [x] 2.2 Блок выгрузки: период, «только просроченные», скачивание.
- [x] 2.3 Проверка периода и ссылки на карточки устройств.
- [x] 2.4 Маршрут `/reports` вместо заглушки, обновление README.

## 3. Проверка

- [x] 3.1 `npm run build`, `npm run lint`.
- [x] 3.2 Сквозная проверка отчётов и скачивания файла на изолированном бэкенде.
- [x] 3.3 `openspec validate --all --strict`.
