"""Глобальный журнал событий устройств: построение и выполнение запроса.

Логика вынесена из роута по правилу `AGENTS.md`: БД и SQL живут в сервисах,
роут только разбирает параметры запроса и проверяет ответ схемой.
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import end_of_day, now_local, start_of_day
from app.models import Device, DeviceEvent

# Окно по умолчанию — как в журнале входов: без фильтров журнал не должен
# возвращать всю историю.
DEFAULT_WINDOW_DAYS = 30

DEVICE_EVENT_TYPE_LABELS = {
    "created": "Создание",
    "updated": "Обновление",
    "owner_changed": "Смена владельца",
    "checked_out": "Выдача",
    "returned": "Возврат",
    "transferred": "Передача",
    "ownership_transferred": "Передача владения",
    "archived": "Архив",
    "restored": "Восстановление",
    "status_changed": "Смена статуса",
    "condition_reported": "Отчёт о состоянии",
    "photo_added": "Фото добавлено",
    "photo_removed": "Фото удалено",
}


def build_audit_query(
    *, device_id: int | None, from_at: datetime | None, to_at: datetime | None
) -> select:
    """Запрос событий с фильтрами по устройству и/или дате."""
    query = select(
        DeviceEvent.id,
        DeviceEvent.device_id,
        Device.inventory_no.label("inventory_no"),
        DeviceEvent.actor_id,
        DeviceEvent.type,
        DeviceEvent.payload,
        DeviceEvent.created_at,
    ).outerjoin(Device, Device.id == DeviceEvent.device_id)

    where_clauses: list = []

    if device_id is not None:
        where_clauses.append(Device.id == device_id)

    if from_at is not None:
        where_clauses.append(DeviceEvent.created_at >= start_of_day(from_at))
    if to_at is not None:
        where_clauses.append(DeviceEvent.created_at <= end_of_day(to_at))

    if not device_id and not from_at and not to_at:
        # По умолчанию — события за последние 30 дней: без фильтров запрос
        # не должен возвращать всю историю. Запрос по конкретному устройству
        # узкий сам по себе, окно ему не нужно.
        thirty_days_ago = now_local() - timedelta(days=DEFAULT_WINDOW_DAYS)
        where_clauses.append(DeviceEvent.created_at >= thirty_days_ago)

    if where_clauses:
        query = query.where(*where_clauses)

    # `clock.now_local()` имеет секундную точность: без второго ключа события
    # одной секунды сортируются нестабильно. `id.desc()` делает порядок
    # детерминированным — так же, как в таймлайне и журнале входов.
    return query.order_by(DeviceEvent.created_at.desc(), DeviceEvent.id.desc())


def list_audit_events(
    db: Session,
    *,
    device_id: int | None,
    from_at: datetime | None,
    to_at: datetime | None,
) -> list[dict[str, Any]]:
    """Возвращает события журнала с развёрнутыми полями, от новых к старым."""
    query = build_audit_query(device_id=device_id, from_at=from_at, to_at=to_at)
    rows = db.execute(query).all()

    events: list[dict[str, Any]] = []
    for row in rows:
        event_id, device_id_val, inventory_no, actor_id, event_type, payload, created_at = row
        event_type_label = DEVICE_EVENT_TYPE_LABELS.get(event_type, event_type)
        events.append({
            "event_id": event_id,
            "device_id": device_id_val,
            "inventory_no": inventory_no,
            "actor_id": actor_id,
            "event_type": event_type,
            "event_type_label": event_type_label,
            "payload": payload or {},
            "created_at": created_at,
        })
    return events
