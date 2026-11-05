"""Отчёты о состоянии устройства."""

from fastapi.testclient import TestClient
from helpers import checkout, create_device, login_as, register_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ConditionReport, Device, DeviceEvent


def _report(client: TestClient, device_id: int, **payload) -> dict:
    response = client.post(f"/devices/{device_id}/condition-reports", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_holder_reports_without_returning(
    client: TestClient, make_user, db: Session
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    checkout(client, device["id"], holder)

    client.cookies.clear()
    login_as(client, holder)
    report = _report(
        client,
        device["id"],
        condition="scratches",
        comment="Появилась царапина",
    )

    assert report["author"]["id"] == holder.id
    assert report["checkout_id"] is not None
    assert report["condition"] == "scratches"
    active = client.get(f"/devices/{device['id']}/checkouts").json()[0]
    assert active["closed_reason"] is None
    assert db.get(Device, device["id"]).status == "active"
    event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"],
            DeviceEvent.type == "condition_reported",
        )
    )
    assert event is not None
    assert event.payload["report_id"] == report["id"]


def test_owner_reports_without_checkout(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)

    report = _report(client, device["id"], condition="ok")

    assert report["checkout_id"] is None
    assert report["author"]["id"] == owner.id
    stored = db.scalar(
        select(ConditionReport).where(ConditionReport.id == report["id"])
    )
    assert stored is not None


def test_requires_repair_keeps_device_status(
    client: TestClient, make_user, db: Session
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    report = _report(
        client, device["id"], condition="damaged", requires_repair=True
    )

    assert report["requires_repair"] is True
    assert db.get(Device, device["id"]).status == "active"


def test_invalid_condition_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)

    response = client.post(
        f"/devices/{device['id']}/condition-reports", json={"condition": "broken"}
    )

    assert response.status_code == 422


def test_stranger_cannot_report(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    stranger = register_user(make_user, username="stranger")
    device = create_device(client)

    client.cookies.clear()
    login_as(client, stranger)
    response = client.post(
        f"/devices/{device['id']}/condition-reports", json={"condition": "ok"}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_archived_device_cannot_be_reported(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    assert client.post(f"/devices/{device['id']}/archive").status_code == 200

    response = client.post(
        f"/devices/{device['id']}/condition-reports", json={"condition": "ok"}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "DEVICE_ARCHIVED"


def test_reports_are_ordered_newest_first(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    first = _report(client, device["id"], condition="ok")
    second = _report(client, device["id"], condition="scratches")

    response = client.get(f"/devices/{device['id']}/condition-reports")

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [second["id"], first["id"]]


def test_reports_require_session(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    client.cookies.clear()

    response = client.get(f"/devices/{device['id']}/condition-reports")

    assert response.status_code == 401
