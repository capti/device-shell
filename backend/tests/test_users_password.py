"""Сброс пароля администратором и смена собственного пароля."""

from fastapi.testclient import TestClient
from helpers import PASSWORD, login_as, register_user


def _login(client: TestClient, username: str, password: str) -> int:
    return client.post(
        "/auth/login", json={"username": username, "password": password}
    ).status_code


def test_admin_resets_password(
    client: TestClient, make_client, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target")
    login_as(client, admin)
    target_session = make_client()
    assert _login(target_session, "target", PASSWORD) == 200

    response = client.post(
        f"/users/{target.id}/password", json={"password": "new-secret-1"}
    )

    assert response.status_code == 204
    assert target_session.get("/auth/me").status_code == 401
    other = make_client()
    assert _login(other, "target", "new-secret-1") == 200
    assert _login(other, "target", PASSWORD) == 401


def test_admin_reset_rejects_weak_password(
    client: TestClient, make_client, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    target = register_user(make_user, username="target")
    login_as(client, admin)
    target_session = make_client()
    assert _login(target_session, "target", PASSWORD) == 200

    response = client.post(
        f"/users/{target.id}/password", json={"password": "short"}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "WEAK_PASSWORD"
    assert target_session.get("/auth/me").status_code == 200


def test_regular_user_cannot_reset_password(
    client: TestClient, make_user
) -> None:
    user = register_user(make_user, username="plain")
    target = register_user(make_user, username="target")
    login_as(client, user)

    response = client.post(
        f"/users/{target.id}/password", json={"password": "new-secret-1"}
    )

    assert response.status_code == 403


def test_reset_password_unknown_user(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    login_as(client, admin)

    response = client.post(
        "/users/9999/password", json={"password": "new-secret-1"}
    )

    assert response.status_code == 404
    assert response.json()["code"] == "USER_NOT_FOUND"


def test_reset_password_requires_session(client: TestClient) -> None:
    response = client.post(
        "/users/1/password", json={"password": "new-secret-1"}
    )
    assert response.status_code == 401


def test_user_changes_own_password(
    client: TestClient, make_client, make_user
) -> None:
    user = register_user(make_user, username="plain")
    login_as(client, user)
    other_session = make_client()
    assert _login(other_session, "plain", PASSWORD) == 200

    response = client.post(
        "/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "another-secret"},
    )

    assert response.status_code == 204
    assert client.get("/auth/me").status_code == 200
    assert other_session.get("/auth/me").status_code == 401
    other = make_client()
    assert _login(other, "plain", "another-secret") == 200
    assert _login(other, "plain", PASSWORD) == 401


def test_change_password_rejects_wrong_current(
    client: TestClient, make_client, make_user
) -> None:
    user = register_user(make_user, username="plain")
    login_as(client, user)

    response = client.post(
        "/auth/change-password",
        json={"current_password": "wrong-one", "new_password": "another-secret"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "INVALID_PASSWORD"
    assert client.get("/auth/me").status_code == 200

    other = make_client()
    assert _login(other, "plain", PASSWORD) == 200


def test_change_password_rejects_weak_new_password(
    client: TestClient, make_client, make_user
) -> None:
    user = register_user(make_user, username="plain")
    login_as(client, user)
    other_session = make_client()
    assert _login(other_session, "plain", PASSWORD) == 200

    response = client.post(
        "/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "short"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "WEAK_PASSWORD"
    assert client.get("/auth/me").status_code == 200
    assert other_session.get("/auth/me").status_code == 200


def test_change_password_requires_session(client: TestClient) -> None:
    response = client.post(
        "/auth/change-password",
        json={"current_password": PASSWORD, "new_password": "another-secret"},
    )

    assert response.status_code == 401
