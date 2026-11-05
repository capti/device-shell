"""Формула состояния устройства и запись событий истории."""

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Checkout, Device, DeviceEvent
from app.services.device_state import device_state_query, record_event, today_start


def _state(db: Session, device: Device):
    query = device_state_query()
    row = db.execute(query.statement.where(Device.id == device.id)).one()
    return row


def _add_checkout(
    db: Session,
    device: Device,
    holder,
    *,
    expected_return_at=None,
    returned_at=None,
) -> Checkout:
    checkout = Checkout(
        device_id=device.id,
        user_id=holder.id,
        taken_at=now_local() - timedelta(days=3),
        expected_return_at=expected_return_at,
        returned_at=returned_at,
        closed_reason="returned" if returned_at is not None else None,
    )
    db.add(checkout)
    db.commit()
    return checkout


def test_today_start_drops_time_of_day() -> None:
    moment = datetime(2026, 10, 27, 23, 45, 12, 345678)

    assert today_start(moment) == datetime(2026, 10, 27)


def test_without_checkout_holder_is_owner(db: Session, make_user, make_device) -> None:
    owner = make_user(username="owner")
    device = make_device(owner=owner)

    row = _state(db, device)

    assert row.holder_id == owner.id
    assert row.overdue == 0
    assert row.expected_return_at is None


def test_expired_checkout_marks_device_overdue(db: Session, make_user, make_device) -> None:
    owner = make_user(username="owner")
    holder = make_user(username="holder")
    device = make_device(owner=owner)
    _add_checkout(db, device, holder, expected_return_at=today_start() - timedelta(days=1))

    row = _state(db, device)

    assert row.holder_id == holder.id
    assert row.overdue == 1


def test_checkout_to_owner_is_never_overdue(db: Session, make_user, make_device) -> None:
    owner = make_user(username="owner")
    device = make_device(owner=owner)
    _add_checkout(db, device, owner, expected_return_at=today_start() - timedelta(days=1))

    row = _state(db, device)

    assert row.holder_id == owner.id
    assert row.overdue == 0


def test_checkout_without_due_date_is_never_overdue(
    db: Session, make_user, make_device
) -> None:
    owner = make_user(username="owner")
    holder = make_user(username="holder")
    device = make_device(owner=owner)
    _add_checkout(db, device, holder, expected_return_at=None)

    row = _state(db, device)

    assert row.overdue == 0


def test_due_today_is_not_overdue_yet(db: Session, make_user, make_device) -> None:
    owner = make_user(username="owner")
    holder = make_user(username="holder")
    device = make_device(owner=owner)
    _add_checkout(db, device, holder, expected_return_at=today_start())

    row = _state(db, device)

    assert row.overdue == 0


def test_closed_checkout_does_not_affect_state(db: Session, make_user, make_device) -> None:
    owner = make_user(username="owner")
    holder = make_user(username="holder")
    device = make_device(owner=owner)
    _add_checkout(
        db,
        device,
        holder,
        expected_return_at=today_start() - timedelta(days=1),
        returned_at=now_local(),
    )

    row = _state(db, device)

    assert row.holder_id == owner.id
    assert row.overdue == 0


def test_record_event_is_written_in_caller_transaction(
    db: Session, make_user, make_device
) -> None:
    owner = make_user(username="owner")
    device = make_device(owner=owner)

    record_event(db, device_id=device.id, actor_id=owner.id, event_type="created")
    db.commit()

    event = db.scalar(select(DeviceEvent).where(DeviceEvent.device_id == device.id))
    assert event is not None
    assert event.type == "created"


def test_record_event_rolls_back_with_transaction(
    db: Session, make_user, make_device
) -> None:
    owner = make_user(username="owner")
    device = make_device(owner=owner)

    record_event(db, device_id=device.id, actor_id=owner.id, event_type="created")
    db.rollback()

    assert db.scalar(select(DeviceEvent).where(DeviceEvent.device_id == device.id)) is None
