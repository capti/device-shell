"""Деактивация и активация сотрудников, автоархив устройств."""

from fastapi.testclient import TestClient
from helpers import add_checkout, login_as, register_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Device, DeviceEvent


def _archived_events(db: Session, device_id: int) -> list[DeviceEvent]:
    return list(
        db.scalars(
            select(DeviceEvent).where(
                DeviceEvent.device_id == device_id,
                DeviceEvent.type == "archived",
            )
        ).all()
    )


def test_deactivate_archives_devices_and_closes_access(
    client: TestClient, make_client, make_user, make_device, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target")
    active = make_device(owner=target, inventory_no="QA-PH-001")
    in_repair = make_device(
        owner=target, inventory_no="QA-PH-002", status="repair"
    )
    archived = make_device(owner=target, inventory_no="QA-PH-003")
    archived.archived_at = now_local()
    db.commit()

    login_as(client, admin)
    response = client.post(f"/users/{target.id}/deactivate")

    assert response.status_code == 200
    body = response.json()
    assert body["is_active"] is False
    assert body["devices_owned"] == 3

    db.expire_all()
    assert db.get(Device, active.id).archived_at is not None
    assert db.get(Device, in_repair.id).archived_at is not None
    assert db.get(Device, in_repair.id).status == "repair"
    assert db.get(Device, archived.id).archived_at is not None
    assert len(_archived_events(db, active.id)) == 1
    event = _archived_events(db, active.id)[0]
    assert event.actor_id == admin.id
    assert event.payload == {"reason": "owner_deactivated"}

    other = make_client()
    login = other.post(
        "/auth/login", json={"username": "target", "password": "secret123"}
    )
    assert login.status_code == 401


def test_deactivate_blocked_when_owned_device_is_checked_out(
    client: TestClient, make_user, make_device, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target")
    colleague = register_user(make_user, username="colleague")
    device = make_device(owner=target, inventory_no="QA-PH-007")
    add_checkout(db, device, colleague)

    login_as(client, admin)
    response = client.post(f"/users/{target.id}/deactivate")

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "HAS_DEVICES"
    assert "QA-PH-007" in body["message"]

    db.expire_all()
    assert db.get(Device, device.id).archived_at is None
    assert db.get(Device, device.id).owner_id == target.id


def test_deactivate_blocked_when_holding_foreign_device(
    client: TestClient, make_user, make_device, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target")
    colleague = register_user(make_user, username="colleague")
    device = make_device(owner=colleague, inventory_no="QA-PH-008")
    add_checkout(db, device, target)

    login_as(client, admin)
    response = client.post(f"/users/{target.id}/deactivate")

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "HAS_DEVICES"
    assert "QA-PH-008" in body["message"]


def test_deactivate_twice_conflicts(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target", is_active=False)
    login_as(client, admin)

    response = client.post(f"/users/{target.id}/deactivate")

    assert response.status_code == 409
    assert response.json()["code"] == "ALREADY_INACTIVE"


def test_cannot_deactivate_last_admin(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, admin)

    response = client.post(f"/users/{admin.id}/deactivate")

    assert response.status_code == 409
    assert response.json()["code"] == "LAST_ADMIN"
    assert client.get(f"/users/{admin.id}").json()["is_active"] is True


def test_can_deactivate_admin_when_another_exists(
    client: TestClient, make_user
) -> None:
    first = register_user(make_user, username="first", role="admin")
    second = register_user(make_user, username="second", role="admin")
    login_as(client, first)

    response = client.post(f"/users/{second.id}/deactivate")

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_activate_restores_access_but_not_devices(
    client: TestClient, make_user, make_device, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target")
    device = make_device(owner=target, inventory_no="QA-PH-001")

    login_as(client, admin)
    client.post(f"/users/{target.id}/deactivate")
    response = client.post(f"/users/{target.id}/activate")

    assert response.status_code == 200
    assert response.json()["is_active"] is True

    db.expire_all()
    assert db.get(Device, device.id).archived_at is not None

    login = client.post(
        "/auth/login", json={"username": "target", "password": "secret123"}
    )
    assert login.status_code == 200


def test_activate_twice_conflicts(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target")
    login_as(client, admin)

    response = client.post(f"/users/{target.id}/activate")

    assert response.status_code == 409
    assert response.json()["code"] == "ALREADY_ACTIVE"


def test_regular_user_cannot_change_activity(
    client: TestClient, make_user
) -> None:
    user = register_user(make_user, username="plain")
    target = register_user(make_user, username="target")
    login_as(client, user)

    assert client.post(f"/users/{target.id}/deactivate").status_code == 403
    assert client.post(f"/users/{target.id}/activate").status_code == 403


def test_deactivate_unknown_user(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, admin)

    response = client.post("/users/9999/deactivate")

    assert response.status_code == 404
    assert response.json()["code"] == "USER_NOT_FOUND"


def test_activation_unknown_user(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, admin)

    response = client.post("/users/9999/activate")

    assert response.status_code == 404
    assert response.json()["code"] == "USER_NOT_FOUND"
