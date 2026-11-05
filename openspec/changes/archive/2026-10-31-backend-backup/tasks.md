# tasks: backend-backup

- [x] backup.ps1: скрипт бэкапа без интерактивных запросов, завершается с кодом 0
- [x] backup.ps1: тест через планировщик Windows (запуск как задание, код 0)
- [x] бэкап: проверка содержимого копии (база + media)
- [x] журнал аудита: роут с фильтрами по дате и устройству, доступен только
      админу — вынесен в change `audit-log-endpoint`, спека `audit-log`,
      `backend/tests/test_audit.py` (8 кейсов)
- [x] `/health`: проверка БД, ответ `database: "ok"|"error"`, 503 при
      недоступности — `backend/app/api/health.py`,
      `backend/tests/test_health.py` (падение БД ломает движок на уровне
      `before_cursor_execute`)
- [x] структурные логи: подтверждение покрытия требований (запросы,
      исключения, секреты) — сверка сценариев `structured-logging` с тестами
      `backend/tests/test_logging.py`, таблица в `design.md`
