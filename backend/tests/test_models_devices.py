import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Device


def test_device_is_created_with_required_owner(db: Session, make_user, make_device) -> None:
    owner = make_user()

    device = make_device(owner=owner, inventory_no="QA-PH-010", imei="356938035643809")

    assert device.id is not None
    assert device.owner_id == owner.id
    assert device.status == "active"
    assert device.archived_at is None


def test_inventory_no_is_unique(db: Session, make_user, make_device) -> None:
    owner = make_user()
    make_device(owner=owner, inventory_no="QA-PH-001")

    with pytest.raises(IntegrityError):
        make_device(owner=owner, inventory_no="QA-PH-001")


def test_device_without_owner_is_rejected(db: Session, make_user) -> None:
    owner = make_user()
    device = Device(
        inventory_no="QA-PH-002",
        brand="Apple",
        model="iPhone 15",
        owner_id=None,  # type: ignore[arg-type]
        created_by=owner.id,
    )
    db.add(device)

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_device_with_unknown_owner_is_rejected(db: Session) -> None:
    device = Device(
        inventory_no="QA-PH-003",
        brand="Apple",
        model="iPhone 15",
        owner_id=999,
    )
    db.add(device)

    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_imei_is_unique_when_filled(db: Session, make_user, make_device) -> None:
    owner = make_user()
    make_device(owner=owner, inventory_no="QA-PH-004", imei="356938035643809")

    with pytest.raises(IntegrityError):
        make_device(owner=owner, inventory_no="QA-PH-005", imei="356938035643809")


def test_empty_imei_is_allowed_for_many_devices(db: Session, make_user, make_device) -> None:
    owner = make_user()
    make_device(owner=owner, inventory_no="QA-PH-006", imei=None)
    make_device(owner=owner, inventory_no="QA-PH-007", imei="")
    make_device(owner=owner, inventory_no="QA-PH-008", imei=None)

    assert db.query(Device).count() == 3


def test_serial_no_is_unique_when_filled(db: Session, make_user, make_device) -> None:
    owner = make_user()
    make_device(owner=owner, inventory_no="QA-PH-009", serial_no="R58N123ABC")

    with pytest.raises(IntegrityError):
        make_device(owner=owner, inventory_no="QA-PH-011", serial_no="R58N123ABC")


def test_status_is_limited_by_check_constraint(db: Session, make_user, make_device) -> None:
    owner = make_user()

    with pytest.raises(IntegrityError):
        make_device(owner=owner, inventory_no="QA-PH-012", status="storage")


def test_empty_imei_partial_index_exists(db: Session) -> None:
    with db.connection() as connection:
        indexes = connection.execute(
            text("SELECT name FROM sqlite_master WHERE type = 'index'")
        ).scalars()
        names = set(indexes)

    assert "uq_devices_imei" in names
    assert "uq_devices_serial_no" in names
