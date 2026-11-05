"""Просроченные выдачи, однократность уведомлений и срок хранения."""

from datetime import timedelta

from fastapi.testclient import TestClient
from helpers import add_checkout, create_device, login_as, notifications, register_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Device, Notification
from app.services.device_state import today_start
from app.services.notifications import (
    CHECKOUT_OVERDUE,
    NOTIFICATION_TTL_DAYS,
    purge_expired,
    sweep_overdue,
)


def _overdue_notes(db: Session) -> list[Notification]:
    return notifications(db, type_=CHECKOUT_OVERDUE)


def test_overdue_checkout_notifies_owner_and_admins(
    client: TestClient, make_user, db: Session
) -> None:
    first_admin = register_user(make_user, username="admin1", role="admin")
    second_admin = register_user(make_user, username="admin2", role="admin")
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    device_row = db.get(Device, device["id"])
    add_checkout(
        db, device_row, holder, expected_return_at=now_local() - timedelta(days=2)
    )

    created = sweep_overdue(db)

    notes = _overdue_notes(db)
    assert created == 3
    assert {item.recipient_id for item in notes} == {
        owner.id,
        first_admin.id,
        second_admin.id,
    }
    assert all(item.device_id == device_row.id for item in notes)
    assert len({item.payload["checkout_id"] for item in notes}) == 1


def test_overdue_sweep_is_idempotent(
    client: TestClient, make_user, db: Session
) -> None:
    first_admin = register_user(make_user, username="admin1", role="admin")
    second_admin = register_user(make_user, username="admin2", role="admin")
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    add_checkout(
        db,
        db.get(Device, device["id"]),
        holder,
        expected_return_at=now_local() - timedelta(days=2),
    )

    sweep_overdue(db)
    sweep_overdue(db)

    notes = _overdue_notes(db)
    assert len(notes) == 3
    assert {item.recipient_id for item in notes} == {
        owner.id,
        first_admin.id,
        second_admin.id,
    }


def test_not_overdue_checkouts_stay_silent(db: Session, make_user, make_device) -> None:
    register_user(make_user, username="admin", role="admin")
    owner = make_user(username="owner")
    holder = make_user(username="holder")
    held_by_owner = make_device(owner=owner, inventory_no="QA-PH-001")
    open_ended = make_device(owner=owner, inventory_no="QA-PH-002")
    add_checkout(
        db,
        held_by_owner,
        owner,
        expected_return_at=today_start() - timedelta(days=3),
    )
    add_checkout(db, open_ended, holder, expected_return_at=None)

    created = sweep_overdue(db)

    assert created == 0
    assert _overdue_notes(db) == []


def test_expired_notification_is_deleted(db: Session, make_user) -> None:
    user = make_user(username="owner")
    fresh = Notification(
        recipient_id=user.id, type="owner_changed", created_at=now_local()
    )
    stale = Notification(
        recipient_id=user.id,
        type="owner_changed",
        created_at=now_local() - timedelta(days=NOTIFICATION_TTL_DAYS + 1),
    )
    db.add_all([fresh, stale])
    db.commit()

    removed = purge_expired(db)

    assert removed == 1
    assert [item.id for item in db.scalars(select(Notification))] == [fresh.id]


def test_purge_keeps_notification_on_ttl_boundary(db: Session, make_user) -> None:
    """Уведомление с created_at ровно на границе срока ещё не протухло."""
    user = make_user(username="owner")
    moment = now_local()
    boundary = Notification(
        recipient_id=user.id,
        type="owner_changed",
        created_at=moment - timedelta(days=NOTIFICATION_TTL_DAYS),
    )
    older = Notification(
        recipient_id=user.id,
        type="owner_changed",
        created_at=moment - timedelta(days=NOTIFICATION_TTL_DAYS, seconds=5),
    )
    db.add_all([boundary, older])
    db.commit()

    removed = purge_expired(db, moment=moment)

    assert removed == 1
    assert [item.id for item in db.scalars(select(Notification))] == [boundary.id]


def test_purge_returns_zero_when_nothing_expired(db: Session, make_user) -> None:
    user = make_user(username="owner")
    fresh = Notification(
        recipient_id=user.id, type="owner_changed", created_at=now_local()
    )
    db.add(fresh)
    db.commit()

    assert purge_expired(db) == 0
    assert [item.id for item in db.scalars(select(Notification))] == [fresh.id]
