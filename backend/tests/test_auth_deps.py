from fastapi import Depends
from fastapi.testclient import TestClient

from app.api.deps import require_admin
from app.main import app
from app.models import User
from app.services.passwords import hash_password


@app.get("/_test/admin-only")
def _admin_only(user: User = Depends(require_admin)) -> dict[str, int]:
    return {"id": user.id}


def _login(client: TestClient, make_user, *, username: str, role: str) -> None:
    make_user(username=username, role=role, password_hash=hash_password("secret123"))
    response = client.post(
        "/auth/login", json={"username": username, "password": "secret123"}
    )
    assert response.status_code == 200


def test_endpoint_requires_session(client: TestClient) -> None:
    response = client.get("/_test/admin-only")

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHORIZED"


def test_user_gets_403_on_admin_endpoint(client: TestClient, make_user) -> None:
    _login(client, make_user, username="plain-user", role="user")

    response = client.get("/_test/admin-only")

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_admin_passes_admin_endpoint(client: TestClient, make_user) -> None:
    _login(client, make_user, username="admin-user", role="admin")

    response = client.get("/_test/admin-only")

    assert response.status_code == 200
    assert response.json()["id"] > 0
