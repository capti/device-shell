"""Смена владельца устройства."""

from datetime import timedelta

from fastapi.testclient import TestClient
from helpers import checkout, create_device, login_as, register_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Checkout, Device, DeviceEvent


def _owner_events(db: Session, device_id: int) -> list[DeviceEvent]:
    return list(
        db.scalars(
            select(DeviceEvent).where(
                DeviceEvent.device_id == device_id,
                DeviceEvent.type == "owner_changed",
            )
        ).all()
    )


def test_owner_transfers_device_to_colleague(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    successor = register_user(make_user, username="successor")
    login_as(client, owner)
    device = create_device(client)

    response = client.post(
        f"/devices/{device['id']}/owner", json={"owner_id": successor.id}
    )

    assert response.status_code == 200
    card = response.json()
    assert card["owner"]["id"] == successor.id
    assert card["holder"]["id"] == successor.id
    events = _owner_events(db, device["id"])
    assert len(events) == 1
    assert events[0].payload == {"from": owner.id, "to": successor.id}


def test_transfer_to_current_holder_closes_checkout(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], holder)
    active = db.scalar(select(Checkout).where(Checkout.device_id == device["id"]))
    active.expected_return_at = now_local() - timedelta(days=2)
    db.commit()
    assert client.get("/devices", params={"overdue": "true"}).json()["total"] == 1

    response = client.post(
        f"/devices/{device['id']}/owner", json={"owner_id": holder.id}
    )

    assert response.status_code == 200
    card = response.json()
    assert card["overdue"] is False
    assert card["holder"]["id"] == holder.id
    db.refresh(active)
    assert active.closed_reason == "ownership_transferred"
    assert active.returned_at is not None
    closed_event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"],
            DeviceEvent.type == "checkout_closed",
        )
    )
    assert closed_event is not None
    assert closed_event.payload["reason"] == "ownership_transferred"


def test_transfer_to_third_party_keeps_holder(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    successor = register_user(make_user, username="successor")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], holder)

    response = client.post(
        f"/devices/{device['id']}/owner", json={"owner_id": successor.id}
    )

    assert response.status_code == 200
    assert response.json()["holder"]["id"] == holder.id
    assert response.json()["owner"]["id"] == successor.id
    active = db.scalar(select(Checkout).where(Checkout.device_id == device["id"]))
    assert active.returned_at is None
    assert active.closed_reason is None


def test_user_cannot_transfer_foreign_device(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    stranger = register_user(make_user, username="stranger")
    device = create_device(client)

    client.cookies.clear()
    login_as(client, stranger)
    response = client.post(
        f"/devices/{device['id']}/owner", json={"owner_id": stranger.id}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_holder_cannot_transfer_ownership(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    receiver = register_user(make_user, username="receiver")
    device = create_device(client)
    checkout(client, device["id"], holder)

    client.cookies.clear()
    login_as(client, holder)
    response = client.post(
        f"/devices/{device['id']}/owner", json={"owner_id": receiver.id}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_admin_transfers_foreign_device(client: TestClient, make_user) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, register_user(make_user, username="owner"))
    successor = register_user(make_user, username="successor")
    device = create_device(client)

    client.cookies.clear()
    login_as(client, admin)
    response = client.post(
        f"/devices/{device['id']}/owner", json={"owner_id": successor.id}
    )

    assert response.status_code == 200
    assert response.json()["owner"]["id"] == successor.id


def test_inactive_new_owner_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    inactive = register_user(make_user, username="inactive", is_active=False)
    device = create_device(client)

    response = client.post(
        f"/devices/{device['id']}/owner", json={"owner_id": inactive.id}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "OWNER_INACTIVE"


def test_same_owner_is_idempotent(client: TestClient, make_user, db: Session) -> None:
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)

    response = client.post(
        f"/devices/{device['id']}/owner", json={"owner_id": owner.id}
    )

    assert response.status_code == 200
    assert response.json()["owner"]["id"] == owner.id
    assert _owner_events(db, device["id"]) == []


def test_archived_device_owner_cannot_change(
    client: TestClient, make_user, db: Session
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    successor = register_user(make_user, username="successor")
    device = create_device(client)
    assert client.post(f"/devices/{device['id']}/archive").status_code == 200

    response = client.post(
        f"/devices/{device['id']}/owner", json={"owner_id": successor.id}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "DEVICE_ARCHIVED"
    assert db.get(Device, device["id"]).owner_id != successor.id
