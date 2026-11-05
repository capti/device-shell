"""Смена владельца устройства и автозакрытие выдачи у нового держателя."""

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import Device, User
from app.schemas.rotation import OwnerChangeRequest
from app.services.access import ensure_can_manage
from app.services.checkouts import close_checkout
from app.services.device_state import active_checkout, record_event
from app.services.notifications import OWNER_CHANGED, notify_admins


def change_owner(
    db: Session, device: Device, payload: OwnerChangeRequest, actor: User
) -> Device:
    ensure_can_manage(device, actor)
    if device.archived_at is not None:
        raise AppError(
            "DEVICE_ARCHIVED",
            "Устройство в архиве: сначала восстановите его",
            409,
        )
    if payload.owner_id == device.owner_id:
        # Повторная передача тому же владельцу — идемпотентный no-op.
        return device

    new_owner = db.get(User, payload.owner_id)
    if new_owner is None or not new_owner.is_active:
        raise AppError(
            "OWNER_INACTIVE",
            "Владелец не найден или деактивирован",
            422,
        )

    previous_owner_id = device.owner_id
    device.owner_id = new_owner.id
    record_event(
        db,
        device_id=device.id,
        actor_id=actor.id,
        event_type="owner_changed",
        payload={"from": previous_owner_id, "to": new_owner.id},
    )
    if actor.role != "admin":
        notify_admins(
            db,
            device,
            type=OWNER_CHANGED,
            actor_id=actor.id,
            extra={"from": previous_owner_id, "to": new_owner.id},
        )

    checkout = active_checkout(db, device.id)
    if checkout is not None and checkout.user_id == new_owner.id:
        close_checkout(checkout, reason="ownership_transferred")
        record_event(
            db,
            device_id=device.id,
            actor_id=actor.id,
            event_type="checkout_closed",
            payload={
                "checkout_id": checkout.id,
                "reason": "ownership_transferred",
            },
        )

    db.commit()
    db.refresh(device)
    return device
