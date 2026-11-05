"""Отчёты о состоянии устройства: создание и чтение."""

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import ConditionReport, Device, User
from app.schemas.maintenance import ConditionReportCreate
from app.services.access import ensure_can_act_on_hold
from app.services.device_state import active_checkout, record_event
from app.services.history import device_history
from app.services.notifications import (
    CONDITION_REPORTED,
    REQUIRES_REPAIR,
    notify_admins,
    notify_owner,
)


def create_report(
    db: Session,
    device: Device,
    actor: User,
    *,
    condition: str,
    requires_repair: bool = False,
    comment: str | None = None,
    checkout_id: int | None = None,
) -> ConditionReport:
    """Добавляет отчёт без коммита — коммитит вызывающий сервис."""
    report = ConditionReport(
        device_id=device.id,
        checkout_id=checkout_id,
        author_id=actor.id,
        condition=condition,
        requires_repair=requires_repair,
        comment=comment,
    )
    db.add(report)
    db.flush()
    notify_owner(
        db,
        device,
        type=CONDITION_REPORTED,
        actor_id=actor.id,
        extra={"report_id": report.id},
    )
    if requires_repair:
        notify_admins(
            db,
            device,
            type=REQUIRES_REPAIR,
            actor_id=actor.id,
            extra={"report_id": report.id, "condition": condition},
        )
    return report


def submit_report(
    db: Session, device: Device, payload: ConditionReportCreate, actor: User
) -> ConditionReport:
    ensure_can_act_on_hold(db, device, actor)
    if device.archived_at is not None:
        raise AppError(
            "DEVICE_ARCHIVED",
            "Устройство в архиве: сначала восстановите его",
            409,
        )

    checkout = active_checkout(db, device.id)
    report = create_report(
        db,
        device,
        actor,
        condition=payload.condition,
        requires_repair=payload.requires_repair,
        comment=payload.comment,
        checkout_id=checkout.id if checkout is not None else None,
    )
    record_event(
        db,
        device_id=device.id,
        actor_id=actor.id,
        event_type="condition_reported",
        payload={
            "report_id": report.id,
            "condition": report.condition,
            "requires_repair": report.requires_repair,
        },
    )
    db.commit()
    db.refresh(report)
    return report


def list_reports(db: Session, device_id: int) -> list[ConditionReport]:
    return device_history(db, ConditionReport, device_id, ConditionReport.created_at)
