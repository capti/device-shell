"""Выдача устройства и история выдач."""

from datetime import timedelta

from fastapi.testclient import TestClient
from helpers import checkout, create_device, login_as, register_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Checkout, Device, DeviceEvent


def _expected_default() -> str:
    return (now_local() + timedelta(days=14)).date().isoformat()


def test_owner_checks_out_device(client: TestClient, make_user, db: Session) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder", full_name="Мария Сидорова")
    login_as(client, owner)
    device = create_device(client)

    card = checkout(client, device["id"], holder)

    assert card["holder"]["id"] == holder.id
    assert card["owner"]["id"] == owner.id
    assert card["expected_return_at"].startswith(_expected_default())
    assert card["overdue"] is False
    event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"],
            DeviceEvent.type == "checked_out",
        )
    )
    assert event is not None
    assert event.actor_id == owner.id
    assert event.payload["holder_id"] == holder.id


def test_explicit_return_date_is_kept(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    expected = (now_local() + timedelta(days=3)).date().isoformat()

    card = checkout(client, device["id"], holder, expected_return_at=expected)

    assert card["expected_return_at"].startswith(expected)


def test_return_date_today_is_allowed(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    today = now_local().date().isoformat()

    card = checkout(client, device["id"], holder, expected_return_at=today)

    assert card["expected_return_at"].startswith(today)
    assert card["overdue"] is False


def test_self_checkout_is_rejected(client: TestClient, make_user, db: Session) -> None:
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)

    response = client.post(
        f"/devices/{device['id']}/checkout", json={"holder_id": owner.id}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "SELF_CHECKOUT"
    assert db.scalar(select(Checkout)) is None


def test_second_checkout_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    first = register_user(make_user, username="first")
    second = register_user(make_user, username="second")
    device = create_device(client)
    checkout(client, device["id"], first)

    response = client.post(
        f"/devices/{device['id']}/checkout", json={"holder_id": second.id}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "ALREADY_CHECKED_OUT"


def test_archived_device_cannot_be_checked_out(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    assert client.post(f"/devices/{device['id']}/archive").status_code == 200

    response = client.post(
        f"/devices/{device['id']}/checkout", json={"holder_id": holder.id}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "DEVICE_ARCHIVED"


def test_repair_and_lost_devices_are_unavailable(
    client: TestClient, make_user, db: Session
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    repair = create_device(client, inventory_no="QA-PH-001")
    lost = create_device(client, inventory_no="QA-PH-002")
    db.get(Device, repair["id"]).status = "repair"
    db.get(Device, lost["id"]).status = "lost"
    db.commit()

    repair_response = client.post(
        f"/devices/{repair['id']}/checkout", json={"holder_id": holder.id}
    )
    lost_response = client.post(
        f"/devices/{lost['id']}/checkout", json={"holder_id": holder.id}
    )

    assert repair_response.status_code == 409
    assert repair_response.json()["code"] == "DEVICE_UNAVAILABLE"
    assert lost_response.status_code == 409
    assert lost_response.json()["code"] == "DEVICE_UNAVAILABLE"


def test_inactive_holder_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    inactive = register_user(make_user, username="inactive", is_active=False)
    device = create_device(client)

    response = client.post(
        f"/devices/{device['id']}/checkout", json={"holder_id": inactive.id}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "HOLDER_INACTIVE"


def test_unknown_holder_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    response = client.post(
        f"/devices/{device['id']}/checkout", json={"holder_id": 9999}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "HOLDER_INACTIVE"


def test_stranger_cannot_check_out_device(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    stranger = register_user(make_user, username="stranger")
    holder = register_user(make_user, username="holder")
    device = create_device(client)

    client.cookies.clear()
    login_as(client, stranger)
    response = client.post(
        f"/devices/{device['id']}/checkout", json={"holder_id": holder.id}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_admin_checks_out_foreign_device(client: TestClient, make_user) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)

    client.cookies.clear()
    login_as(client, admin)
    response = client.post(
        f"/devices/{device['id']}/checkout", json={"holder_id": holder.id}
    )

    assert response.status_code == 200
    assert response.json()["holder"]["id"] == holder.id


def test_past_return_date_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    yesterday = (now_local() - timedelta(days=1)).date().isoformat()

    response = client.post(
        f"/devices/{device['id']}/checkout",
        json={"holder_id": holder.id, "expected_return_at": yesterday},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_checkout_requires_session(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    client.cookies.clear()

    response = client.post(
        f"/devices/{device['id']}/checkout", json={"holder_id": holder.id}
    )

    assert response.status_code == 401


def test_checkout_unknown_device(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")

    response = client.post("/devices/9999/checkout", json={"holder_id": holder.id})

    assert response.status_code == 404
    assert response.json()["code"] == "DEVICE_NOT_FOUND"


def test_checkout_history_orders_newest_first(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    first = register_user(make_user, username="first")
    second = register_user(make_user, username="second")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], first)
    assert (
        client.post(
            f"/devices/{device['id']}/return", json={"condition_in": "ok"}
        ).status_code
        == 200
    )
    checkout(client, device["id"], second)

    response = client.get(f"/devices/{device['id']}/checkouts")

    assert response.status_code == 200
    payload = response.json()
    assert [item["holder"]["id"] for item in payload] == [second.id, first.id]
    assert payload[1]["closed_reason"] == "returned"
    assert payload[1]["returned_at"] is not None
    assert payload[0]["closed_reason"] is None


def test_checkout_history_requires_session(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    client.cookies.clear()

    response = client.get(f"/devices/{device['id']}/checkouts")

    assert response.status_code == 401
