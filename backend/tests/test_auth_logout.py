from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import UserSession
from app.services.passwords import hash_password


def _login(client: TestClient, make_user) -> None:
    make_user(username="logout-user", password_hash=hash_password("secret123"))
    response = client.post(
        "/auth/login", json={"username": "logout-user", "password": "secret123"}
    )
    assert response.status_code == 200


def test_logout_revokes_session_and_clears_cookie(
    client: TestClient, db: Session, make_user
) -> None:
    _login(client, make_user)

    response = client.post("/auth/logout")

    assert response.status_code == 204
    assert db.scalar(select(func.count()).select_from(UserSession)) == 0
    assert client.get("/auth/me").status_code == 401


def test_logout_without_session_is_idempotent(client: TestClient) -> None:
    response = client.post("/auth/logout")

    assert response.status_code == 204
    assert client.get("/auth/me").status_code == 401
