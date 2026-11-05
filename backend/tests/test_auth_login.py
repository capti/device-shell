from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.passwords import hash_password


def _make_login_user(make_user, *, is_active: bool = True):
    return make_user(
        username="login-user",
        password_hash=hash_password("secret123"),
        is_active=is_active,
    )


def test_login_sets_http_only_cookie(client: TestClient, make_user) -> None:
    user = _make_login_user(make_user)

    response = client.post(
        "/auth/login", json={"username": "login-user", "password": "secret123"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == user.username
    assert "password_hash" not in body

    set_cookie = response.headers["set-cookie"]
    assert "qa_session=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie.lower() or "samesite=lax" in set_cookie.lower()


def test_login_updates_last_login_at(
    client: TestClient, db: Session, make_user
) -> None:
    user = _make_login_user(make_user)
    assert user.last_login_at is None

    client.post("/auth/login", json={"username": "login-user", "password": "secret123"})

    db.refresh(user)
    assert user.last_login_at is not None


def test_login_with_wrong_password_returns_401(client: TestClient, make_user) -> None:
    _make_login_user(make_user)

    response = client.post(
        "/auth/login", json={"username": "login-user", "password": "wrong-password"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"
    assert "set-cookie" not in response.headers


def test_unknown_user_returns_401(client: TestClient) -> None:
    response = client.post(
        "/auth/login", json={"username": "nobody", "password": "secret123"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


def test_inactive_user_cannot_login(client: TestClient, make_user) -> None:
    _make_login_user(make_user, is_active=False)

    response = client.post(
        "/auth/login", json={"username": "login-user", "password": "secret123"}
    )

    assert response.status_code == 401
    assert response.json()["code"] == "INVALID_CREDENTIALS"


def test_login_requires_credentials(client: TestClient) -> None:
    response = client.post("/auth/login", json={})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
