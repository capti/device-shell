"""Возврат устройства и отчёт о состоянии при возврате."""

from datetime import timedelta

from fastapi.testclient import TestClient
from helpers import checkout, create_device, login_as, register_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Checkout, ConditionReport, Device, DeviceEvent


def test_holder_returns_device(client: TestClient, make_user, db: Session) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], holder)

    client.cookies.clear()
    login_as(client, holder)
    response = client.post(
        f"/devices/{device['id']}/return",
        json={"condition_in": "scratches", "comment_in": "Царапина на корпусе"},
    )

    assert response.status_code == 200
    card = response.json()
    assert card["holder"]["id"] == owner.id
    assert card["overdue"] is False
    stored = db.get(Device, device["id"])
    assert stored.status == "active"
    closed = db.scalar(
        select(Checkout).where(Checkout.device_id == device["id"])
    )
    assert closed.returned_at is not None
    assert closed.closed_reason == "returned"
    assert closed.condition_in == "scratches"
    assert closed.comment_in == "Царапина на корпусе"
    event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"], DeviceEvent.type == "returned"
        )
    )
    assert event is not None
    assert event.actor_id == holder.id
    assert event.payload["condition"] == "scratches"


def test_return_creates_condition_report(
    client: TestClient, make_user, db: Session
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    checkout(client, device["id"], holder)

    client.cookies.clear()
    login_as(client, holder)
    response = client.post(
        f"/devices/{device['id']}/return",
        json={"condition_in": "damaged", "requires_repair": True},
    )

    assert response.status_code == 200
    report = db.scalar(
        select(ConditionReport).where(ConditionReport.device_id == device["id"])
    )
    assert report is not None
    assert report.checkout_id is not None
    assert report.author_id == holder.id
    assert report.condition == "damaged"
    assert report.requires_repair is True
    assert db.get(Device, device["id"]).status == "active"


def test_return_without_condition_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    checkout(client, device["id"], holder)

    client.cookies.clear()
    login_as(client, holder)
    response = client.post(f"/devices/{device['id']}/return", json={})

    assert response.status_code == 422


def test_return_without_active_checkout_is_rejected(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    response = client.post(
        f"/devices/{device['id']}/return", json={"condition_in": "ok"}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "NO_ACTIVE_CHECKOUT"


def test_stranger_cannot_return_device(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    stranger = register_user(make_user, username="stranger")
    device = create_device(client)
    checkout(client, device["id"], holder)

    client.cookies.clear()
    login_as(client, stranger)
    response = client.post(
        f"/devices/{device['id']}/return", json={"condition_in": "ok"}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_owner_closes_forgotten_checkout(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    checkout(client, device["id"], holder)

    response = client.post(
        f"/devices/{device['id']}/return", json={"condition_in": "not_working"}
    )

    assert response.status_code == 200
    assert response.json()["holder"]["id"] == response.json()["owner"]["id"]


def test_return_clears_overdue(client: TestClient, make_user, db: Session) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    checkout(client, device["id"], holder)
    stored = db.scalar(select(Checkout).where(Checkout.device_id == device["id"]))
    stored.expected_return_at = now_local() - timedelta(days=3)
    db.commit()
    assert client.get("/devices", params={"overdue": "true"}).json()["total"] == 1

    client.cookies.clear()
    login_as(client, holder)
    response = client.post(
        f"/devices/{device['id']}/return", json={"condition_in": "ok"}
    )

    assert response.status_code == 200
    assert response.json()["overdue"] is False
    assert client.get("/devices", params={"overdue": "true"}).json()["total"] == 0


def test_admin_returns_holder_device(client: TestClient, make_user) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    checkout(client, device["id"], holder)

    client.cookies.clear()
    login_as(client, admin)
    response = client.post(
        f"/devices/{device['id']}/return", json={"condition_in": "ok"}
    )

    assert response.status_code == 200
