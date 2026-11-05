"""Единое вычисление состояния устройства: держатель и просрочка.

Формула живёт здесь и только здесь: список, карточка, дашборд, Excel и
уведомления о просрочке обязаны брать `holder_id`/`overdue` из этого запроса
(инвариант 6).
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import ColumnElement, and_, case, func, select
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql import Select

from app.clock import now_local
from app.models import Checkout, Device, DeviceEvent


def today_start(moment: datetime | None = None) -> datetime:
    """Начало текущих локальных суток: с этого момента выдача считается просроченной."""
    moment = moment or now_local()
    return moment.replace(hour=0, minute=0, second=0, microsecond=0)


@dataclass(frozen=True)
class DeviceStateQuery:
    """Запрос устройств с вычисленными `holder_id`/`overdue` и сами выражения."""

    statement: Select
    holder_id: ColumnElement[int]
    overdue: ColumnElement[int]
    checkout_taken_at: ColumnElement[datetime | None]
    checkout_id: ColumnElement[int | None]


def device_state_query() -> DeviceStateQuery:
    """Строит `SELECT` устройств с активной выдачей, держателем и просрочкой."""
    active = aliased(Checkout, name="active_checkout")
    holder_id = func.coalesce(active.user_id, Device.owner_id)
    overdue = case(
        (
            and_(
                active.id.is_not(None),
                active.user_id != Device.owner_id,
                active.expected_return_at.is_not(None),
                active.expected_return_at < today_start(),
            ),
            1,
        ),
        else_=0,
    )
    statement = select(
        Device,
        holder_id.label("holder_id"),
        overdue.label("overdue"),
        active.expected_return_at.label("expected_return_at"),
        active.taken_at.label("checkout_taken_at"),
        active.id.label("checkout_id"),
    ).outerjoin(
        active,
        and_(active.device_id == Device.id, active.returned_at.is_(None)),
    )
    return DeviceStateQuery(
        statement=statement,
        holder_id=holder_id,
        overdue=overdue,
        checkout_taken_at=active.taken_at,
        checkout_id=active.id,
    )


def active_checkout(db: Session, device_id: int) -> Checkout | None:
    """Активная выдача устройства: `returned_at IS NULL` (она максимум одна)."""
    return db.scalar(
        select(Checkout).where(
            Checkout.device_id == device_id,
            Checkout.returned_at.is_(None),
        )
    )


def record_event(
    db: Session,
    *,
    device_id: int,
    actor_id: int | None,
    event_type: str,
    payload: dict | None = None,
) -> None:
    """Добавляет событие истории без коммита — коммитит вызывающий сервис."""
    db.add(
        DeviceEvent(
            device_id=device_id,
            actor_id=actor_id,
            type=event_type,
            payload=payload,
        )
    )
