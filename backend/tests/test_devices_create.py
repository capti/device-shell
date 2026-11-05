"""Создание устройства: обязательные поля, владелец, уникальность, карточка."""

from fastapi.testclient import TestClient
from helpers import create_device, login_as, register_user


def test_create_requires_model(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="creator"))

    response = client.post("/devices", json={"brand": "Samsung"})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert "model" in response.json()["message"]


def test_create_rejects_status_field(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="creator"))

    response = client.post(
        "/devices", json={"brand": "Samsung", "model": "Galaxy S23", "status": "lost"}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_create_assigns_creator_as_owner(client: TestClient, make_user) -> None:
    creator = register_user(make_user, username="creator", full_name="Иван Петров")
    login_as(client, creator)

    body = create_device(client)

    assert body["owner"]["id"] == creator.id
    assert body["holder"]["id"] == creator.id
    assert body["status"] == "active"
    assert body["overdue"] is False
    assert body["archived_at"] is None


def test_user_cannot_assign_another_owner(client: TestClient, make_user) -> None:
    creator = register_user(make_user, username="creator")
    other = register_user(make_user, username="other")
    login_as(client, creator)

    response = client.post(
        "/devices",
        json={"brand": "Samsung", "model": "Galaxy S23", "owner_id": other.id},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_admin_can_assign_another_owner(
    client: TestClient, make_client, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    login_as(client, admin)

    body = create_device(client, owner_id=owner.id)

    assert body["owner"]["id"] == owner.id


def test_deactivated_owner_is_rejected(
    client: TestClient, make_user
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    inactive = register_user(make_user, username="inactive", is_active=False)
    login_as(client, admin)

    response = client.post(
        "/devices",
        json={"brand": "Samsung", "model": "Galaxy S23", "owner_id": inactive.id},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "OWNER_INACTIVE"


def test_inventory_number_is_generated(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="creator"))

    first = create_device(client)
    second = create_device(client)

    assert first["inventory_no"] == "QA-PH-001"
    assert second["inventory_no"] == "QA-PH-002"


def test_inventory_generation_skips_taken_numbers(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="creator"))
    create_device(client, inventory_no="QA-PH-007")

    body = create_device(client)

    assert body["inventory_no"] == "QA-PH-008"


def test_duplicate_inventory_number_is_rejected(
    client: TestClient, make_user
) -> None:
    login_as(client, register_user(make_user, username="creator"))
    create_device(client, inventory_no="QA-PH-100")

    response = client.post(
        "/devices",
        json={"inventory_no": "QA-PH-100", "brand": "Samsung", "model": "Galaxy S23"},
    )

    assert response.status_code == 409
    assert response.json()["code"] == "INVENTORY_TAKEN"
    assert "QA-PH-100" in response.json()["message"]


def test_duplicate_imei_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="creator"))
    create_device(client, imei="356938035643809")

    response = client.post(
        "/devices",
        json={
            "inventory_no": "QA-PH-002",
            "brand": "Samsung",
            "model": "Galaxy S23",
            "imei": "356938035643809",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "IMEI_TAKEN"


def test_duplicate_serial_is_rejected(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="creator"))
    create_device(client, serial_no="SN-1")

    response = client.post(
        "/devices",
        json={
            "inventory_no": "QA-PH-002",
            "brand": "Samsung",
            "model": "Galaxy S23",
            "serial_no": "SN-1",
        },
    )

    assert response.status_code == 409
    assert response.json()["code"] == "SERIAL_TAKEN"


def test_devices_without_imei_are_allowed(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="creator"))

    first = create_device(client)
    second = create_device(client)

    assert first["imei"] is None
    assert second["imei"] is None


def test_card_and_list_return_device(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="creator"))
    created = create_device(client, brand="Google", model="Pixel 8")

    card = client.get(f"/devices/{created['id']}")
    listing = client.get("/devices")

    assert card.status_code == 200
    assert card.json()["brand"] == "Google"
    assert card.json()["owner"]["username"] == "creator"

    body = listing.json()
    assert body["total"] == 1
    assert body["page"] == 1
    assert body["page_size"] == 25
    assert body["items"][0]["id"] == created["id"]
    assert body["items"][0]["holder"]["username"] == "creator"


def test_missing_device_returns_404(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="creator"))

    response = client.get("/devices/999")

    assert response.status_code == 404
    assert response.json()["code"] == "DEVICE_NOT_FOUND"


def test_devices_require_session(client: TestClient) -> None:
    assert client.get("/devices").status_code == 401
    assert client.post("/devices", json={"brand": "Samsung", "model": "X"}).status_code == 401
    assert client.get("/devices/1").status_code == 401
