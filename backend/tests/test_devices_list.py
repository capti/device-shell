"""Список устройств: поиск, фильтры, сортировка и пагинация."""

from datetime import timedelta

from fastapi.testclient import TestClient
from helpers import add_checkout, create_device, login_as, register_user
from sqlalchemy.orm import Session

from app.models import Device
from app.services.device_state import today_start


def _ids(response) -> list[int]:
    return [item["id"] for item in response.json()["items"]]


def test_search_by_imei(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    with_imei = create_device(client, inventory_no="QA-PH-001", imei="356938035643809")
    create_device(client, inventory_no="QA-PH-002", imei="351000000000008")

    response = client.get("/devices", params={"q": "643809"})

    assert _ids(response) == [with_imei["id"]]


def test_search_treats_wildcards_literally(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    create_device(client, inventory_no="QA-PH-001")
    create_device(client, inventory_no="QA-PH-002")

    percent = client.get("/devices", params={"q": "%"})
    underscore = client.get("/devices", params={"q": "QA_PH"})

    assert percent.json()["total"] == 0
    assert underscore.json()["total"] == 0


def test_search_by_owner_name_ignores_case(client: TestClient, make_user) -> None:
    owner = register_user(
        make_user, username="ivanov", full_name="Иван Петров"
    )
    login_as(client, owner)
    own = create_device(client, inventory_no="QA-PH-001")

    response = client.get("/devices", params={"q": "иван"})

    assert _ids(response) == [own["id"]]


def test_search_by_holder_name(client: TestClient, make_user, db: Session) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder", full_name="Мария Сидорова")
    login_as(client, owner)
    device = create_device(client, inventory_no="QA-PH-001")
    add_checkout(db, db.get(Device, device["id"]), holder)

    response = client.get("/devices", params={"q": "сидорова"})

    assert _ids(response) == [device["id"]]
    assert response.json()["items"][0]["holder"]["id"] == holder.id


def test_filter_by_status(client: TestClient, make_user, db: Session) -> None:
    login_as(client, register_user(make_user, username="owner"))
    create_device(client, inventory_no="QA-PH-001")
    repair = create_device(client, inventory_no="QA-PH-002")
    stored = db.get(Device, repair["id"])
    stored.status = "repair"
    db.commit()

    response = client.get("/devices", params={"status": "repair"})

    assert _ids(response) == [repair["id"]]


def test_filter_by_owner(client: TestClient, make_user) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    first = register_user(make_user, username="first")
    second = register_user(make_user, username="second")
    login_as(client, admin)
    create_device(client, inventory_no="QA-PH-001", owner_id=first.id)
    other = create_device(client, inventory_no="QA-PH-002", owner_id=second.id)

    response = client.get("/devices", params={"owner_id": second.id})

    assert _ids(response) == [other["id"]]


def test_filter_by_holder(client: TestClient, make_user, db: Session) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    add_checkout(db, db.get(Device, device["id"]), holder)

    by_holder = client.get("/devices", params={"holder_id": holder.id})
    by_owner = client.get("/devices", params={"owner_id": holder.id})

    assert _ids(by_holder) == [device["id"]]
    assert by_owner.json()["total"] == 0


def test_filter_mine_includes_owned_and_held(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    other = register_user(make_user, username="other")
    login_as(client, admin)
    owned = create_device(client, inventory_no="QA-PH-001", owner_id=owner.id)
    foreign = create_device(client, inventory_no="QA-PH-002", owner_id=other.id)
    lent = create_device(client, inventory_no="QA-PH-003", owner_id=owner.id)
    add_checkout(db, db.get(Device, foreign["id"]), owner)
    add_checkout(db, db.get(Device, lent["id"]), other)

    client.cookies.clear()
    login_as(client, owner)
    response = client.get("/devices", params={"mine": True})

    assert set(_ids(response)) == {owned["id"], foreign["id"], lent["id"]}


def test_filter_overdue(client: TestClient, make_user, db: Session) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    overdue = create_device(client, inventory_no="QA-PH-001")
    on_time = create_device(client, inventory_no="QA-PH-002")
    add_checkout(
        db,
        db.get(Device, overdue["id"]),
        holder,
        expected_return_at=today_start() - timedelta(days=1),
    )
    add_checkout(
        db,
        db.get(Device, on_time["id"]),
        holder,
        expected_return_at=today_start() + timedelta(days=3),
    )

    response = client.get("/devices", params={"overdue": True})
    not_overdue = client.get("/devices", params={"overdue": False})

    assert _ids(response) == [overdue["id"]]
    assert _ids(not_overdue) == [on_time["id"]]


def test_archived_filter(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    active = create_device(client, inventory_no="QA-PH-001")
    archived = create_device(client, inventory_no="QA-PH-002")
    assert client.post(f"/devices/{archived['id']}/archive").status_code == 200

    only_archived = client.get("/devices", params={"archived": "true"})
    both = client.get("/devices", params={"archived": "all"})

    assert _ids(only_archived) == [archived["id"]]
    assert set(_ids(both)) == {active["id"], archived["id"]}


def test_sorting_and_pagination(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    for number in ("001", "002", "003"):
        create_device(client, inventory_no=f"QA-PH-{number}")

    first_page = client.get("/devices", params={"page_size": 1})
    second_page = client.get("/devices", params={"page_size": 1, "page": 2})
    descending = client.get("/devices", params={"page_size": 1, "sort": "-inventory_no"})

    assert first_page.json()["total"] == 3
    assert second_page.json()["total"] == 3
    assert first_page.json()["items"][0]["inventory_no"] == "QA-PH-001"
    assert second_page.json()["items"][0]["inventory_no"] == "QA-PH-002"
    assert descending.json()["items"][0]["inventory_no"] == "QA-PH-003"


def test_pagination_offset_scales_with_page_size(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))
    for number in ("001", "002", "003", "004"):
        create_device(client, inventory_no=f"QA-PH-{number}")

    second_page = client.get("/devices", params={"page_size": 2, "page": 2})

    assert second_page.json()["total"] == 4
    assert [item["inventory_no"] for item in second_page.json()["items"]] == [
        "QA-PH-003",
        "QA-PH-004",
    ]


def test_invalid_sort_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))

    response = client.get("/devices", params={"sort": "price"})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_list_and_card_share_state(client: TestClient, make_user, db: Session) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder", full_name="Мария Сидорова")
    login_as(client, owner)
    device = create_device(client)
    add_checkout(
        db,
        db.get(Device, device["id"]),
        holder,
        expected_return_at=today_start() - timedelta(days=2),
    )

    listed = client.get("/devices").json()["items"][0]
    card = client.get(f"/devices/{device['id']}").json()

    assert listed["holder"]["id"] == holder.id
    assert listed["overdue"] is True
    assert (listed["holder"], listed["overdue"]) == (card["holder"], card["overdue"])


def test_page_size_is_limited(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))

    response = client.get("/devices", params={"page_size": 500})

    assert response.status_code == 422


def test_page_and_page_size_must_be_positive(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="owner"))

    zero_page = client.get("/devices", params={"page": 0})
    zero_page_size = client.get("/devices", params={"page_size": 0})

    assert zero_page.status_code == 422
    assert zero_page.json()["code"] == "VALIDATION_ERROR"
    assert zero_page_size.status_code == 422
    assert zero_page_size.json()["code"] == "VALIDATION_ERROR"
