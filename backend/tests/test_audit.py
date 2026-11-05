"""Глобальный журнал аудита: состав событий, фильтры, окно по умолчанию, доступ."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from helpers import login_as, register_user
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import DeviceEvent


def _add_event(
    db: Session,
    device,
    actor,
    *,
    type_: str = "created",
    created_at: datetime | None = None,
    payload: dict | None = None,
) -> DeviceEvent:
    event = DeviceEvent(
        device_id=device.id,
        actor_id=actor.id,
        type=type_,
        payload=payload,
        created_at=created_at or now_local(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def test_audit_events_lists_events_of_all_devices(
    client: TestClient, make_user, make_device, db: Session
) -> None:
    actor = register_user(make_user, username="actor")
    first = make_device(owner=actor, inventory_no="QA-PH-001")
    second = make_device(owner=actor, inventory_no="QA-PH-002")
    _add_event(db, first, actor, created_at=now_local() - timedelta(hours=2))
    _add_event(db, second, actor, created_at=now_local() - timedelta(hours=1))
    login_as(client, register_user(make_user, username="admin", role="admin"))

    response = client.get("/audit/events")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    # От новых к старым, с номером устройства и автором.
    assert [item["inventory_no"] for item in body["events"]] == ["QA-PH-002", "QA-PH-001"]
    assert {item["actor_id"] for item in body["events"]} == {actor.id}
    assert body["filtered_device_id"] is None


def test_audit_events_expose_type_payload_and_label(
    client: TestClient, make_user, make_device, db: Session
) -> None:
    actor = register_user(make_user, username="actor")
    device = make_device(owner=actor)
    _add_event(db, device, actor, type_="checked_out", payload={"holder_id": 7})
    login_as(client, register_user(make_user, username="admin", role="admin"))

    response = client.get("/audit/events")

    item = response.json()["events"][0]
    assert item["event_type"] == "checked_out"
    assert item["event_type_label"] == "Выдача"
    assert item["payload"] == {"holder_id": 7}
    assert item["device_id"] == device.id


def test_audit_events_label_falls_back_to_type_code(
    client: TestClient, make_user, make_device, db: Session
) -> None:
    """Новый тип события не должен ломать ответ — отдаётся его код."""
    actor = register_user(make_user, username="actor")
    device = make_device(owner=actor)
    _add_event(db, device, actor, type_="invented_action")
    login_as(client, register_user(make_user, username="admin", role="admin"))

    response = client.get("/audit/events")

    item = response.json()["events"][0]
    assert item["event_type"] == "invented_action"
    assert item["event_type_label"] == "invented_action"


def test_audit_events_filter_by_device(
    client: TestClient, make_user, make_device, db: Session
) -> None:
    actor = register_user(make_user, username="actor")
    chosen = make_device(owner=actor, inventory_no="QA-PH-001")
    other = make_device(owner=actor, inventory_no="QA-PH-002")
    _add_event(db, chosen, actor)
    _add_event(db, other, actor)
    login_as(client, register_user(make_user, username="admin", role="admin"))

    response = client.get("/audit/events", params={"device_id": chosen.id})

    body = response.json()
    assert body["total"] == 1
    assert body["filtered_device_id"] == chosen.id
    assert [item["inventory_no"] for item in body["events"]] == ["QA-PH-001"]


def test_audit_events_date_range_is_inclusive_on_day_boundaries(
    client: TestClient, make_user, make_device, db: Session
) -> None:
    actor = register_user(make_user, username="actor")
    device = make_device(owner=actor)
    today = now_local().replace(hour=0, minute=0, second=0, microsecond=0)
    _add_event(db, device, actor, created_at=today, payload={"edge": "start"})
    _add_event(
        db,
        device,
        actor,
        created_at=today.replace(hour=23, minute=59, second=59),
        payload={"edge": "end"},
    )
    _add_event(
        db,
        device,
        actor,
        created_at=today - timedelta(seconds=1),
        payload={"edge": "before"},
    )
    login_as(client, register_user(make_user, username="admin", role="admin"))

    response = client.get(
        "/audit/events",
        params={"from_at": today.isoformat(), "to_at": today.isoformat()},
    )

    body = response.json()
    assert body["total"] == 2
    assert {item["payload"]["edge"] for item in body["events"]} == {"start", "end"}


def test_audit_events_default_window_is_thirty_days(
    client: TestClient, make_user, make_device, db: Session
) -> None:
    actor = register_user(make_user, username="actor")
    device = make_device(owner=actor)
    _add_event(db, device, actor, created_at=now_local() - timedelta(days=29))
    _add_event(db, device, actor, created_at=now_local() - timedelta(days=31))
    login_as(client, register_user(make_user, username="admin", role="admin"))

    response = client.get("/audit/events")

    assert response.json()["total"] == 1


def test_audit_events_by_device_are_not_cut_by_default_window(
    client: TestClient, make_user, make_device, db: Session
) -> None:
    """Запрос по устройству узкий сам по себе: старые события не должны пропадать."""
    actor = register_user(make_user, username="actor")
    device = make_device(owner=actor)
    _add_event(db, device, actor, created_at=now_local() - timedelta(days=31))
    login_as(client, register_user(make_user, username="admin", role="admin"))

    response = client.get("/audit/events", params={"device_id": device.id})

    assert response.json()["total"] == 1


def test_audit_events_rejects_non_admin(client: TestClient, make_user) -> None:
    register_user(make_user, username="admin", role="admin")
    user = register_user(make_user, username="plain", role="user")
    login_as(client, user)

    response = client.get("/audit/events")

    assert response.status_code == 403
    assert response.json() == {
        "code": "FORBIDDEN",
        "message": "Доступ к журналу аудита только для администраторов",
    }
