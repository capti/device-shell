"""Эндпоинты оборота: выдача, возврат, передача, владелец и статус."""

from collections.abc import Sequence

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.api.serializers import device_card, user_brief, users_by_id
from app.db import get_db
from app.models import Checkout, User
from app.schemas.devices import DeviceRead
from app.schemas.maintenance import StatusChangeRequest
from app.schemas.rotation import (
    CheckoutCreate,
    CheckoutRead,
    OwnerChangeRequest,
    ReturnRequest,
    TransferRequest,
)
from app.services import checkouts as checkouts_service
from app.services import devices as devices_service
from app.services import maintenance, ownership

router = APIRouter(prefix="/devices", tags=["rotation"])


def _checkout_read(checkout: Checkout, users: dict[int, User]) -> CheckoutRead:
    creator = users.get(checkout.created_by) if checkout.created_by is not None else None
    return CheckoutRead(
        id=checkout.id,
        device_id=checkout.device_id,
        holder=user_brief(users[checkout.user_id]),
        taken_at=checkout.taken_at,
        expected_return_at=checkout.expected_return_at,
        returned_at=checkout.returned_at,
        closed_reason=checkout.closed_reason,
        condition_out=checkout.condition_out,
        condition_in=checkout.condition_in,
        comment_out=checkout.comment_out,
        comment_in=checkout.comment_in,
        created_by=user_brief(creator) if creator is not None else None,
    )


def _checkout_list(db: Session, checkouts: Sequence[Checkout]) -> list[CheckoutRead]:
    users = users_by_id(
        db,
        [checkout.user_id for checkout in checkouts]
        + [checkout.created_by for checkout in checkouts],
    )
    return [_checkout_read(checkout, users) for checkout in checkouts]


@router.post("/{device_id}/checkout", response_model=DeviceRead)
def checkout_device(
    device_id: int,
    payload: CheckoutCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceRead:
    """Выдача активного устройства другому сотруднику (`holder != owner`)."""
    device = devices_service.get_device(db, device_id)
    checkouts_service.checkout_device(db, device, payload, user)
    return device_card(db, device_id)


@router.post("/{device_id}/return", response_model=DeviceRead)
def return_device(
    device_id: int,
    payload: ReturnRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceRead:
    """Возврат устройства владельцу с фиксацией отчёта о состоянии."""
    device = devices_service.get_device(db, device_id)
    checkouts_service.return_device(db, device, payload, user)
    return device_card(db, device_id)


@router.post("/{device_id}/transfer", response_model=DeviceRead)
def transfer_device(
    device_id: int,
    payload: TransferRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceRead:
    """Передача выданного устройства от текущего держателя другому сотруднику."""
    device = devices_service.get_device(db, device_id)
    checkouts_service.transfer_device(db, device, payload, user)
    return device_card(db, device_id)


@router.post("/{device_id}/owner", response_model=DeviceRead)
def change_owner(
    device_id: int,
    payload: OwnerChangeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceRead:
    """Смена владельца устройства (автозакрывает выдачу у текущего держателя)."""
    device = devices_service.get_device(db, device_id)
    ownership.change_owner(db, device, payload, user)
    return device_card(db, device_id)


@router.post("/{device_id}/status", response_model=DeviceRead)
def change_status(
    device_id: int,
    payload: StatusChangeRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceRead:
    """Переключение статуса устройства между `active` и `lost` владельцем или администратором."""
    device = devices_service.get_device(db, device_id)
    maintenance.change_status(db, device, payload, user)
    return device_card(db, device_id)


@router.get("/{device_id}/checkouts", response_model=list[CheckoutRead])
def read_checkouts(
    device_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[CheckoutRead]:
    """История всех выдач и возвратов конкретного устройства."""
    devices_service.get_device(db, device_id)
    return _checkout_list(db, checkouts_service.list_checkouts(db, device_id))
