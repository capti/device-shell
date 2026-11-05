"""Статусы `lost`/`active` и журнал ремонтов устройства."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.clock import now_local
from app.errors import AppError
from app.models import Device, Repair, User
from app.schemas.maintenance import (
    RepairCreate,
    RepairFinishRequest,
    StatusChangeRequest,
)
from app.services.access import ensure_can_manage
from app.services.device_state import active_checkout, record_event
from app.services.history import device_history
from app.services.notifications import DEVICE_LOST, notify_admins

_STATUS_MESSAGES = {
    "lost": "Отметить потерянным можно только активное устройство",
    "active": "Вернуть в работу можно только потерянное устройство",
}


def _ensure_not_archived(device: Device) -> None:
    if device.archived_at is not None:
        raise AppError(
            "DEVICE_ARCHIVED",
            "Устройство в архиве: сначала восстановите его",
            409,
        )


def _ensure_transition(device: Device, target: str) -> None:
    allowed = {"lost": "active", "active": "lost"}
    if device.status != allowed[target]:
        raise AppError(
            "INVALID_STATUS_TRANSITION",
            _STATUS_MESSAGES[target],
            409,
        )


def change_status(
    db: Session, device: Device, payload: StatusChangeRequest, actor: User
) -> Device:
    ensure_can_manage(device, actor)
    _ensure_not_archived(device)
    _ensure_transition(device, payload.status)
    if payload.status == "active" and not payload.comment:
        raise AppError(
            "COMMENT_REQUIRED",
            "Укажите комментарий: где и при каких обстоятельствах нашлось устройство",
            422,
        )

    previous_status = device.status
    device.status = payload.status
    record_event(
        db,
        device_id=device.id,
        actor_id=actor.id,
        event_type="status_changed",
        payload={
            "from": previous_status,
            "to": payload.status,
            "comment": payload.comment,
        },
    )
    if payload.status == "lost":
        notify_admins(db, device, type=DEVICE_LOST, actor_id=actor.id)
    db.commit()
    db.refresh(device)
    return device


def start_repair(
    db: Session, device: Device, payload: RepairCreate, actor: User
) -> Repair:
    ensure_can_manage(device, actor)
    _ensure_not_archived(device)
    if active_checkout(db, device.id) is not None:
        raise AppError(
            "ACTIVE_CHECKOUT",
            "Сначала примите телефон у держателя",
            409,
        )
    if device.status != "active":
        raise AppError(
            "DEVICE_UNAVAILABLE",
            "В ремонт можно отправить только активное устройство",
            409,
        )

    repair = Repair(
        device_id=device.id,
        sent_at=now_local(),
        service=payload.service,
        description=payload.description,
        cost=payload.cost,
        comment=payload.comment,
        created_by=actor.id,
    )
    db.add(repair)
    device.status = "repair"
    db.flush()
    record_event(
        db,
        device_id=device.id,
        actor_id=actor.id,
        event_type="repair_started",
        payload={"repair_id": repair.id, "service": repair.service},
    )
    db.commit()
    db.refresh(repair)
    return repair


def get_repair(db: Session, device_id: int, repair_id: int) -> Repair:
    repair = db.get(Repair, repair_id)
    if repair is None or repair.device_id != device_id:
        raise AppError("REPAIR_NOT_FOUND", "Запись ремонта не найдена", 404)
    return repair


def finish_repair(
    db: Session,
    device: Device,
    repair_id: int,
    payload: RepairFinishRequest,
    actor: User,
) -> Repair:
    ensure_can_manage(device, actor)
    repair = get_repair(db, device.id, repair_id)
    if repair.returned_at is not None:
        raise AppError("REPAIR_ALREADY_FINISHED", "Ремонт уже завершён", 409)

    returned_at: datetime = payload.returned_at or now_local()
    if returned_at < repair.sent_at:
        raise AppError(
            "VALIDATION_ERROR",
            "Дата возврата из ремонта не может быть раньше отправки",
            422,
        )
    repair.returned_at = returned_at
    if payload.comment is not None:
        repair.comment = payload.comment
    device.status = "active"
    record_event(
        db,
        device_id=device.id,
        actor_id=actor.id,
        event_type="repair_finished",
        payload={"repair_id": repair.id},
    )
    db.commit()
    db.refresh(repair)
    return repair


def list_repairs(db: Session, device_id: int) -> list[Repair]:
    return device_history(db, Repair, device_id, Repair.sent_at)
