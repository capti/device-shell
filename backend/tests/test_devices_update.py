"""Редактирование устройства и запрет удаления."""

from fastapi.testclient import TestClient
from helpers import create_device, login_as, register_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DeviceEvent


def test_owner_updates_own_device(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)

    response = client.patch(
        f"/devices/{device['id']}", json={"model": "Pixel 9", "notes": "экран заменён"}
    )

    assert response.status_code == 200
    assert response.json()["model"] == "Pixel 9"
    assert response.json()["notes"] == "экран заменён"
    event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"], DeviceEvent.type == "updated"
        )
    )
    assert event is not None
    assert event.actor_id == owner.id
    assert event.payload["changes"]["model"] == {"from": "Galaxy S23", "to": "Pixel 9"}


def test_update_without_changes_writes_no_event(
    client: TestClient, make_user, db: Session
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    response = client.patch(f"/devices/{device['id']}", json={"model": "Galaxy S23"})

    assert response.status_code == 200
    events = db.scalars(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"], DeviceEvent.type == "updated"
        )
    ).all()
    assert events == []


def test_user_cannot_update_foreign_device(client: TestClient, make_user) -> None:
    owner = register_user(make_user, username="owner")
    stranger = register_user(make_user, username="stranger")
    login_as(client, owner)
    device = create_device(client)

    client.cookies.clear()
    login_as(client, stranger)
    response = client.patch(f"/devices/{device['id']}", json={"model": "Pixel 9"})

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_admin_updates_foreign_device(client: TestClient, make_user) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)

    client.cookies.clear()
    login_as(client, admin)
    response = client.patch(f"/devices/{device['id']}", json={"color": "black"})

    assert response.status_code == 200
    assert response.json()["color"] == "black"


def test_archived_device_is_read_only(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    assert client.post(f"/devices/{device['id']}/archive").status_code == 200

    response = client.patch(f"/devices/{device['id']}", json={"model": "Pixel 9"})

    assert response.status_code == 409
    assert response.json()["code"] == "DEVICE_ARCHIVED"


def test_update_rejects_duplicate_imei(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    create_device(client, inventory_no="QA-PH-001", imei="356938035643809")
    device = create_device(client, inventory_no="QA-PH-002")

    response = client.patch(
        f"/devices/{device['id']}", json={"imei": "356938035643809"}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "IMEI_TAKEN"


def test_update_rejects_empty_inventory_number(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    response = client.patch(f"/devices/{device['id']}", json={"inventory_no": ""})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_update_rejects_owner_field(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    response = client.patch(f"/devices/{device['id']}", json={"owner_id": 1})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_physical_delete_is_forbidden(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    response = client.delete(f"/devices/{device['id']}")

    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"
    assert "архив" in response.json()["message"]
