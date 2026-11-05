"""Передача устройства между держателями."""

from fastapi.testclient import TestClient
from helpers import checkout, create_device, login_as, register_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Checkout, ConditionReport, DeviceEvent


def test_holder_transfers_device(client: TestClient, make_user, db: Session) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    receiver = register_user(make_user, username="receiver")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], holder)

    client.cookies.clear()
    login_as(client, holder)
    response = client.post(
        f"/devices/{device['id']}/transfer",
        json={"holder_id": receiver.id, "condition_in": "ok"},
    )

    assert response.status_code == 200
    card = response.json()
    assert card["holder"]["id"] == receiver.id
    assert card["owner"]["id"] == owner.id
    checkouts = db.scalars(
        select(Checkout)
        .where(Checkout.device_id == device["id"])
        .order_by(Checkout.id)
    ).all()
    assert len(checkouts) == 2
    assert checkouts[0].closed_reason == "transferred"
    assert checkouts[0].condition_in == "ok"
    assert checkouts[1].user_id == receiver.id
    assert checkouts[1].condition_out == "ok"
    assert checkouts[1].returned_at is None
    event = db.scalar(
        select(DeviceEvent).where(
            DeviceEvent.device_id == device["id"], DeviceEvent.type == "transferred"
        )
    )
    assert event is not None
    assert event.payload["from_holder_id"] == holder.id
    assert event.payload["to_holder_id"] == receiver.id


def test_owner_transfers_checked_out_device(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    receiver = register_user(make_user, username="receiver")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], holder)

    response = client.post(
        f"/devices/{device['id']}/transfer", json={"holder_id": receiver.id}
    )

    assert response.status_code == 200
    assert response.json()["holder"]["id"] == receiver.id
    assert (
        db.scalar(
            select(ConditionReport).where(
                ConditionReport.device_id == device["id"]
            )
        )
        is None
    )


def test_transfer_without_checkout_is_rejected(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    receiver = register_user(make_user, username="receiver")
    device = create_device(client)

    response = client.post(
        f"/devices/{device['id']}/transfer", json={"holder_id": receiver.id}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "NO_ACTIVE_CHECKOUT"


def test_transfer_to_same_holder_is_rejected(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    device = create_device(client)
    checkout(client, device["id"], holder)

    response = client.post(
        f"/devices/{device['id']}/transfer", json={"holder_id": holder.id}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "SAME_HOLDER"


def test_transfer_to_owner_is_rejected(client: TestClient, make_user) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], holder)

    response = client.post(
        f"/devices/{device['id']}/transfer", json={"holder_id": owner.id}
    )

    assert response.status_code == 409
    assert response.json()["code"] == "SELF_CHECKOUT"


def test_transfer_to_inactive_user_is_rejected(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    inactive = register_user(make_user, username="inactive", is_active=False)
    device = create_device(client)
    checkout(client, device["id"], holder)

    response = client.post(
        f"/devices/{device['id']}/transfer", json={"holder_id": inactive.id}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "HOLDER_INACTIVE"


def test_stranger_cannot_transfer_device(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    receiver = register_user(make_user, username="receiver")
    stranger = register_user(make_user, username="stranger")
    device = create_device(client)
    checkout(client, device["id"], holder)

    client.cookies.clear()
    login_as(client, stranger)
    response = client.post(
        f"/devices/{device['id']}/transfer", json={"holder_id": receiver.id}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_transfer_creates_report_for_previous_checkout(
    client: TestClient, make_user, db: Session
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    holder = register_user(make_user, username="holder")
    receiver = register_user(make_user, username="receiver")
    device = create_device(client)
    checkout(client, device["id"], holder)

    client.cookies.clear()
    login_as(client, holder)
    response = client.post(
        f"/devices/{device['id']}/transfer",
        json={"holder_id": receiver.id, "condition_in": "scratches"},
    )

    assert response.status_code == 200
    report = db.scalar(
        select(ConditionReport).where(ConditionReport.device_id == device["id"])
    )
    assert report is not None
    assert report.condition == "scratches"
    assert report.author_id == holder.id
    previous = db.scalar(
        select(Checkout).where(
            Checkout.device_id == device["id"], Checkout.returned_at.is_not(None)
        )
    )
    assert previous is not None
    assert report.checkout_id == previous.id
