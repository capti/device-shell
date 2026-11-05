"""Создание и редактирование сотрудников администратором."""

from fastapi.testclient import TestClient
from helpers import PASSWORD, login_as, register_user
from sqlalchemy.orm import Session

from app.models import User


def _payload(**overrides) -> dict:
    data = {
        "username": "new-user",
        "full_name": "Новый Сотрудник",
        "password": PASSWORD,
    }
    data.update(overrides)
    return data


def test_admin_creates_user(
    client: TestClient, make_user, make_client
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, admin)

    response = client.post(
        "/users",
        json=_payload(
            role="user",
            email="new@example.com",
            team="QA",
            telegram="@new",
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "new-user"
    assert body["email"] == "new@example.com"
    assert body["team"] == "QA"
    assert body["telegram"] == "@new"
    assert body["is_active"] is True
    assert body["devices_owned"] == 0
    assert body["devices_held"] == 0

    other = make_client()
    logged = other.post(
        "/auth/login", json={"username": "new-user", "password": PASSWORD}
    )
    assert logged.status_code == 200


def test_create_user_rejects_duplicate_username(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    register_user(make_user, username="taken")
    login_as(client, admin)

    response = client.post("/users", json=_payload(username="taken"))

    assert response.status_code == 409
    assert response.json()["code"] == "USERNAME_TAKEN"


def test_create_user_rejects_weak_password(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, admin)

    response = client.post("/users", json=_payload(password="short"))

    assert response.status_code == 422
    assert response.json()["code"] == "WEAK_PASSWORD"


def test_regular_user_cannot_create_user(
    client: TestClient, make_user
) -> None:
    user = register_user(make_user, username="plain")
    login_as(client, user)

    response = client.post("/users", json=_payload())

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_create_user_requires_session(client: TestClient) -> None:
    assert client.post("/users", json=_payload()).status_code == 401


def test_admin_updates_user_fields_and_role(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target")
    login_as(client, admin)

    response = client.patch(
        f"/users/{target.id}",
        json={
            "full_name": "Новое Имя",
            "email": "new@example.com",
            "team": "Mobile",
            "telegram": "@target",
            "role": "admin",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["full_name"] == "Новое Имя"
    assert body["email"] == "new@example.com"
    assert body["team"] == "Mobile"
    assert body["telegram"] == "@target"
    assert body["role"] == "admin"

    card = client.get(f"/users/{target.id}").json()
    assert card["role"] == "admin"


def test_update_clears_contact_with_empty_string(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target")
    target.email = "old@example.com"
    db.commit()
    login_as(client, admin)

    response = client.patch(f"/users/{target.id}", json={"email": ""})

    assert response.status_code == 200
    assert response.json()["email"] is None


def test_update_rejects_username_change(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target")
    login_as(client, admin)

    response = client.patch(
        f"/users/{target.id}", json={"username": "renamed"}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_update_rejects_blank_full_name(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target")
    login_as(client, admin)

    response = client.patch(f"/users/{target.id}", json={"full_name": "   "})

    assert response.status_code == 422


def test_update_without_changes_keeps_user(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target")
    login_as(client, admin)

    response = client.patch(f"/users/{target.id}", json={})

    assert response.status_code == 200
    assert response.json()["full_name"] == target.full_name
    assert response.json()["role"] == "user"


def test_regular_user_cannot_update_user(
    client: TestClient, make_user
) -> None:
    user = register_user(make_user, username="plain")
    target = register_user(make_user, username="target")
    login_as(client, user)

    response = client.patch(
        f"/users/{target.id}", json={"full_name": "Взлом"}
    )

    assert response.status_code == 403


def test_update_unknown_user(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, admin)

    response = client.patch("/users/9999", json={"full_name": "Никто"})

    assert response.status_code == 404
    assert response.json()["code"] == "USER_NOT_FOUND"


def test_cannot_demote_last_admin(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, admin)

    response = client.patch(f"/users/{admin.id}", json={"role": "user"})

    assert response.status_code == 409
    assert response.json()["code"] == "LAST_ADMIN"

    card = client.get(f"/users/{admin.id}").json()
    assert card["role"] == "admin"


def test_delete_user_is_forbidden(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target")
    login_as(client, admin)

    response = client.delete(f"/users/{target.id}")

    assert response.status_code == 405
    body = response.json()
    assert body["code"] == "METHOD_NOT_ALLOWED"
    assert "Деактивируйте" in body["message"]

    db.expire_all()
    assert db.get(User, target.id) is not None


def test_can_demote_admin_when_another_exists(
    client: TestClient, make_user, db: Session
) -> None:
    first = register_user(make_user, username="first", role="admin")
    second = register_user(make_user, username="second", role="admin")
    login_as(client, first)

    response = client.patch(f"/users/{second.id}", json={"role": "user"})

    assert response.status_code == 200
    assert response.json()["role"] == "user"

    db.expire_all()
    assert db.get(User, second.id).role == "user"
