"""Эндпоинты устройств: список, карточка, архив, восстановление, история."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.reject import reject_deletion
from app.api.serializers import device_card, device_reads, user_brief, users_by_id
from app.db import get_db
from app.models import DeviceEvent, User
from app.schemas.devices import (
    ArchivedFilter,
    DeviceCreate,
    DeviceEventRead,
    DeviceListResponse,
    DeviceRead,
    DeviceSort,
    DeviceStatus,
    DeviceUpdate,
    RestoreRequest,
)
from app.services import devices as devices_service
from app.services.devices import DeviceListParams

router = APIRouter(prefix="/devices", tags=["devices"])


@router.get("", response_model=DeviceListResponse)
def list_devices(
    q: str | None = Query(default=None, max_length=128),
    status_filter: DeviceStatus | None = Query(default=None, alias="status"),
    owner_id: int | None = None,
    holder_id: int | None = None,
    overdue: bool | None = None,
    mine: bool = False,
    archived: ArchivedFilter = "false",
    sort: DeviceSort = "inventory_no",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceListResponse:
    params = DeviceListParams(
        query=q,
        status=status_filter,
        owner_id=owner_id,
        holder_id=holder_id,
        overdue=overdue,
        mine=mine,
        archived=archived,
        sort=sort,
        page=page,
        page_size=page_size,
    )
    rows, total = devices_service.list_devices(db, user, params)
    return DeviceListResponse(
        items=device_reads(db, rows), total=total, page=page, page_size=page_size
    )


@router.post("", response_model=DeviceRead, status_code=status.HTTP_201_CREATED)
def create_device(
    payload: DeviceCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceRead:
    device = devices_service.create_device(db, payload, user)
    return device_card(db, device.id)


@router.get("/{device_id}", response_model=DeviceRead)
def read_device(
    device_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceRead:
    return device_card(db, device_id)


@router.patch("/{device_id}", response_model=DeviceRead)
def update_device(
    device_id: int,
    payload: DeviceUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceRead:
    device = devices_service.get_device(db, device_id)
    devices_service.update_device(db, device, payload, user)
    return device_card(db, device_id)


@router.delete("/{device_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
def delete_device(device_id: int, _user: User = Depends(get_current_user)) -> None:
    reject_deletion("Удаление не поддерживается. Отправьте устройство в архив")


@router.post("/{device_id}/archive", response_model=DeviceRead)
def archive_device(
    device_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceRead:
    device = devices_service.get_device(db, device_id)
    devices_service.archive_device(db, device, user)
    return device_card(db, device_id)


@router.post("/{device_id}/restore", response_model=DeviceRead)
def restore_device(
    device_id: int,
    payload: RestoreRequest | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceRead:
    device = devices_service.get_device(db, device_id)
    devices_service.restore_device(db, device, payload or RestoreRequest(), user)
    return device_card(db, device_id)


def _to_event(event: DeviceEvent, users: dict[int, User]) -> DeviceEventRead:
    actor = users.get(event.actor_id) if event.actor_id is not None else None
    return DeviceEventRead(
        id=event.id,
        type=event.type,
        actor=user_brief(actor) if actor is not None else None,
        payload=event.payload,
        created_at=event.created_at,
    )


@router.get("/{device_id}/history", response_model=list[DeviceEventRead])
def read_history(
    device_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[DeviceEventRead]:
    events = devices_service.get_history(db, device_id)
    users = users_by_id(db, (event.actor_id for event in events))
    return [_to_event(event, users) for event in events]
