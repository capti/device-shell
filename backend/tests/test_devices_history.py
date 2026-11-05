"""История устройства: состав, порядок и доступ."""

from fastapi.testclient import TestClient
from helpers import create_device, login_as, register_user


def test_history_lists_events_newest_first(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))
    device = create_device(client)
    client.patch(f"/devices/{device['id']}", json={"model": "Pixel 9"})
    client.post(f"/devices/{device['id']}/archive")
    client.post(f"/devices/{device['id']}/restore", json={})

    response = client.get(f"/devices/{device['id']}/history")

    assert response.status_code == 200
    events = response.json()
    assert [event["type"] for event in events] == [
        "restored",
        "archived",
        "updated",
        "created",
    ]
    assert events[-1]["actor"]["username"] == "owner"
    assert events[1]["payload"] is None


def test_history_is_visible_to_any_authenticated_user(
    client: TestClient, make_user
) -> None:
    owner = register_user(make_user, username="owner")
    stranger = register_user(make_user, username="stranger")
    login_as(client, owner)
    device = create_device(client)

    client.cookies.clear()
    login_as(client, stranger)
    response = client.get(f"/devices/{device['id']}/history")

    assert response.status_code == 200
    assert response.json()[0]["type"] == "created"


def test_history_requires_session(client: TestClient) -> None:
    response = client.get("/devices/1/history")

    assert response.status_code == 401


def test_history_of_missing_device_is_404(client: TestClient, make_user) -> None:
    login_as(client, register_user(make_user, username="owner"))

    response = client.get("/devices/999/history")

    assert response.status_code == 404
    assert response.json()["code"] == "DEVICE_NOT_FOUND"
