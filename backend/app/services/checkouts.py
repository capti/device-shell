"""Оборот устройства: выдача, возврат, передача держателю и история выдач."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.clock import now_local
from app.errors import AppError
from app.models import Checkout, Device, User
from app.schemas.rotation import CheckoutCreate, ReturnRequest, TransferRequest
from app.services.access import ensure_can_act_on_hold, ensure_can_manage
from app.services.condition_reports import create_report
from app.services.device_state import active_checkout, record_event, today_start
from app.services.history import device_history
from app.services.notifications import DEVICE_CHECKED_OUT, DEVICE_RETURNED, notify_owner

DEFAULT_CHECKOUT_DAYS = 14


def ensure_active_checkout(db: Session, device_id: int) -> Checkout:
    checkout = active_checkout(db, device_id)
    if checkout is None:
        raise AppError(
            "NO_ACTIVE_CHECKOUT",
            "У устройства нет активной выдачи",
            409,
        )
    return checkout


def ensure_device_available(device: Device) -> None:
    if device.archived_at is not None:
        raise AppError(
            "DEVICE_ARCHIVED",
            "Устройство в архиве: сначала восстановите его",
            409,
        )
    if device.status != "active":
        raise AppError(
            "DEVICE_UNAVAILABLE",
            "Устройство недоступно: оно в ремонте или потеряно",
            409,
        )


def ensure_holder(db: Session, holder_id: int) -> User:
    holder = db.get(User, holder_id)
    if holder is None or not holder.is_active:
        raise AppError(
            "HOLDER_INACTIVE",
            "Держатель не найден или деактивирован",
            422,
        )
    return holder


def resolve_expected_return(
    value: datetime | None, taken_at: datetime
) -> datetime:
    """Дата по умолчанию — +14 дней; дата в прошлом отклоняется."""
    if value is None:
        return taken_at + timedelta(days=DEFAULT_CHECKOUT_DAYS)
    if value < today_start(taken_at):
        raise AppError(
            "VALIDATION_ERROR",
            "Дата возврата не может быть в прошлом",
            422,
        )
    return value


def close_checkout(
    checkout: Checkout,
    *,
    reason: str,
    condition: str | None = None,
    comment: str | None = None,
    moment: datetime | None = None,
) -> None:
    """Закрывает выдачу: `returned_at` и `closed_reason` всегда вместе."""
    checkout.returned_at = moment or now_local()
    checkout.closed_reason = reason
    if condition is not None:
        checkout.condition_in = condition
    if comment is not None:
        checkout.comment_in = comment


def checkout_device(
    db: Session, device: Device, payload: CheckoutCreate, actor: User
) -> Device:
    ensure_can_manage(device, actor)
    ensure_device_available(device)
    if active_checkout(db, device.id) is not None:
        raise AppError(
            "ALREADY_CHECKED_OUT",
            "Устройство уже выдано: сначала примите его обратно",
            409,
        )
    if payload.holder_id == device.owner_id:
        raise AppError("SELF_CHECKOUT", "Нельзя выдать устройство самому себе", 409)
    holder = ensure_holder(db, payload.holder_id)
    taken_at = now_local()
    checkout = Checkout(
        device_id=device.id,
        user_id=holder.id,
        taken_at=taken_at,
        expected_return_at=resolve_expected_return(payload.expected_return_at, taken_at),
        condition_out=payload.condition_out,
        comment_out=payload.comment_out,
        created_by=actor.id,
    )
    db.add(checkout)
    db.flush()
    record_event(
        db,
        device_id=device.id,
        actor_id=actor.id,
        event_type="checked_out",
        payload={
            "checkout_id": checkout.id,
            "holder_id": holder.id,
            "expected_return_at": checkout.expected_return_at.isoformat(),
        },
    )
    notify_owner(
        db,
        device,
        type=DEVICE_CHECKED_OUT,
        actor_id=actor.id,
        extra={"checkout_id": checkout.id, "holder_id": holder.id},
    )
    db.commit()
    db.refresh(device)
    return device


def return_device(
    db: Session, device: Device, payload: ReturnRequest, actor: User
) -> Device:
    ensure_can_act_on_hold(db, device, actor)
    checkout = ensure_active_checkout(db, device.id)
    moment = now_local()
    close_checkout(
        checkout,
        reason="returned",
        condition=payload.condition_in,
        comment=payload.comment_in,
        moment=moment,
    )
    report = create_report(
        db,
        device,
        actor,
        condition=payload.condition_in,
        requires_repair=payload.requires_repair,
        comment=payload.comment_in,
        checkout_id=checkout.id,
    )
    record_event(
        db,
        device_id=device.id,
        actor_id=actor.id,
        event_type="returned",
        payload={
            "checkout_id": checkout.id,
            "report_id": report.id,
            "condition": report.condition,
            "requires_repair": report.requires_repair,
        },
    )
    notify_owner(
        db,
        device,
        type=DEVICE_RETURNED,
        actor_id=actor.id,
        extra={"checkout_id": checkout.id, "report_id": report.id},
    )
    db.commit()
    db.refresh(device)
    return device


def transfer_device(
    db: Session, device: Device, payload: TransferRequest, actor: User
) -> Device:
    ensure_can_act_on_hold(db, device, actor)
    checkout = ensure_active_checkout(db, device.id)
    if payload.holder_id == checkout.user_id:
        raise AppError(
            "SAME_HOLDER",
            "Устройство уже у этого держателя",
            409,
        )
    if payload.holder_id == device.owner_id:
        raise AppError(
            "SELF_CHECKOUT",
            "Чтобы вернуть телефон владельцу, используйте возврат",
            409,
        )
    holder = ensure_holder(db, payload.holder_id)
    moment = now_local()
    expected_return_at = resolve_expected_return(payload.expected_return_at, moment)

    close_checkout(
        checkout,
        reason="transferred",
        condition=payload.condition_in,
        comment=payload.comment,
        moment=moment,
    )
    # Сначала закрываем старую выдачу в БД: partial unique index не пропустит
    # вторую активную выдачу на то же устройство.
    db.flush()
    if payload.condition_in is not None:
        create_report(
            db,
            device,
            actor,
            condition=payload.condition_in,
            comment=payload.comment,
            checkout_id=checkout.id,
        )

    new_checkout = Checkout(
        device_id=device.id,
        user_id=holder.id,
        taken_at=moment,
        expected_return_at=expected_return_at,
        condition_out=payload.condition_in,
        comment_out=payload.comment,
        created_by=actor.id,
    )
    db.add(new_checkout)
    db.flush()
    record_event(
        db,
        device_id=device.id,
        actor_id=actor.id,
        event_type="transferred",
        payload={
            "from_holder_id": checkout.user_id,
            "to_holder_id": holder.id,
            "checkout_id": new_checkout.id,
            "previous_checkout_id": checkout.id,
        },
    )
    db.commit()
    db.refresh(device)
    return device


def list_checkouts(db: Session, device_id: int) -> list[Checkout]:
    return device_history(db, Checkout, device_id, Checkout.taken_at)
