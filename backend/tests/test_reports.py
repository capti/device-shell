"""Дашборд и отчёты: счётчики, топ просрочек, «у кого что», графики, доступ."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from helpers import add_checkout, login_as, register_user
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Device
from app.services.reports import (
    dashboard_charts,
    dashboard_stats,
    holders_report,
    overdue_report,
)


def _archived(db: Session, device: Device) -> Device:
    device.archived_at = now_local()
    db.commit()
    return device


def test_dashboard_counts_categories(db: Session, make_user, make_device) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    make_device(owner=owner, inventory_no="QA-PH-001")
    checked_out = make_device(owner=owner, inventory_no="QA-PH-002")
    add_checkout(db, checked_out, holder)
    make_device(owner=owner, inventory_no="QA-PH-003", status="repair")
    make_device(owner=owner, inventory_no="QA-PH-004", status="lost")
    _archived(db, make_device(owner=owner, inventory_no="QA-PH-005"))
    overdue = make_device(owner=owner, inventory_no="QA-PH-006")
    add_checkout(
        db, overdue, holder, expected_return_at=now_local() - timedelta(days=3)
    )

    stats = dashboard_stats(db)

    assert stats["counters"] == {
        "total_active": 5,
        "with_owners": 3,
        "checked_out": 2,
        "in_repair": 1,
        "lost": 1,
        "archived": 1,
        "overdue": 1,
    }


def test_dashboard_top_overdue_ordered(db: Session, make_user, make_device) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    days = (7, 6, 5, 4, 3, 2, 1)
    for index, day in enumerate(days, start=1):
        device = make_device(owner=owner, inventory_no=f"QA-PH-{index:03d}")
        add_checkout(db, device, holder, expected_return_at=now_local() - timedelta(days=day))

    stats = dashboard_stats(db)

    top = stats["top_overdue"]
    assert [row["inventory_no"] for row in top] == [
        "QA-PH-001",
        "QA-PH-002",
        "QA-PH-003",
        "QA-PH-004",
        "QA-PH-005",
    ]
    assert [row["days_overdue"] for row in top] == [7, 6, 5, 4, 3]
    assert top[0]["device_id"] == db.get(Device, top[0]["device_id"]).id
    assert top[0]["holder"]["id"] == holder.id


def test_dashboard_counters_from_api(
    client: TestClient, make_user, make_device
) -> None:
    owner = register_user(make_user, username="owner")
    register_user(make_user, username="admin", role="admin")
    make_device(owner=owner, inventory_no="QA-PH-001")
    login_as(client, owner)

    response = client.get("/dashboard/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["counters"]["total_active"] == 1
    assert body["counters"]["with_owners"] == 1
    assert body["counters"]["overdue"] == 0


def test_holders_report_lists_active(
    client: TestClient, make_user, db: Session, make_device
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    free = make_device(owner=owner, inventory_no="QA-PH-001")
    held = make_device(owner=owner, inventory_no="QA-PH-002")
    add_checkout(db, held, holder)
    _archived(db, make_device(owner=owner, inventory_no="QA-PH-003"))

    report = holders_report(db)

    rows = report["items"]
    assert [(row["inventory_no"], row["holder"]["id"]) for row in rows] == [
        ("QA-PH-001", owner.id),
        ("QA-PH-002", holder.id),
    ]
    assert rows[0]["owner"]["full_name"] == owner.full_name
    assert rows[0]["status"] == "active"
    assert {row["device_id"] for row in rows} == {free.id, held.id}


def test_overdue_report_rows(db: Session, make_user, make_device) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    from app.services.reports import overdue_report

    on_time = make_device(owner=owner, inventory_no="QA-PH-001")
    add_checkout(db, on_time, holder, expected_return_at=now_local() + timedelta(days=2))
    late = make_device(owner=owner, inventory_no="QA-PH-002")
    checkout = add_checkout(
        db, late, holder, expected_return_at=now_local() - timedelta(days=2)
    )

    report = overdue_report(db)

    rows = report["items"]
    assert len(rows) == 1
    assert rows[0]["device_id"] == late.id
    assert rows[0]["inventory_no"] == "QA-PH-002"
    assert rows[0]["holder"]["id"] == holder.id
    assert rows[0]["expected_return_at"] == checkout.expected_return_at
    assert rows[0]["days_overdue"] == 2


def test_reports_require_authentication(client: TestClient) -> None:
    assert client.get("/dashboard/stats").status_code == 401
    assert client.get("/dashboard/charts").status_code == 401
    assert client.get("/reports/holders").status_code == 401
    assert client.get("/reports/overdue").status_code == 401
    assert client.get("/reports/export.xlsx").status_code == 401


def test_reports_available_to_plain_user(
    client: TestClient, make_user, make_device
) -> None:
    owner = register_user(make_user, username="owner")
    make_device(owner=owner, inventory_no="QA-PH-001")
    login_as(client, owner)

    assert client.get("/dashboard/stats").status_code == 200
    assert client.get("/dashboard/charts").status_code == 200
    assert client.get("/reports/holders").status_code == 200
    assert client.get("/reports/overdue").status_code == 200
    assert client.get("/reports/export.xlsx").status_code == 200


def _months_ago(count: int) -> datetime:
    """Первое число месяца `count` месяцев назад (день не важен, месяц — да)."""
    moment = now_local()
    month = moment.month - count
    year = moment.year
    while month <= 0:
        month += 12
        year -= 1
    return moment.replace(year=year, month=month, day=1)


def test_charts_turnover_spans_twelve_months(db: Session, make_user, make_device) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    device = make_device(owner=owner, inventory_no="QA-PH-001")
    checkout = add_checkout(
        db, device, holder, expected_return_at=now_local() + timedelta(days=14)
    )
    checkout.taken_at = _months_ago(3)
    db.commit()

    charts = dashboard_charts(db)

    points = charts["turnover"]
    months = [point["month"] for point in points]
    assert len(months) == 12
    assert months[-1] == f"{now_local():%Y-%m}"
    assert months == sorted(months)

    target = f"{_months_ago(3):%Y-%m}"
    assert next(p for p in points if p["month"] == target)["checked_out"] == 1
    others = [p for p in points if p["month"] != target]
    assert all(p["checked_out"] == 0 and p["returned"] == 0 for p in others)


def test_charts_turnover_excludes_events_after_current_month(
    db: Session, make_user, make_device
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    device = make_device(owner=owner, inventory_no="QA-PH-001")
    checkout = add_checkout(db, device, holder)
    checkout.taken_at = now_local() + timedelta(days=400)
    db.commit()

    charts = dashboard_charts(db)

    assert len(charts["turnover"]) == 12
    assert all(point["checked_out"] == 0 for point in charts["turnover"])


def test_charts_return_counted_by_return_month(db: Session, make_user, make_device) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    device = make_device(owner=owner, inventory_no="QA-PH-001")
    checkout = add_checkout(db, device, holder)
    checkout.taken_at = _months_ago(2)
    checkout.returned_at = now_local()
    checkout.closed_reason = "returned"
    db.commit()

    points = {p["month"]: p for p in dashboard_charts(db)["turnover"]}

    assert points[f"{_months_ago(2):%Y-%m}"] == {
        "month": f"{_months_ago(2):%Y-%m}",
        "checked_out": 1,
        "returned": 0,
    }
    assert points[f"{now_local():%Y-%m}"]["returned"] == 1


def test_charts_overdue_buckets_split_by_days(db: Session, make_user, make_device) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    for index, days in enumerate((3, 10, 20, 40), start=1):
        device = make_device(owner=owner, inventory_no=f"QA-PH-{index:03d}")
        add_checkout(
            db, device, holder, expected_return_at=now_local() - timedelta(days=days)
        )

    charts = dashboard_charts(db)

    assert charts["overdue_buckets"] == [
        {"bucket": "1-7", "count": 1},
        {"bucket": "8-14", "count": 1},
        {"bucket": "15-30", "count": 1},
        {"bucket": "31+", "count": 1},
    ]
    overdue_count = len(overdue_report(db)["items"])
    assert sum(bucket["count"] for bucket in charts["overdue_buckets"]) == overdue_count
    assert dashboard_stats(db)["counters"]["overdue"] == overdue_count


def test_charts_overdue_buckets_without_overdue(db: Session) -> None:
    charts = dashboard_charts(db)

    assert charts["overdue_buckets"] == [
        {"bucket": label, "count": 0} for label in ("1-7", "8-14", "15-30", "31+")
    ]
    assert all(point["checked_out"] == 0 for point in charts["turnover"])


def test_charts_overdue_buckets_count_active_only(
    db: Session, make_user, make_device
) -> None:
    """В корзины попадают только активные выдачи; закрытые и архив не считаются."""
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    device = make_device(owner=owner, inventory_no="QA-PH-001")
    add_checkout(
        db, device, holder, expected_return_at=now_local() - timedelta(days=5)
    )
    archived = make_device(owner=owner, inventory_no="QA-PH-002")
    archived_checkout = add_checkout(
        db, archived, holder, expected_return_at=now_local() - timedelta(days=5)
    )
    archived_checkout.returned_at = now_local()
    archived_checkout.closed_reason = "returned"
    archived.archived_at = now_local()
    db.commit()

    charts = dashboard_charts(db)

    assert sum(point["count"] for point in charts["overdue_buckets"]) == 1
    assert charts["overdue_buckets"][0] == {"bucket": "1-7", "count": 1}
