"""Схемы запроса и ответа для журнала аудита."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    """Одно событие в журнале аудита."""

    event_id: int
    device_id: int | None
    inventory_no: str | None
    actor_id: int | None
    event_type: str
    event_type_label: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class AuditEventsResponse(BaseModel):
    """Ответ списка событий."""

    events: list[AuditEvent]
    total: int
    filtered_device_id: int | None
    from_at: datetime | None
    to_at: datetime | None


class LoginEvent(BaseModel):
    """Одна попытка входа в журнале."""

    event_id: int
    username_attempted: str
    user_id: int | None
    success: bool
    reason: str | None
    reason_label: str | None = None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginEventsResponse(BaseModel):
    """Ответ журнала входов: выборка и полное число подходящих записей."""

    events: list[LoginEvent]
    total: int
    from_at: datetime | None
    to_at: datetime | None
    limit: int
