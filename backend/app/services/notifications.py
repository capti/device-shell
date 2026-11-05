"""Адресные уведомления: типы событий и запись без коммита.

Единственное место, где создаются строки `notifications`. Вызывающий сервис
добавляет уведомления в свою транзакцию и коммитит вместе с мутацией.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.clock import now_local
from app.errors import AppError
from app.models import Device, Notification, User
from app.services.device_state import device_state_query

# Типы уведомлений: строковые константы, их же понимает фронтенд.
OWNER_CHANGED = "owner_changed"
DEVICE_ARCHIVED = "device_archived"
DEVICE_RESTORED = "device_restored"
DEVICE_LOST = "device_lost"
REQUIRES_REPAIR = "requires_repair"
DEVICE_CHECKED_OUT = "device_checked_out"
DEVICE_RETURNED = "device_returned"
CONDITION_REPORTED = "condition_reported"
CHECKOUT_OVERDUE = "checkout_overdue"
USER_DEACTIVATED = "user_deactivated"
ROLE_CHANGED = "role_changed"
PASSWORD_RESET = "password_reset"

NOTIFICATION_TTL_DAYS = 90


def active_admin_ids(db: Session) -> list[int]:
    """Идентификаторы активных администраторов — основной групповой получатель."""
    statement = select(User.id).where(User.role == "admin", User.is_active.is_(True))
    return list(db.scalars(statement))


def notify(
    db: Session,
    *,
    type: str,
    recipients: Iterable[int],
    actor_id: int | None = None,
    device_id: int | None = None,
    payload: dict | None = None,
) -> None:
    """Ставит уведомления без коммита — коммитит вызывающий сервис."""
    for recipient_id in dict.fromkeys(recipients):
        db.add(
            Notification(
                recipient_id=recipient_id,
                actor_id=actor_id,
                type=type,
                device_id=device_id,
                payload=payload,
            )
        )


def notify_device(
    db: Session,
    device: Device,
    *,
    type: str,
    recipients: Iterable[int],
    actor_id: int | None = None,
    extra: dict | None = None,
) -> None:
    """Уведомление по устройству: в payload попадает снимок инвентарного номера."""
    payload: dict = {"inventory_no": device.inventory_no}
    if extra:
        payload.update(extra)
    notify(
        db,
        type=type,
        recipients=recipients,
        actor_id=actor_id,
        device_id=device.id,
        payload=payload,
    )


def notify_admins(
    db: Session,
    device: Device,
    *,
    type: str,
    actor_id: int | None = None,
    extra: dict | None = None,
) -> None:
    """Групповое уведомление активных администраторов."""
    notify_device(
        db,
        device,
        type=type,
        recipients=active_admin_ids(db),
        actor_id=actor_id,
        extra=extra,
    )


def notify_owner(
    db: Session,
    device: Device,
    *,
    type: str,
    actor_id: int | None = None,
    extra: dict | None = None,
) -> None:
    """Уведомление владельца устройства."""
    notify_device(
        db,
        device,
        type=type,
        recipients=[device.owner_id],
        actor_id=actor_id,
        extra=extra,
    )


def notify_employee(
    db: Session,
    *,
    type: str,
    employee_id: int,
    actor: User | None,
    payload: dict | None = None,
) -> None:
    """Уведомление о действии в чужой учётной записи.

    `actor is None` означает, что действие совершил сам сотрудник, — тогда
    уведомление не нужно.
    """
    if actor is None or actor.id == employee_id:
        return
    notify(db, type=type, recipients=[employee_id], actor_id=actor.id, payload=payload)


def _sent_overdue(db: Session, recipients: list[int]) -> set[tuple[int, int | None]]:
    """Пары «получатель + выдача», которым уведомление о просрочке уже уходило."""
    statement = select(Notification.recipient_id, Notification.payload).where(
        Notification.type == CHECKOUT_OVERDUE,
        Notification.recipient_id.in_(recipients),
    )
    pairs = db.execute(statement).all()
    return {
        (recipient_id, (payload or {}).get("checkout_id"))
        for recipient_id, payload in pairs
    }


def sweep_overdue(db: Session) -> int:
    """Материализует просрочку: по одному уведомлению на получателя и выдачу.

    Формула — общая с `device_state` (инвариант 6), поэтому здесь нет своей
    проверки дат. Возвращает число созданных записей и коммитит их сам.
    """
    state = device_state_query()
    rows = db.execute(state.statement.where(state.overdue == 1)).all()
    if not rows:
        return 0

    admins = active_admin_ids(db)
    owners = {row[0].owner_id for row in rows}
    sent = _sent_overdue(db, list(dict.fromkeys([*owners, *admins])))
    created = 0
    for row in rows:
        device: Device = row[0]
        candidates = dict.fromkeys([device.owner_id, *admins])
        fresh = [
            recipient
            for recipient in candidates
            if (recipient, row.checkout_id) not in sent
        ]
        if not fresh:
            continue
        notify(
            db,
            type=CHECKOUT_OVERDUE,
            recipients=fresh,
            device_id=device.id,
            payload={
                "inventory_no": device.inventory_no,
                "checkout_id": row.checkout_id,
            },
        )
        created += len(fresh)
    if created:
        db.commit()
    return created


def purge_expired(db: Session, *, moment: datetime | None = None) -> int:
    """Удаляет уведомления старше срока хранения; возвращает число удалённых."""
    moment = moment or now_local()
    cutoff = moment - timedelta(days=NOTIFICATION_TTL_DAYS)
    result = db.execute(delete(Notification).where(Notification.created_at < cutoff))
    removed = int(result.rowcount or 0)
    if removed:
        db.commit()
    return removed


@dataclass(frozen=True)
class NotificationPage:
    """Страница списка: записи, общий размер и число непрочитанных."""

    items: list[Notification]
    total: int
    unread: int


def list_notifications(
    db: Session,
    *,
    recipient_id: int,
    page: int,
    page_size: int,
    moment: datetime | None = None,
) -> NotificationPage:
    """Чтение списка одним заходом: подчищает старое и материализует просрочку."""
    moment = moment or now_local()
    purge_expired(db, moment=moment)
    sweep_overdue(db)

    cutoff = moment - timedelta(days=NOTIFICATION_TTL_DAYS)
    base = select(Notification).where(
        Notification.recipient_id == recipient_id,
        Notification.created_at >= cutoff,
    )
    unread_scope = base.where(Notification.read_at.is_(None))
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    unread = (
        db.scalar(select(func.count()).select_from(unread_scope.subquery())) or 0
    )
    items = list(
        db.scalars(
            base.order_by(Notification.created_at.desc(), Notification.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    )
    return NotificationPage(items=items, total=total, unread=unread)


def mark_read(
    db: Session,
    *,
    notification_id: int,
    recipient_id: int,
    moment: datetime | None = None,
) -> Notification:
    """Отмечает своё уведомление прочитанным; чужое и неизвестное — 404."""
    notification = db.get(Notification, notification_id)
    if notification is None or notification.recipient_id != recipient_id:
        raise AppError("NOTIFICATION_NOT_FOUND", "Уведомление не найдено", 404)
    if notification.read_at is None:
        notification.read_at = moment or now_local()
        db.commit()
        db.refresh(notification)
    return notification


def mark_all_read(
    db: Session, *, recipient_id: int, moment: datetime | None = None
) -> int:
    """Отмечает прочитанными все свои уведомления; возвращает их число."""
    statement = (
        update(Notification)
        .where(
            Notification.recipient_id == recipient_id,
            Notification.read_at.is_(None),
        )
        .values(read_at=moment or now_local())
        .execution_options(synchronize_session=False)
    )
    result = db.execute(statement)
    db.commit()
    return int(result.rowcount or 0)
