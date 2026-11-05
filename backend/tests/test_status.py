"""Статусы lost и active."""

from fastapi.testclient import TestClient
from helpers import create_device, login_as, register_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Device, DeviceEvent


def _set_status(client: TestClient, device_id: int, status: str, **extra):
    return client.post(
        f"/devices/{device_id}/status", json={"status": status, **extra}
    )


def test_mark_device_lost(client: TestClient, make_user, db: Session) -> None:
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)

    response = _set_status(client, device["id"], "lost", comment="Потерян в офисе")

    assert response.status_code == 200
    assert response.json()["status"] == "lost"
    event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"],
            DeviceEvent.type == "status_changed",
        )
    )
    assert event is not None
    assert event.payload == {"from": "active", "to": "lost", "comment": "Потерян в офисе"}


def test_lost_device_cannot_be_checked_out(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    _set_status(client, device["id"], "lost")

    response = client.post(
        f"/devices/{device['id']}/checkout", json={"holder_id": holder.id}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "DEVICE_UNAVAILABLE"


def test_return_from_lost_requires_comment(
    client: TestClient, make_user, db: Session
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    _set_status(client, device["id"], "lost")

    response = _set_status(client, device["id"], "active")

    assert response.status_code == 422
    assert response.json()["code"] == "COMMENT_REQUIRED"
    assert db.get(Device, device["id"]).status == "lost"


def test_return_from_lost_with_comment(client: TestClient, make_user, db: Session) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    _set_status(client, device["id"], "lost")

    response = _set_status(client, device["id"], "active", comment="Нашёлся в переговорке")

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    event = db.scalar(
        select(DeviceEvent)
        .where(DeviceEvent.device_id == device["id"])
        .order_by(DeviceEvent.id.desc())
    )
    assert event is not None
    assert event.payload == {
        "from": "lost",
        "to": "active",
        "comment": "Нашёлся в переговорке",
    }


def test_active_to_active_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    response = _set_status(client, device["id"], "active", comment="не нужно")

    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATUS_TRANSITION"


def test_repair_to_lost_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    assert (
        client.post(f"/devices/{device['id']}/repairs", json={"service": "Сервис"}).status_code
        == 201
    )

    response = _set_status(client, device["id"], "lost")

    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_STATUS_TRANSITION"


def test_stranger_cannot_change_status(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    stranger = register_user(make_user, username="stranger")
    device = create_device(client)

    client.cookies.clear()
    login_as(client, stranger)
    response = _set_status(client, device["id"], "lost")

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_archived_device_status_cannot_change(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    assert client.post(f"/devices/{device['id']}/archive").status_code == 200

    response = _set_status(client, device["id"], "lost")

    assert response.status_code == 409
    assert response.json()["code"] == "DEVICE_ARCHIVED"


def test_status_requires_session(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    client.cookies.clear()

    response = _set_status(client, device["id"], "lost")

    assert response.status_code == 401


def test_invalid_status_value_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    response = client.post(
        f"/devices/{device['id']}/status", json={"status": "repair"}
    )

    assert response.status_code == 422
