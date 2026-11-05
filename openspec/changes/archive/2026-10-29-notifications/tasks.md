# Tasks

## 1. Триггеры по устройствам

- [x] 1.1 Написать падающие тесты `backend/tests/test_notifications_events.py`:
      смена владельца не-админом уведомляет каждого активного admin, админом —
      никого; выдача уведомляет владельца; возврат уведомляет владельца;
      инициатор не получает уведомление о собственном действии. Проверка:
      `uv run pytest tests/test_notifications_events.py -q` падает (модуля
      ещё нет).
- [x] 1.2 Создать `backend/app/services/notifications.py` (типы событий,
      `notify`/`notify_admins`/`notify_owner`, активные админы, запись без
      коммита) и вызвать его из `services/ownership.change_owner`,
      `services/checkouts.checkout_device`, `services/checkouts.return_device`
      перед `db.commit()`. Проверка: `uv run pytest
      tests/test_notifications_events.py -q` зелёный.
- [x] 1.3 Дописать тесты в `test_notifications_events.py`: архивация и
      восстановление не-админом → админам; статус `lost` → админам; отчёт с
      `requires_repair` → админам; любой новый отчёт о состоянии → владельцу
      (требование `condition-reports`). Проверка: `uv run pytest
      tests/test_notifications_events.py -q` падает на новых тестах.
- [x] 1.4 Подключить `services/devices.archive_device`,
      `services/devices.restore_device`, `services/maintenance.change_status`,
      `services/condition_reports.create_report`. Проверка: `uv run pytest
      tests/test_notifications_events.py -q` зелёный, остальные тесты
      устройств не сломаны (`uv run pytest tests/test_devices_archive.py
      tests/test_return.py tests/test_repairs.py -q`).

## 2. Уведомления по учётным записям

- [x] 2.1 Дописать тесты `test_notifications_events.py`: деактивация
      уведомляет активных админов, кроме инициатора; смена роли уведомляет
      самого сотрудника; правка карточки без `role` уведомления не создаёт;
      сброс пароля админом уведомляет сотрудника; смена собственного пароля
      уведомления не создаёт. Проверка: `uv run pytest
      tests/test_notifications_events.py -q` падает на новых тестах.
- [x] 2.2 Вызвать `notify_*` из `services/users.deactivate_user`,
      `services/users.update_user`, `services/users.set_password` (передача
      инициатора, чтобы смена собственного пароля не уведомляла себя).
      Проверка: `uv run pytest tests/test_notifications_events.py
      tests/test_users*.py -q` зелёный.

## 3. Просрочка и срок хранения

- [x] 3.1 Написать падающие тесты `backend/tests/test_notifications_overdue.py`:
      активная просроченная выдача (дата в прошлом, `holder != owner`)
      создаёт уведомление владельцу и всем активным админам; повторный запуск
      не создаёт дублей; выдача владельцу и бессрочная выдача не уведомляются;
      запись старше 90 дней удаляется и не попадает в список. Проверка:
      `uv run pytest tests/test_notifications_overdue.py -q` падает.
- [x] 3.2 Реализовать в `services/notifications.py` `sweep_overdue` (формула
      просрочки из `device_state`, дедупликация по паре «получатель +
      checkout_id») и `purge_expired` (90 дней). Проверка: `uv run pytest
      tests/test_notifications_overdue.py -q` зелёный.

## 4. API уведомлений

- [x] 4.1 Написать падающие тесты `backend/tests/test_notifications_api.py`:
      без сессии → 401; `GET /notifications` отдаёт только свои записи с
      `total`/`unread`; пагинация не меняет `total` и `unread`;
      `POST /notifications/{id}/read` чужого или неизвестного → 404;
      `POST /notifications/read-all` закрывает только свои; чтение списка
      подчищает записи старше 90 дней и материализует просрочку. Проверка:
      `uv run pytest tests/test_notifications_api.py -q` падает.
- [x] 4.2 Создать `backend/app/schemas/notifications.py`
      (`NotificationRead`, `NotificationListResponse`, `ReadAllResponse`) и
      `backend/app/api/notifications.py`, подключить роутер в `app/main.py`.
      Проверка: `uv run pytest tests/test_notifications_api.py -q` зелёный.
- [x] 4.3 Обновить контракт API: `uv run python -m app.export_openapi` и
      `uv run pytest tests/test_openapi.py -q` зелёный; `README.md`
      дополнен тремя уведомлительными эндпоинтами. Проверка: команды выше.

## 5. Интеграционная проверка

- [x] 5.1 Полный прогон: `uv run pytest -q`, `uv run ruff check .`,
      `openspec validate --all --strict` — всё зелёное.
- [x] 5.2 Ревью по AGENTS.md: `crapper`, `dryer`, `mutator` на backend;
      закрыть SURVIVED и высокий CRAP по новым модулям. Проверка: вывод
      инструментов без SURVIVED в `services/notifications.py`,
      `api/notifications.py` и `schemas/notifications.py`.

## Workflow follow-up

- Локальный коммит этапа (`feat(backend): notifications B6`).
- `openspec archive notifications` и повторный локальный коммит.
