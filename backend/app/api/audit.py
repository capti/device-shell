"""Аудит: глобальный журнал событий устройств с фильтрами по дате и устройству."""

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.clock import end_of_day, now_local, start_of_day
from app.db import get_db
from app.errors import AppError
from app.models import Device, DeviceEvent, User
from app.schemas.audit import (
    AuditEvent,
    AuditEventsResponse,
    LoginEvent,
    LoginEventsResponse,
)
from app.services import login_audit

router = APIRouter(tags=["audit"])

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
    """Возвращает запрос событий с фильтрами по устройству и/или дате."""
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
        thirty_days_ago = now_local() - timedelta(days=30)
        where_clauses.append(DeviceEvent.created_at >= thirty_days_ago)

    if where_clauses:
        query = query.where(*where_clauses)

    query = query.order_by(DeviceEvent.created_at.desc())
    return query


def get_audit_events(
    db: Session,
    *,
    device_id: int | None,
    from_at: datetime | None,
    to_at: datetime | None,
) -> list[dict[str, Any]]:
    """Возвращает список событий с развёрнутыми полями."""
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


async def _require_admin(user=Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise AppError(
            "FORBIDDEN",
            "Доступ к журналу аудита только для администраторов",
            status_code=403,
        )
    return user


@router.get("/audit/events", response_model=AuditEventsResponse)
def list_audit_events(
    device_id: int | None = Query(default=None, description="Идентификатор устройства"),
    from_at: datetime | None = Query(default=None, description="Начало диапазона (включительно)"),
    to_at: datetime | None = Query(default=None, description="Конец диапазона (включительно)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
) -> AuditEventsResponse:
    """Глобальный журнал аудита: события устройств с фильтрами по дате и устройству."""
    events = get_audit_events(db, device_id=device_id, from_at=from_at, to_at=to_at)
    return AuditEventsResponse(
        events=[AuditEvent.model_validate(event) for event in events],
        total=len(events),
        filtered_device_id=device_id,
        from_at=from_at,
        to_at=to_at,
    )


@router.get("/audit/logins", response_model=LoginEventsResponse)
def list_login_events(
    from_at: datetime | None = Query(default=None, description="Начало диапазона (включительно)"),
    to_at: datetime | None = Query(default=None, description="Конец диапазона (включительно)"),
    success: bool | None = Query(default=None, description="Исход попытки: истина или ложь"),
    username: str | None = Query(default=None, description="Введённый логин, часть строки"),
    limit: int = Query(default=login_audit.DEFAULT_LIMIT, ge=1, le=login_audit.MAX_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
) -> LoginEventsResponse:
    """Журнал входов: попытки с фильтрами по дате, логину и исходу."""
    events, total = login_audit.list_login_events(
        db,
        from_at=from_at,
        to_at=to_at,
        success=success,
        username=username,
        limit=limit,
    )
    return LoginEventsResponse(
        events=[LoginEvent.model_validate(event) for event in events],
        total=total,
        from_at=from_at,
        to_at=to_at,
        limit=limit,
    )
