"""Справочник сотрудников: чтение, счётчики и скрытие деактивированных."""

from fastapi.testclient import TestClient
from helpers import add_checkout, login_as, register_user
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Device


def test_users_require_session(client: TestClient) -> None:
    assert client.get("/users").status_code == 401
    assert client.get("/users/1").status_code == 401


def test_list_users_hides_inactive_by_default(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    register_user(make_user, username="active")
    gone = register_user(make_user, username="gone", is_active=False)

    login_as(client, admin)

    usernames = [user["username"] for user in client.get("/users").json()]
    assert "active" in usernames
    assert "admin" in usernames
    assert "gone" not in usernames

    all_users = client.get("/users", params={"include_inactive": "true"}).json()
    inactive = next(user for user in all_users if user["id"] == gone.id)
    assert inactive["is_active"] is False


def test_list_users_counts_owned_and_held(
    client: TestClient, make_user, make_device, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    colleague = register_user(make_user, username="colleague")

    make_device(owner=owner, inventory_no="QA-PH-001")
    archived = make_device(owner=owner, inventory_no="QA-PH-002")
    archived.archived_at = now_local()
    db.commit()
    foreign = make_device(owner=colleague, inventory_no="QA-PH-003")
    add_checkout(db, foreign, owner)

    login_as(client, admin)
    rows = {user["id"]: user for user in client.get("/users").json()}

    assert rows[owner.id]["devices_owned"] == 2
    assert rows[owner.id]["devices_held"] == 1
    assert rows[holder.id]["devices_owned"] == 0
    assert rows[holder.id]["devices_held"] == 0
    assert rows[colleague.id]["devices_owned"] == 1


def test_user_card_returns_profile_and_counters(
    client: TestClient, make_user, make_device
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(
        make_user,
        username="owner",
        full_name="Иван Петров",
    )
    make_device(owner=owner, inventory_no="QA-PH-001")

    login_as(client, admin)
    card = client.get(f"/users/{owner.id}").json()

    assert card["username"] == "owner"
    assert card["full_name"] == "Иван Петров"
    assert card["role"] == "user"
    assert card["is_active"] is True
    assert card["devices_owned"] == 1
    assert card["devices_held"] == 0
    assert "password_hash" not in card


def test_user_card_of_inactive_user_is_available(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    gone = register_user(make_user, username="gone", is_active=False)

    login_as(client, admin)
    card = client.get(f"/users/{gone.id}").json()

    assert card["is_active"] is False


def test_user_card_not_found(client: TestClient, make_user) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, admin)

    response = client.get("/users/9999")

    assert response.status_code == 404
    assert response.json()["code"] == "USER_NOT_FOUND"


def test_list_users_is_ordered_by_full_name(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    register_user(make_user, username="z", full_name="Яков")
    register_user(make_user, username="a", full_name="Анна")

    login_as(client, admin)
    names = [user["full_name"] for user in client.get("/users").json()]

    assert names == sorted(names)


def test_archived_device_belongs_to_owner(
    client: TestClient, make_user, make_device, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    device: Device = make_device(owner=owner, inventory_no="QA-PH-001")
    device.archived_at = now_local()
    db.commit()

    login_as(client, admin)
    card = client.get(f"/users/{owner.id}").json()

    assert card["devices_owned"] == 1
    assert card["devices_held"] == 0
