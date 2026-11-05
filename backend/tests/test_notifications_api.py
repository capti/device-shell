"""API уведомлений: список, счётчик, прочтение и чужие записи."""

from datetime import timedelta

from fastapi.testclient import TestClient
from helpers import (
    add_checkout,
    checkout,
    create_device,
    login_as,
    notifications,
    register_user,
)
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Device, Notification


def _add_notification(db: Session, recipient_id: int, type_: str = "device_lost"):
    notification = Notification(recipient_id=recipient_id, type=type_)
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def test_endpoints_require_authentication(client: TestClient) -> None:
    assert client.get("/notifications").status_code == 401
    assert client.post("/notifications/read-all").status_code == 401
    assert client.post("/notifications/1/read").status_code == 401


def test_list_returns_own_notifications_with_unread_counter(
    client: TestClient, make_user, db: Session
) -> None:
    register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], holder)

    response = client.get("/notifications")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["unread"] == 1
    assert body["page"] == 1
    item = body["items"][0]
    assert item["type"] == "device_checked_out"
    assert item["device_id"] == device["id"]
    assert item["actor"]["id"] == owner.id
    assert item["read_at"] is None

    client.cookies.clear()
    login_as(client, holder)
    empty = client.get("/notifications").json()
    assert empty["items"] == []
    assert empty["total"] == 0
    assert empty["unread"] == 0


def test_pagination_keeps_total_and_unread(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    for index in range(1, 4):
        device = create_device(client, inventory_no=f"QA-PH-00{index}")
        checkout(client, device["id"], holder)

    first_page = client.get("/notifications", params={"page": 1, "page_size": 2}).json()
    second_page = client.get(
        "/notifications", params={"page": 2, "page_size": 2}
    ).json()

    assert len(first_page["items"]) == 2
    assert len(second_page["items"]) == 1
    assert first_page["total"] == second_page["total"] == 3
    assert first_page["unread"] == second_page["unread"] == 3


def test_read_notification_marks_it_read(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], holder)
    created = client.get("/notifications").json()["items"][0]

    response = client.post(f"/notifications/{created['id']}/read")

    assert response.status_code == 200
    first_read_at = response.json()["read_at"]
    assert first_read_at is not None
    page = client.get("/notifications").json()
    assert page["total"] == 1
    assert page["unread"] == 0
    repeated = client.post(f"/notifications/{created['id']}/read")
    assert repeated.json()["read_at"] == first_read_at


def test_read_foreign_or_unknown_notification_is_404(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    foreign = _add_notification(db, admin.id)
    login_as(client, owner)

    response = client.post(f"/notifications/{foreign.id}/read")
    unknown = client.post("/notifications/999999/read")

    assert response.status_code == 404
    assert response.json()["code"] == "NOTIFICATION_NOT_FOUND"
    assert unknown.status_code == 404
    db.refresh(foreign)
    assert foreign.read_at is None


def test_read_all_marks_only_own_notifications(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    foreign = _add_notification(db, admin.id)
    login_as(client, owner)
    for index in (1, 2):
        device = create_device(client, inventory_no=f"QA-PH-00{index}")
        checkout(client, device["id"], holder)

    response = client.post("/notifications/read-all")

    assert response.status_code == 200
    assert response.json() == {"updated": 2}
    assert client.get("/notifications").json()["unread"] == 0
    db.refresh(foreign)
    assert foreign.read_at is None


def test_read_all_returns_zero_when_nothing_unread(
    client: TestClient, make_user
) -> None:
    owner = register_user(make_user, username="owner")
    login_as(client, owner)

    response = client.post("/notifications/read-all")

    assert response.status_code == 200
    assert response.json() == {"updated": 0}

def test_list_purges_expired_notifications(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    stale = Notification(
        recipient_id=owner.id,
        type="owner_changed",
        created_at=now_local() - timedelta(days=91),
    )
    db.add(stale)
    db.commit()
    login_as(client, owner)

    body = client.get("/notifications").json()

    assert body["items"] == []
    assert body["total"] == 0
    assert notifications(db, recipient_id=owner.id) == []


def test_list_materializes_overdue_notifications(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    device_row = db.get(Device, device["id"])
    add_checkout(
        db, device_row, holder, expected_return_at=now_local() - timedelta(days=2)
    )

    first = client.get("/notifications").json()
    second = client.get("/notifications").json()

    overdue = [item for item in first["items"] if item["type"] == "checkout_overdue"]
    assert len(overdue) == 1
    assert overdue[0]["device_id"] == device_row.id
    stored = notifications(db, type_="checkout_overdue")
    assert {item.recipient_id for item in stored} == {owner.id, admin.id}
    assert second["total"] == first["total"]
