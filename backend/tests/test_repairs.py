"""Журнал ремонтов устройства."""

from datetime import timedelta

from fastapi.testclient import TestClient
from helpers import checkout, create_device, login_as, register_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Device, DeviceEvent, Repair


def _start(client: TestClient, device_id: int, **payload) -> dict:
    response = client.post(f"/devices/{device_id}/repairs", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_start_repair(client: TestClient, make_user, db: Session) -> None:
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)

    repair = _start(
        client,
        device["id"],
        service="Официальный сервис",
        description="Замена экрана",
        cost="12000.00",
        comment="Разбит при падении",
    )

    assert repair["device_id"] == device["id"]
    assert repair["returned_at"] is None
    assert repair["created_by"]["id"] == owner.id
    assert db.get(Device, device["id"]).status == "repair"
    event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"],
            DeviceEvent.type == "repair_started",
        )
    )
    assert event is not None
    assert event.payload["repair_id"] == repair["id"]


def test_device_in_repair_cannot_be_checked_out(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    _start(client, device["id"], service="Сервис")

    response = client.post(
        f"/devices/{device['id']}/checkout", json={"holder_id": holder.id}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "DEVICE_UNAVAILABLE"


def test_repair_with_active_checkout_is_rejected(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    checkout(client, device["id"], holder)

    response = client.post(
        f"/devices/{device['id']}/repairs", json={"service": "Сервис"}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "ACTIVE_CHECKOUT"


def test_lost_device_cannot_be_sent_to_repair(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    assert (
        client.post(
            f"/devices/{device['id']}/status", json={"status": "lost"}
        ).status_code
        == 200
    )

    response = client.post(
        f"/devices/{device['id']}/repairs", json={"service": "Сервис"}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "DEVICE_UNAVAILABLE"


def test_stranger_cannot_start_repair(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    stranger = register_user(make_user, username="stranger")
    device = create_device(client)

    client.cookies.clear()
    login_as(client, stranger)
    response = client.post(
        f"/devices/{device['id']}/repairs", json={"service": "Сервис"}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_admin_can_start_repair(client: TestClient, make_user) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    client.cookies.clear()
    login_as(client, admin)
    response = client.post(
        f"/devices/{device['id']}/repairs", json={"service": "Сервис"}
    )

    assert response.status_code == 201


def test_finish_repair_returns_device_to_service(
    client: TestClient, make_user, db: Session
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    repair = _start(client, device["id"], service="Сервис")

    response = client.post(
        f"/devices/{device['id']}/repairs/{repair['id']}/finish",
        json={"comment": "Экран заменён"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["returned_at"] is not None
    assert payload["comment"] == "Экран заменён"
    assert db.get(Device, device["id"]).status == "active"
    event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"],
            DeviceEvent.type == "repair_finished",
        )
    )
    assert event is not None
    assert (
        client.post(
            f"/devices/{device['id']}/checkout", json={"holder_id": holder.id}
        ).status_code
        == 200
    )


def test_finish_unknown_repair_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    response = client.post(f"/devices/{device['id']}/repairs/9999/finish", json={})

    assert response.status_code == 404
    assert response.json()["code"] == "REPAIR_NOT_FOUND"


def test_finish_foreign_repair_is_rejected(
    client: TestClient, make_user, db: Session
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    first = create_device(client, inventory_no="QA-PH-001")
    second = create_device(client, inventory_no="QA-PH-002")
    repair = _start(client, second["id"], service="Сервис")

    response = client.post(
        f"/devices/{first['id']}/repairs/{repair['id']}/finish", json={}
    )

    assert response.status_code == 404
    assert response.json()["code"] == "REPAIR_NOT_FOUND"
    assert db.get(Device, second["id"]).status == "repair"


def test_finish_repair_twice_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    repair = _start(client, device["id"], service="Сервис")
    assert (
        client.post(
            f"/devices/{device['id']}/repairs/{repair['id']}/finish", json={}
        ).status_code
        == 200
    )

    response = client.post(
        f"/devices/{device['id']}/repairs/{repair['id']}/finish", json={}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "REPAIR_ALREADY_FINISHED"


def test_finish_before_start_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    repair = _start(client, device["id"], service="Сервис")

    response = client.post(
        f"/devices/{device['id']}/repairs/{repair['id']}/finish",
        json={"returned_at": (now_local() - timedelta(days=1)).isoformat()},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_repair_journal_orders_newest_first(
    client: TestClient, make_user, db: Session
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    first = _start(client, device["id"], service="Первый")
    client.post(f"/devices/{device['id']}/repairs/{first['id']}/finish", json={})
    second = _start(client, device["id"], service="Второй")

    response = client.get(f"/devices/{device['id']}/repairs")

    assert response.status_code == 200
    services = [item["service"] for item in response.json()]
    assert services == ["Второй", "Первый"]
    assert response.json()[0]["id"] == second["id"]
    assert db.scalar(select(Repair).where(Repair.id == first["id"])) is not None


def test_repair_journal_requires_session(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    client.cookies.clear()

    response = client.get(f"/devices/{device['id']}/repairs")

    assert response.status_code == 401
