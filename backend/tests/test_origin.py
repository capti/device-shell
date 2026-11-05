from fastapi.testclient import TestClient

from app.config import settings
from app.services.passwords import hash_password


def test_foreign_origin_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/auth/login",
        json={"username": "nobody", "password": "secret123"},
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_own_origin_passes(client: TestClient, make_user) -> None:
    make_user(username="origin-user", password_hash=hash_password("secret123"))

    response = client.post(
        "/auth/login",
        json={"username": "origin-user", "password": "secret123"},
        headers={"Origin": "http://localhost:8000"},
    )

    assert response.status_code == 200


def test_missing_origin_is_allowed(client: TestClient, make_user) -> None:
    make_user(username="origin-user", password_hash=hash_password("secret123"))

    response = client.post(
        "/auth/login", json={"username": "origin-user", "password": "secret123"}
    )

    assert response.status_code == 200


def test_missing_origin_is_rejected_in_production(
    client: TestClient, make_user, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    make_user(username="prod-user", password_hash=hash_password("secret123"))

    response = client.post(
        "/auth/login", json={"username": "prod-user", "password": "secret123"}
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_missing_origin_is_allowed_in_development(
    client: TestClient, make_user, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "app_env", "development")
    make_user(username="dev-user", password_hash=hash_password("secret123"))

    response = client.post(
        "/auth/login", json={"username": "dev-user", "password": "secret123"}
    )

    assert response.status_code == 200


def test_foreign_origin_is_rejected_in_production(
    client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")

    response = client.post(
        "/auth/login",
        json={"username": "nobody", "password": "secret123"},
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_foreign_origin_does_not_block_read_requests(client: TestClient) -> None:
    response = client.get("/health", headers={"Origin": "https://evil.example"})

    assert response.status_code == 200
