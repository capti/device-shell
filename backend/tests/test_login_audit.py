"""Журнал входов: запись попыток, append-only и админ-чтение."""

from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from helpers import PASSWORD, login_as, register_user
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import LoginEvent, User

USER_AGENT = "QA-Test-Agent/1.0"
# IP, который TestClient подставляет как request.client.host.
TEST_HOST = "testclient"


def _events(db: Session) -> list[LoginEvent]:
    return list(db.scalars(select(LoginEvent).order_by(LoginEvent.id)).all())


def _login(client: TestClient, username: str, password: str = PASSWORD):
    return client.post(
        "/auth/login",
        json={"username": username, "password": password},
        headers={"User-Agent": USER_AGENT},
    )


def _add_event(
    db: Session,
    *,
    username_attempted: str = "tester",
    success: bool = True,
    reason: str | None = None,
    user: User | None = None,
    created_at: datetime | None = None,
) -> LoginEvent:
    event = LoginEvent(
        username_attempted=username_attempted,
        user_id=user.id if user else None,
        success=success,
        reason=reason,
        ip_address="127.0.0.1",
        user_agent=USER_AGENT,
        created_at=created_at or now_local(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def _admin_client(client: TestClient, make_user) -> TestClient:
    return login_as(client, register_user(make_user, username="admin", role="admin"))


def test_successful_login_is_recorded(client: TestClient, make_user, db: Session) -> None:
    user = register_user(make_user, username="tester")

    response = _login(client, "tester")

    assert response.status_code == 200, response.text
    (event,) = _events(db)
    assert event.success is True
    assert event.reason is None
    assert event.user_id == user.id
    assert event.username_attempted == "tester"
    assert event.ip_address == TEST_HOST
    assert event.user_agent == USER_AGENT


def test_wrong_password_is_recorded(client: TestClient, make_user, db: Session) -> None:
    """Запись переживает откат транзакции: 401 не должен её уничтожать."""
    user = register_user(make_user, username="tester")

    response = _login(client, "tester", "wrong-password")

    assert response.status_code == 401
    (event,) = _events(db)
    assert event.success is False
    assert event.reason == "invalid_credentials"
    assert event.user_id == user.id


def test_unknown_username_is_recorded_without_user(
    client: TestClient, db: Session
) -> None:
    response = _login(client, "ghost")

    assert response.status_code == 401
    (event,) = _events(db)
    assert event.success is False
    assert event.reason == "invalid_credentials"
    assert event.username_attempted == "ghost"
    assert event.user_id is None


def test_inactive_user_is_recorded(client: TestClient, make_user, db: Session) -> None:
    user = register_user(make_user, username="fired", is_active=False)

    response = _login(client, "fired")

    assert response.status_code == 401
    (event,) = _events(db)
    assert event.success is False
    assert event.reason == "inactive_user"
    assert event.user_id == user.id


def test_rate_limited_attempt_is_recorded(
    client: TestClient, make_user, db: Session
) -> None:
    register_user(make_user, username="tester")
    for _ in range(5):
        assert _login(client, "tester", "wrong").status_code == 401

    response = _login(client, "tester", "wrong")

    assert response.status_code == 429
    events = _events(db)
    assert len(events) == 6
    blocked = events[-1]
    assert blocked.success is False
    assert blocked.reason == "rate_limited"
    assert blocked.username_attempted == "tester"


def test_login_event_is_append_only(client: TestClient, make_user, db: Session) -> None:
    register_user(make_user, username="tester")
    _login(client, "tester")

    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("UPDATE login_events SET success = 0"))
    db.rollback()
    with pytest.raises(DBAPIError, match="append-only"):
        db.execute(text("DELETE FROM login_events"))
    db.rollback()


def test_admin_lists_login_events_newest_first(
    client: TestClient, make_user, db: Session
) -> None:
    user = register_user(make_user, username="tester")
    _login(client, "tester", "wrong")
    _login(client, "tester")
    _admin_client(client, make_user)

    # Вход админа ради проверки тоже попадает в журнал — это верно,
    # поэтому выборку сужаем фильтром по логину.
    response = client.get("/audit/logins", params={"username": "tester"})

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [item["success"] for item in body["events"]] == [True, False]
    newest = body["events"][0]
    assert newest["user_id"] == user.id
    assert newest["ip_address"] == TEST_HOST
    assert body["events"][1]["reason_label"] == "Неверные учётные данные"

    whole_journal = client.get("/audit/logins").json()
    assert {item["username_attempted"] for item in whole_journal["events"]} == {
        "tester",
        "admin",
    }


def test_login_events_filter_by_success_and_username(
    client: TestClient, make_user, db: Session
) -> None:
    register_user(make_user, username="tester")
    register_user(make_user, username="other")
    _login(client, "tester", "wrong")
    _login(client, "other")
    _admin_client(client, make_user)

    failed = client.get("/audit/logins", params={"success": False}).json()
    by_name = client.get("/audit/logins", params={"username": "TEST"}).json()

    assert [item["username_attempted"] for item in failed["events"]] == ["tester"]
    # Подстрока в любом регистре: в журнале логины вводят как угодно.
    assert [item["username_attempted"] for item in by_name["events"]] == ["tester"]


def test_login_events_date_range_is_inclusive_on_day_boundaries(
    client: TestClient, make_user, db: Session
) -> None:
    today = now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    _add_event(db, created_at=today, username_attempted="day-start")
    _add_event(
        db,
        created_at=today.replace(hour=23, minute=59, second=59),
        username_attempted="day-end",
    )
    _add_event(
        db, created_at=today - timedelta(seconds=1), username_attempted="day-before"
    )
    _admin_client(client, make_user)

    response = client.get(
        "/audit/logins",
        params={
            "from_at": today.isoformat(),
            "to_at": today.isoformat(),
            "username": "day-",
        },
    )

    body = response.json()
    assert body["total"] == 2
    assert {item["username_attempted"] for item in body["events"]} == {
        "day-start",
        "day-end",
    }


def test_login_events_default_window_is_thirty_days(
    client: TestClient, make_user, db: Session
) -> None:
    _add_event(
        db, created_at=now_local() - timedelta(days=29), username_attempted="win-recent"
    )
    _add_event(
        db, created_at=now_local() - timedelta(days=31), username_attempted="win-ancient"
    )
    _admin_client(client, make_user)

    params = {"username": "win-"}
    default_view = client.get("/audit/logins", params=params).json()
    with_range = client.get(
        "/audit/logins",
        params={**params, "from_at": (now_local() - timedelta(days=40)).date().isoformat()},
    ).json()

    assert [item["username_attempted"] for item in default_view["events"]] == [
        "win-recent"
    ]
    assert {item["username_attempted"] for item in with_range["events"]} == {
        "win-recent",
        "win-ancient",
    }


def test_login_events_limit_truncates_but_total_stays_full(
    client: TestClient, make_user, db: Session
) -> None:
    for index in range(3):
        _add_event(db, username_attempted=f"bulk-{index}")
    _admin_client(client, make_user)

    response = client.get("/audit/logins", params={"limit": 2, "username": "bulk-"})

    body = response.json()
    assert len(body["events"]) == 2
    assert body["total"] == 3
    assert body["limit"] == 2


def test_login_events_reject_non_admin(client: TestClient, make_user) -> None:
    register_user(make_user, username="admin", role="admin")
    login_as(client, register_user(make_user, username="plain", role="user"))

    response = client.get("/audit/logins")

    assert response.status_code == 403
    assert response.json() == {
        "code": "FORBIDDEN",
        "message": "Доступ к журналу аудита только для администраторов",
    }
