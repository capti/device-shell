from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Checkout


def _checkout(db: Session, *, device_id: int, user_id: int, returned: bool = False) -> Checkout:
    now = now_local()
    checkout = Checkout(
        device_id=device_id,
        user_id=user_id,
        taken_at=now,
        expected_return_at=now + timedelta(days=14),
        returned_at=now if returned else None,
        condition_out="ok",
        condition_in="ok" if returned else None,
        closed_reason="returned" if returned else None,
    )
    db.add(checkout)
    return checkout


def test_second_active_checkout_is_rejected(db: Session, make_user, make_device) -> None:
    owner = make_user(username="owner")
    holder = make_user(username="holder")
    device = make_device(owner=owner)
    _checkout(db, device_id=device.id, user_id=holder.id)
    db.commit()

    _checkout(db, device_id=device.id, user_id=holder.id)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_closed_checkout_allows_new_active_one(db: Session, make_user, make_device) -> None:
    owner = make_user(username="owner")
    holder = make_user(username="holder")
    device = make_device(owner=owner)

    _checkout(db, device_id=device.id, user_id=holder.id, returned=True)
    db.commit()
    _checkout(db, device_id=device.id, user_id=holder.id)
    db.commit()

    active = db.query(Checkout).filter(Checkout.returned_at.is_(None)).all()
    assert len(active) == 1


def test_active_checkout_without_closed_reason_is_saved(
    db: Session, make_user, make_device
) -> None:
    owner = make_user(username="owner")
    holder = make_user(username="holder")
    device = make_device(owner=owner)
    checkout = _checkout(db, device_id=device.id, user_id=holder.id)

    db.commit()

    assert checkout.id is not None
    assert checkout.returned_at is None
    assert checkout.closed_reason is None


def test_closed_checkout_with_reason_is_saved(
    db: Session, make_user, make_device
) -> None:
    owner = make_user(username="owner")
    holder = make_user(username="holder")
    device = make_device(owner=owner)
    checkout = _checkout(db, device_id=device.id, user_id=holder.id, returned=True)

    db.commit()

    assert checkout.id is not None
    assert checkout.returned_at is not None
    assert checkout.closed_reason == "returned"


def test_returned_at_requires_closed_reason(
    db: Session, make_user, make_device
) -> None:
    owner = make_user(username="owner")
    holder = make_user(username="holder")
    device = make_device(owner=owner)
    checkout = _checkout(db, device_id=device.id, user_id=holder.id)
    checkout.returned_at = now_local()
    checkout.closed_reason = None
    db.add(checkout)

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_closed_reason_requires_returned_at(
    db: Session, make_user, make_device
) -> None:
    owner = make_user(username="owner")
    holder = make_user(username="holder")
    device = make_device(owner=owner)
    checkout = _checkout(db, device_id=device.id, user_id=holder.id)
    checkout.returned_at = None
    checkout.closed_reason = "returned"
    db.add(checkout)

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_active_checkout_partial_index_exists(db: Session) -> None:
    with db.connection() as connection:
        row = connection.execute(
            text(
                "SELECT sql FROM sqlite_master "
                "WHERE type = 'index' AND name = 'uq_checkouts_active_device'"
            )
        ).scalar_one()

    assert "returned_at IS NULL" in row


def test_closed_reason_is_limited_by_check_constraint(
    db: Session, make_user, make_device
) -> None:
    owner = make_user(username="owner")
    holder = make_user(username="holder")
    device = make_device(owner=owner)
    checkout = _checkout(db, device_id=device.id, user_id=holder.id, returned=True)
    checkout.closed_reason = "lost"
    db.add(checkout)

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
