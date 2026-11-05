"""Проверки прав на действия с устройством."""

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Device, User
from app.services.device_state import active_checkout


def ensure_can_manage(device: Device, actor: User) -> None:
    """Управлять устройством может владелец или администратор."""
    if actor.role == "admin" or device.owner_id == actor.id:
        return
    raise AppError(
        "FORBIDDEN",
        "Управлять устройством может только владелец или администратор",
        403,
    )


def ensure_can_act_on_hold(db: Session, device: Device, actor: User) -> None:
    """Действовать с телефоном может держатель, владелец или администратор."""
    if actor.role == "admin" or device.owner_id == actor.id:
        return
    checkout = active_checkout(db, device.id)
    if checkout is not None and checkout.user_id == actor.id:
        return
    raise AppError(
        "FORBIDDEN",
        "Действие доступно владельцу, держателю или администратору",
        403,
    )
