from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User
from app.services.passwords import hash_password


def _login(client: TestClient, make_user, *, username: str = "me-user") -> dict:
    make_user(username=username, password_hash=hash_password("secret123"))
    response = client.post(
        "/auth/login", json={"username": username, "password": "secret123"}
    )
    assert response.status_code == 200
    return response.json()


def test_me_returns_profile_without_password_hash(
    client: TestClient, make_user
) -> None:
    _login(client, make_user)

    response = client.get("/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "me-user"
    assert body["full_name"] == "Тестовый Пользователь"
    assert body["role"] == "user"
    assert body["is_active"] is True
    assert "password_hash" not in body


def test_me_requires_session(client: TestClient) -> None:
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_me_rejects_unknown_session_token(client: TestClient) -> None:
    client.cookies.set("qa_session", "not-a-real-token")

    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "SESSION_EXPIRED"


def test_me_rejects_deactivated_user(
    client: TestClient, make_user, db: Session
) -> None:
    _login(client, make_user)
    user = db.scalar(select(User).where(User.username == "me-user"))
    user.is_active = False
    db.commit()

    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json()["code"] == "USER_INACTIVE"
    assert "set-cookie" not in response.headers


def test_me_refreshes_session_cookie(client: TestClient, make_user) -> None:
    _login(client, make_user)

    response = client.get("/auth/me")

    assert response.status_code == 200
    assert "qa_session=" in response.headers["set-cookie"]
