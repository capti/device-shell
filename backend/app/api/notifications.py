"""Эндпоинты уведомлений: список со счётчиком, прочтение, прочитать всё."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.serializers import user_brief, users_by_id
from app.db import get_db
from app.models import Notification, User
from app.schemas.notifications import (
    NotificationListResponse,
    NotificationRead,
    ReadAllResponse,
)
from app.services import notifications as notifications_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _notification_read(
    notification: Notification, users: dict[int, User]
) -> NotificationRead:
    actor = users.get(notification.actor_id) if notification.actor_id is not None else None
    return NotificationRead(
        id=notification.id,
        type=notification.type,
        actor=user_brief(actor) if actor is not None else None,
        device_id=notification.device_id,
        payload=notification.payload,
        read_at=notification.read_at,
        created_at=notification.created_at,
    )


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationListResponse:
    result = notifications_service.list_notifications(
        db, recipient_id=user.id, page=page, page_size=page_size
    )
    users = users_by_id(db, (item.actor_id for item in result.items))
    return NotificationListResponse(
        items=[_notification_read(item, users) for item in result.items],
        total=result.total,
        page=page,
        page_size=page_size,
        unread=result.unread,
    )


@router.post("/{notification_id}/read", response_model=NotificationRead)
def read_notification(
    notification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> NotificationRead:
    notification = notifications_service.mark_read(
        db, notification_id=notification_id, recipient_id=user.id
    )
    users = users_by_id(db, [notification.actor_id])
    return _notification_read(notification, users)


@router.post("/read-all", response_model=ReadAllResponse)
def read_all(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ReadAllResponse:
    updated = notifications_service.mark_all_read(db, recipient_id=user.id)
    return ReadAllResponse(updated=updated)
