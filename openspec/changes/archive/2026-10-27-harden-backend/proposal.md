# Proposal

## Why

Контракт ошибок и защита истории сейчас держатся на соглашениях, а не на коде и
БД. Необработанное исключение отдаёт `text/plain` вместо `{code, message}`,
мутация без `Origin` проходит в production, `checkouts` допускает
несогласованные состояния (`returned_at` без причины закрытия и наоборот), а
append-only для `device_events` ничем не обеспечен. Это ломает контракт API из
`AGENTS.md` и инварианты домена, поэтому чиним до появления доменных ручек.

## What Changes

- Любое необработанное исключение возвращает JSON `{code, message}` с кодом
  `INTERNAL_ERROR`, сообщением на русском и без деталей стека; трейс пишется в
  лог.
- В production мутирующий запрос без заголовка `Origin` отклоняется с 403.
  В dev/test отсутствие `Origin` по-прежнему разрешено для curl и тестов.
  **BREAKING** для не-браузерных клиентов, которые ходят в production без
  `Origin`.
- `checkouts` получает CHECK-ограничение: `returned_at IS NULL` тогда и только
  тогда, когда `closed_reason IS NULL`.
- `device_events` защищается SQLite-триггерами `BEFORE UPDATE` и
  `BEFORE DELETE`, которые прерывают операцию.
- Обе гарантии добавляются Alembic-миграцией и тестами на уровне БД и API.

Не входит в изменение: управление пользователями и сброс пароля, frontend,
новые эндпоинты, регистронезависимый username, периодическая очистка сессий,
а также уже сделанные тесты и чистка этапа 1.

## Capabilities

### New Capabilities

- `api-errors`: единый JSON-конверт ошибок для всех ответов, включая
  необработанные 5xx.

### Modified Capabilities

- `access-control`: проверка `Origin` становится обязательной в production.
- `checkout-lifecycle`: состояние выдачи должно быть согласовано —
  `returned_at` и `closed_reason` либо оба пусты, либо оба заполнены.
- `audit-log`: запрет изменения и удаления событий обеспечивается БД, а не
  только отсутствием эндпоинтов.

## Impact

- `backend/app/errors.py` — обработчик необработанных исключений.
- `backend/app/middleware.py` — режим production для отсутствующего `Origin`.
- `backend/app/models/checkouts.py` — CHECK-ограничение.
- `backend/app/models/audit.py` — триггеры append-only.
- `backend/alembic/versions/` — новая миграция.
- `backend/tests/` — тесты контракта ошибок, Origin, CHECK и триггеров.
- Внешнее поведение API: формат 500 и ответ на мутацию без `Origin` в
  production. Frontend не меняется.
