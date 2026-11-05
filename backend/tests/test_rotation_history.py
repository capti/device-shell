"""Сквозные сценарии оборота: история и единая формула просрочки."""

from datetime import timedelta

from fastapi.testclient import TestClient
from helpers import checkout, create_device, login_as, register_user
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Checkout


def test_rotation_events_reach_device_history(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    receiver = register_user(make_user, username="receiver")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], holder)

    client.cookies.clear()
    login_as(client, holder)
    client.post(
        f"/devices/{device['id']}/transfer",
        json={"holder_id": receiver.id, "condition_in": "ok"},
    )

    client.cookies.clear()
    login_as(client, receiver)
    client.post(f"/devices/{device['id']}/return", json={"condition_in": "ok"})

    client.cookies.clear()
    login_as(client, owner)
    client.post(f"/devices/{device['id']}/owner", json={"owner_id": receiver.id})

    client.cookies.clear()
    login_as(client, receiver)
    repair = client.post(
        f"/devices/{device['id']}/repairs", json={"service": "Сервис"}
    ).json()
    client.post(f"/devices/{device['id']}/repairs/{repair['id']}/finish", json={})
    client.post(f"/devices/{device['id']}/status", json={"status": "lost"})
    client.post(
        f"/devices/{device['id']}/status",
        json={"status": "active", "comment": "Нашёлся"},
    )

    response = client.get(f"/devices/{device['id']}/history")

    assert response.status_code == 200
    types = [event["type"] for event in response.json()]
    for expected in (
        "checked_out",
        "transferred",
        "returned",
        "owner_changed",
        "repair_started",
        "repair_finished",
        "status_changed",
    ):
        assert expected in types
    assert all(event["actor"] is not None for event in response.json())


def test_overdue_matches_between_list_and_card(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], holder)
    active = db.scalar(select(Checkout).where(Checkout.device_id == device["id"]))
    active.expected_return_at = now_local() - timedelta(days=1)
    db.commit()

    listed = client.get("/devices", params={"overdue": "true"}).json()["items"]
    card = client.get(f"/devices/{device['id']}").json()

    assert len(listed) == 1
    assert listed[0]["id"] == card["id"] == device["id"]
    assert listed[0]["overdue"] is card["overdue"] is True
    assert listed[0]["holder"]["id"] == card["holder"]["id"] == holder.id
    assert listed[0]["owner"]["id"] == owner.id
