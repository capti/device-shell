"""Схемы уведомлений: запись, страница списка и отметка «прочитано»."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.schemas.devices import UserBrief


class NotificationRead(BaseModel):
    """Уведомление текущего пользователя; `device_id` ведёт в карточку."""

    id: int
    type: str
    actor: UserBrief | None
    device_id: int | None
    payload: dict[str, Any] | None
    read_at: datetime | None
    created_at: datetime


class NotificationListResponse(BaseModel):
    items: list[NotificationRead]
    total: int
    page: int
    page_size: int
    unread: int


class ReadAllResponse(BaseModel):
    updated: int
