import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import DeviceEvent, Notification


def _event(db: Session, make_user, make_device) -> DeviceEvent:
    actor = make_user()
    device = make_device(owner=actor)
    event = DeviceEvent(
        device_id=device.id,
        actor_id=actor.id,
        type="created",
        payload={"inventory_no": device.inventory_no},
    )
    db.add(event)
    db.commit()
    return event


def test_device_event_with_json_payload(db: Session, make_user, make_device) -> None:
    actor = make_user()
    device = make_device(owner=actor)

    event = DeviceEvent(
        device_id=device.id,
        actor_id=actor.id,
        type="created",
        payload={"inventory_no": device.inventory_no},
    )
    db.add(event)
    db.commit()

    assert event.id is not None
    assert event.payload == {"inventory_no": device.inventory_no}
    assert event.created_at is not None


def test_device_event_update_is_rejected(
    db: Session, make_user, make_device
) -> None:
    event = _event(db, make_user, make_device)

    with pytest.raises(IntegrityError):
        db.execute(
            text("UPDATE device_events SET type = 'archived' WHERE id = :id"),
            {"id": event.id},
        )
        db.commit()
    db.rollback()

    assert db.get(DeviceEvent, event.id).type == "created"


def test_device_event_delete_is_rejected(
    db: Session, make_user, make_device
) -> None:
    event = _event(db, make_user, make_device)

    with pytest.raises(IntegrityError):
        db.execute(
            text("DELETE FROM device_events WHERE id = :id"),
            {"id": event.id},
        )
        db.commit()
    db.rollback()

    assert db.get(DeviceEvent, event.id) is not None


def test_notification_with_indexed_read_state(db: Session, make_user, make_device) -> None:
    recipient = make_user(username="admin", role="admin")
    actor = make_user(username="user")
    device = make_device(owner=recipient)

    notification = Notification(
        recipient_id=recipient.id,
        actor_id=actor.id,
        type="device_archived",
        device_id=device.id,
        payload={"device_id": device.id},
    )
    db.add(notification)
    db.commit()

    assert notification.id is not None
    assert notification.read_at is None
    assert notification.payload == {"device_id": device.id}
