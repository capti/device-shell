# Tasks

## 1. Модель и миграция

- [x] 1.1 `backend/app/models/login_events.py`: `LoginEvent` с временем,
      введённым логином, `user_id` (NULL, если пользователя нет), исходом,
      причиной, IP и user-agent; индексы по времени и логину.
- [x] 1.2 Триггеры `no_update`/`no_delete` на модели и в миграции
      `0003_login_events.py` (upgrade/downgrade).
- [x] 1.3 `backend/tests/test_migrations.py`: таблица и триггеры видны после
      `upgrade head`, после `downgrade 0001` — нет.

## 2. Запись попыток

- [x] 2.1 `backend/app/services/login_audit.py`: `record_login_attempt()` на
      отдельной сессии БД.
- [x] 2.2 Вызовы в `app/api/auth.py`: успех, неверный пароль, неизвестный
      логин, деактивированная учётная запись, отсечённый rate-limit'ом.
- [x] 2.3 Границы дня `start_of_day`/`end_of_day` переезжают в
      `app/clock.py`, оба журнала используют общие хелперы.

## 3. Чтение журнала

- [x] 3.1 `GET /audit/logins`: фильтры `from_at`, `to_at`, `success`,
      `username`, `limit` (по умолчанию 200, максимум 1000), только админ.
- [x] 3.2 `backend/app/schemas/audit.py`: `LoginEvent`, `LoginEventsResponse`
      с `total` по всей выборке.

## 4. Тесты

- [x] 4.1 `backend/tests/test_login_audit.py`: успешный вход, неверный пароль,
      неизвестный логин, деактивированная запись, rate limit — по записи на
      каждый случай с IP и user-agent.
- [x] 4.2 Запись переживает 401: после неудачного входа строка в БД есть.
- [x] 4.3 UPDATE/DELETE отклоняются триггером.
- [x] 4.4 Фильтры по дате (границы дня включительно), логину и исходу; лимит
      обрезает ответ, `total` остаётся полным; не-админ получает 403.

## 5. Проверка

- [x] 5.1 `uv run pytest` и `uv run ruff check .` — зелёные.
- [x] 5.2 Перегенерация `backend/openapi.json` (guard-тест следит).
- [x] 5.3 `openspec validate --all --strict` — без ошибок.
- [x] 5.4 README: журнал входов в разделе про события и API.
