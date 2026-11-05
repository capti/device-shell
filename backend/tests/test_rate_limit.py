from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.errors import AppError
from app.services.passwords import hash_password
from app.services.rate_limit import LoginRateLimiter


def test_sixth_attempt_is_rate_limited(client: TestClient, make_user) -> None:
    make_user(username="rate-user", password_hash=hash_password("secret123"))
    payload = {"username": "rate-user", "password": "wrong-password"}

    for _ in range(5):
        response = client.post("/auth/login", json=payload)
        assert response.status_code == 401

    blocked = client.post("/auth/login", json=payload)

    assert blocked.status_code == 429
    assert blocked.json()["code"] == "RATE_LIMITED"


def test_correct_password_is_not_checked_while_blocked(
    client: TestClient, make_user
) -> None:
    make_user(username="rate-user", password_hash=hash_password("secret123"))
    for _ in range(5):
        client.post(
            "/auth/login", json={"username": "rate-user", "password": "wrong-password"}
        )

    response = client.post(
        "/auth/login", json={"username": "rate-user", "password": "secret123"}
    )

    assert response.status_code == 429
    assert "set-cookie" not in response.headers


def test_rate_limit_is_scoped_to_username(client: TestClient, make_user) -> None:
    make_user(username="first-user", password_hash=hash_password("secret123"))
    make_user(username="second-user", password_hash=hash_password("secret123"))
    for _ in range(5):
        client.post(
            "/auth/login", json={"username": "first-user", "password": "wrong-password"}
        )

    response = client.post(
        "/auth/login", json={"username": "second-user", "password": "secret123"}
    )

    assert response.status_code == 200


def _fixed_clock(monkeypatch, moment: datetime) -> None:
    monkeypatch.setattr("app.services.rate_limit.now_local", lambda: moment)


def test_failure_exactly_one_window_old_is_forgotten(monkeypatch) -> None:
    moment = datetime(2026, 1, 1, 12, 0, 0)
    _fixed_clock(monkeypatch, moment)
    limiter = LoginRateLimiter(max_attempts=2, window=timedelta(minutes=1))
    limiter.register_failure("key")

    _fixed_clock(monkeypatch, moment + timedelta(minutes=1))
    limiter.register_failure("key")

    limiter.check("key")


def test_block_is_released_exactly_at_lockout_end(monkeypatch) -> None:
    moment = datetime(2026, 1, 1, 12, 0, 0)
    current = [moment]
    monkeypatch.setattr("app.services.rate_limit.now_local", lambda: current[0])
    limiter = LoginRateLimiter(
        max_attempts=1,
        window=timedelta(minutes=1),
        lockout=timedelta(minutes=15),
    )
    limiter.register_failure("key")

    current[0] = moment + timedelta(minutes=15)
    limiter.check("key")


def test_sub_minute_lockout_reports_at_least_one_minute(monkeypatch) -> None:
    moment = datetime(2026, 1, 1, 12, 0, 0)
    _fixed_clock(monkeypatch, moment)
    limiter = LoginRateLimiter(
        max_attempts=1,
        window=timedelta(minutes=1),
        lockout=timedelta(seconds=30),
    )
    limiter.register_failure("key")

    with pytest.raises(AppError) as excinfo:
        limiter.check("key")

    assert "1 мин" in excinfo.value.message


def test_default_window_is_one_minute(monkeypatch) -> None:
    moment = datetime(2026, 1, 1, 12, 0, 0)
    current = [moment]
    monkeypatch.setattr("app.services.rate_limit.now_local", lambda: current[0])
    limiter = LoginRateLimiter(max_attempts=2)

    limiter.register_failure("key")
    current[0] = moment + timedelta(seconds=30)
    limiter.register_failure("key")

    with pytest.raises(AppError):
        limiter.check("key")


def test_successful_login_resets_failures(client: TestClient, make_user) -> None:
    make_user(username="rate-user", password_hash=hash_password("secret123"))
    for _ in range(4):
        client.post(
            "/auth/login", json={"username": "rate-user", "password": "wrong-password"}
        )

    assert (
        client.post(
            "/auth/login", json={"username": "rate-user", "password": "secret123"}
        ).status_code
        == 200
    )
    for _ in range(5):
        response = client.post(
            "/auth/login", json={"username": "rate-user", "password": "wrong-password"}
        )
        assert response.status_code == 401
