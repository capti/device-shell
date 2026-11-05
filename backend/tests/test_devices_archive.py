"""Архив и восстановление устройства."""

from fastapi.testclient import TestClient
from helpers import add_checkout, create_device, login_as, register_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, DeviceEvent


def _archive(client: TestClient, device_id: int) -> None:
    response = client.post(f"/devices/{device_id}/archive")
    assert response.status_code == 200, response.text


def test_owner_archives_device(client: TestClient, make_user, db: Session) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    response = client.post(f"/devices/{device['id']}/archive")

    assert response.status_code == 200
    assert response.json()["archived_at"] is not None
    event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"], DeviceEvent.type == "archived"
        )
    )
    assert event is not None


def test_archived_device_leaves_active_list(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    _archive(client, device["id"])

    active = client.get("/devices")
    archived = client.get("/devices", params={"archived": "true"})

    assert active.json()["total"] == 0
    assert archived.json()["total"] == 1
    assert archived.json()["items"][0]["id"] == device["id"]


def test_archive_with_active_checkout_is_rejected(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    stored = db.get(Device, device["id"])
    add_checkout(db, stored, holder)

    response = client.post(f"/devices/{device['id']}/archive")

    assert response.status_code == 409
    assert response.json()["code"] == "ACTIVE_CHECKOUT"
    assert db.get(Device, device["id"]).archived_at is None


def test_admin_cannot_archive_device_with_active_checkout(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    add_checkout(db, db.get(Device, device["id"]), holder)

    client.cookies.clear()
    login_as(client, admin)
    response = client.post(f"/devices/{device['id']}/archive")

    assert response.status_code == 409
    assert response.json()["code"] == "ACTIVE_CHECKOUT"


def test_repeated_archive_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    _archive(client, device["id"])

    response = client.post(f"/devices/{device['id']}/archive")

    assert response.status_code == 409
    assert response.json()["code"] == "ALREADY_ARCHIVED"


def test_user_cannot_archive_foreign_device(client: TestClient, make_user) -> None:
    owner = register_user(make_user, username="owner")
    stranger = register_user(make_user, username="stranger")
    login_as(client, owner)
    device = create_device(client)

    client.cookies.clear()
    login_as(client, stranger)
    response = client.post(f"/devices/{device['id']}/archive")

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_admin_archives_foreign_device(client: TestClient, make_user) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)

    client.cookies.clear()
    login_as(client, admin)
    response = client.post(f"/devices/{device['id']}/archive")

    assert response.status_code == 200
    assert response.json()["archived_at"] is not None


def test_restore_active_device_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    response = client.post(f"/devices/{device['id']}/restore")

    assert response.status_code == 409
    assert response.json()["code"] == "NOT_ARCHIVED"


def test_restore_returns_device_to_active_list(
    client: TestClient, make_user, db: Session
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    _archive(client, device["id"])

    response = client.post(f"/devices/{device['id']}/restore", json={})

    assert response.status_code == 200
    assert response.json()["archived_at"] is None
    assert response.json()["status"] == "active"
    assert client.get("/devices").json()["total"] == 1
    event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"], DeviceEvent.type == "restored"
        )
    )
    assert event is not None


def test_restore_supports_target_status(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    _archive(client, device["id"])

    response = client.post(
        f"/devices/{device['id']}/restore", json={"status": "repair"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "repair"


def test_restore_with_deactivated_owner_requires_new_owner(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)
    _archive(client, device["id"])

    owner.is_active = False
    db.commit()

    client.cookies.clear()
    login_as(client, admin)
    response = client.post(f"/devices/{device['id']}/restore", json={})

    assert response.status_code == 422
    assert response.json()["code"] == "OWNER_REQUIRED"


def test_restore_with_new_owner_records_owner_change(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    successor = register_user(make_user, username="successor")
    login_as(client, owner)
    device = create_device(client)
    _archive(client, device["id"])
    owner.is_active = False
    db.commit()

    client.cookies.clear()
    login_as(client, admin)
    response = client.post(
        f"/devices/{device['id']}/restore", json={"owner_id": successor.id}
    )

    assert response.status_code == 200
    assert response.json()["owner"]["id"] == successor.id
    event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"],
            DeviceEvent.type == "owner_changed",
        )
    )
    assert event is not None
    assert event.payload == {"from": owner.id, "to": successor.id}


def test_restore_with_same_owner_keeps_single_owner_event(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    _archive(client, device["id"])
    owner = db.scalar(select(Device).where(Device.id == device["id"])).owner_id

    client.cookies.clear()
    login_as(client, admin)
    response = client.post(
        f"/devices/{device['id']}/restore", json={"owner_id": owner}
    )

    assert response.status_code == 200
    assert response.json()["owner"]["id"] == owner
    assert (
        db.scalar(
            select(DeviceEvent).where(
                DeviceEvent.device_id == device["id"],
                DeviceEvent.type == "owner_changed",
            )
        )
        is None
    )


def test_restore_with_deactivated_new_owner_is_rejected(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    _archive(client, device["id"])
    inactive = register_user(make_user, username="inactive", is_active=False)

    client.cookies.clear()
    login_as(client, admin)
    response = client.post(
        f"/devices/{device['id']}/restore", json={"owner_id": inactive.id}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "OWNER_INACTIVE"


def test_owner_cannot_assign_new_owner_on_restore(
    client: TestClient, make_user
) -> None:
    owner = register_user(make_user, username="owner")
    successor = register_user(make_user, username="successor")
    login_as(client, owner)
    device = create_device(client)
    _archive(client, device["id"])

    response = client.post(
        f"/devices/{device['id']}/restore", json={"owner_id": successor.id}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
