"""Excel-выгрузка: три листа, фильтры, период истории, единая просрочка."""

from datetime import datetime, timedelta
from io import BytesIO

from fastapi.testclient import TestClient
from helpers import add_checkout, login_as, register_user
from openpyxl import load_workbook
from sqlalchemy.orm import Session

from app.clock import now_local
from app.services.reports import days_overdue


def _book(client: TestClient, **params) -> dict:
    response = client.get("/reports/export.xlsx", params=params)
    assert response.status_code == 200, response.text
    assert "spreadsheet" in response.headers["content-type"]
    workbook = load_workbook(BytesIO(response.content))
    return {sheet.title: sheet for sheet in workbook.worksheets}


def test_export_three_sheets(client: TestClient, make_user, make_device) -> None:
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    make_device(owner=owner, inventory_no="QA-PH-001")

    book = _book(client)

    assert list(book) == ["Все устройства", "Просроченные", "История выдач"]
    assert [cell.value for cell in book["Все устройства"][1]][:3] == [
        "Инв. №",
        "Производитель",
        "Модель",
    ]
    assert book["Все устройства"][2][0].value == "QA-PH-001"
    assert book["Все устройства"].max_row == 2
    assert book["Просроченные"].max_row == 1


def test_export_includes_manufacturer_before_model_on_every_sheet(
    client: TestClient, make_user, db: Session, make_device
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = make_device(owner=owner, inventory_no="QA-PH-001")
    device.brand = "Google"
    db.commit()
    add_checkout(db, device, holder, expected_return_at=now_local() - timedelta(days=4))

    book = _book(client)

    for sheet_name in ("Все устройства", "Просроченные", "История выдач"):
        sheet = book[sheet_name]
        assert [cell.value for cell in sheet[1]][:3] == [
            "Инв. №",
            "Производитель",
            "Модель",
        ]
        assert [sheet.cell(row=2, column=column).value for column in (2, 3)] == [
            "Google",
            "Galaxy S23",
        ]


def test_export_formula_like_model_as_text(
    client: TestClient, make_user, db: Session, make_device
) -> None:
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = make_device(owner=owner, inventory_no="QA-PH-001")
    device.model = "=1+1"
    db.commit()

    cell = _book(client)["Все устройства"]["C2"]

    assert cell.value == "=1+1"
    assert cell.data_type == "s"


def test_export_respects_filters(
    client: TestClient, make_user, db: Session, make_device
) -> None:
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    make_device(owner=owner, inventory_no="QA-PH-001")
    repair = make_device(owner=owner, inventory_no="QA-PH-002", status="repair")

    book = _book(client, status="repair")

    rows = list(book["Все устройства"].iter_rows(min_row=2, values_only=True))
    assert [row[0] for row in rows] == ["QA-PH-002"]
    assert repair is not None


def test_export_overdue_sheet(
    client: TestClient, make_user, db: Session, make_device
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    late = make_device(owner=owner, inventory_no="QA-PH-001")
    add_checkout(db, late, holder, expected_return_at=now_local() - timedelta(days=4))

    book = _book(client)

    rows = list(book["Просроченные"].iter_rows(min_row=2, values_only=True))
    assert [row[0] for row in rows] == ["QA-PH-001"]
    assert rows[0][7] == 4


def test_export_history_period(
    client: TestClient, make_user, db: Session, make_device
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    seasonal = make_device(owner=owner, inventory_no="QA-PH-001")
    closed = add_checkout(
        db,
        seasonal,
        holder,
        expected_return_at=datetime(2026, 6, 20, 12, 0),
        returned_at=datetime(2026, 6, 25, 12, 0),
    )
    closed.taken_at = datetime(2026, 6, 10, 12, 0)
    db.commit()
    current = make_device(owner=owner, inventory_no="QA-PH-002")
    add_checkout(db, current, holder)

    book = _book(client, from_date="2026-05-01", to_date="2026-07-31")

    rows = list(book["История выдач"].iter_rows(min_row=2, values_only=True))
    assert [row[0] for row in rows] == ["QA-PH-001"]
    assert rows[0][5] == "25.06.2026"
    assert rows[0][6] == "returned"


def test_export_invalid_period(
    client: TestClient, make_user, make_device
) -> None:
    owner = register_user(make_user, username="owner")
    make_device(owner=owner, inventory_no="QA-PH-001")
    login_as(client, owner)

    response = client.get(
        "/reports/export.xlsx",
        params={"from_date": "2026-08-01", "to_date": "2026-07-01"},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_export_accepts_single_day_period(
    client: TestClient, make_user, make_device
) -> None:
    owner = register_user(make_user, username="owner")
    make_device(owner=owner, inventory_no="QA-PH-001")
    login_as(client, owner)

    book = _book(client, from_date="2026-07-01", to_date="2026-07-01")

    assert book["История выдач"].max_row == 1


def test_export_device_sheet_marks_overdue(
    client: TestClient, make_user, db: Session, make_device
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    late = make_device(owner=owner, inventory_no="QA-PH-001")
    add_checkout(db, late, holder, expected_return_at=now_local() - timedelta(days=3))
    on_time = make_device(owner=owner, inventory_no="QA-PH-002")
    add_checkout(
        db, on_time, holder, expected_return_at=now_local() + timedelta(days=3)
    )

    rows = list(
        _book(client)["Все устройства"].iter_rows(min_row=2, values_only=True)
    )

    assert [(row[0], row[9]) for row in rows] == [
        ("QA-PH-001", "Да"),
        ("QA-PH-002", "Нет"),
    ]


def test_export_history_keeps_return_comment(
    client: TestClient, make_user, db: Session, make_device
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = make_device(owner=owner, inventory_no="QA-PH-001")
    closed = add_checkout(
        db,
        device,
        holder,
        expected_return_at=datetime(2026, 6, 20, 12, 0),
        returned_at=datetime(2026, 6, 25, 12, 0),
    )
    closed.taken_at = datetime(2026, 6, 10, 12, 0)
    closed.comment_in = "Царапина на корпусе"
    db.commit()

    rows = list(
        _book(client, from_date="2026-06-01", to_date="2026-06-30")[
            "История выдач"
        ].iter_rows(min_row=2, values_only=True)
    )

    assert rows[0][7] == "Царапина на корпусе"


def test_days_overdue_is_zero_on_the_deadline_day() -> None:
    """Срок «сегодня» ещё не просрочен — счётчик не должен стать 1."""
    today = now_local()

    assert days_overdue(today) == 0


def test_overdue_matches_everywhere(
    client: TestClient, make_user, db: Session, make_device
) -> None:
    """Состав просроченных одинаков в списке, отчёте и Excel (инвариант 6)."""
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    late1 = make_device(owner=owner, inventory_no="QA-PH-001")
    late2 = make_device(owner=owner, inventory_no="QA-PH-002")
    for device in (late1, late2):
        add_checkout(
            db, device, holder, expected_return_at=now_local() - timedelta(days=2)
        )
    fine = make_device(owner=owner, inventory_no="QA-PH-003")
    add_checkout(db, fine, holder, expected_return_at=now_local() + timedelta(days=2))

    overdue_rows = list(
        _book(client)["Просроченные"].iter_rows(min_row=2, values_only=True)
    )
    from_excel = {row[0] for row in overdue_rows}

    report = client.get("/reports/overdue").json()
    from_report = {row["inventory_no"] for row in report["items"]}
    listing = client.get("/devices", params={"archived": "all", "overdue": "true"}).json()
    from_list = {item["inventory_no"] for item in listing["items"]}

    assert from_excel == from_report == from_list == {"QA-PH-001", "QA-PH-002"}
