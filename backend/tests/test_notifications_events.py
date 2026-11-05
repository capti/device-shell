"""Триггеры уведомлений: устройства, оборот и учётные записи."""

from fastapi.testclient import TestClient
from helpers import (
    checkout,
    create_device,
    login_as,
    notification_recipients,
    notifications,
    register_user,
)
from sqlalchemy.orm import Session


def test_owner_change_by_user_notifies_active_admins(
    client: TestClient, make_user, db: Session
) -> None:
    first_admin = register_user(make_user, username="admin1", role="admin")
    second_admin = register_user(make_user, username="admin2", role="admin")
    register_user(
        make_user, username="inactive-admin", role="admin", is_active=False
    )
    owner = register_user(make_user, username="owner")
    successor = register_user(make_user, username="successor")
    login_as(client, owner)
    device = create_device(client)

    response = client.post(
        f"/devices/{device['id']}/owner", json={"owner_id": successor.id}
    )

    assert response.status_code == 200
    assert notification_recipients(db, "owner_changed") == {first_admin.id, second_admin.id}
    notification = notifications(db, type_="owner_changed")[0]
    assert notification.device_id == device["id"]
    assert notification.actor_id == owner.id


def test_owner_change_by_admin_creates_no_notification(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    register_user(make_user, username="other-admin", role="admin")
    owner = register_user(make_user, username="owner")
    successor = register_user(make_user, username="successor")
    login_as(client, owner)
    device = create_device(client)
    client.cookies.clear()
    login_as(client, admin)

    response = client.post(
        f"/devices/{device['id']}/owner", json={"owner_id": successor.id}
    )

    assert response.status_code == 200
    assert notifications(db) == []


def test_checkout_notifies_device_owner(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)

    checkout(client, device["id"], holder)

    mine = notifications(db, recipient_id=owner.id, type_="device_checked_out")
    assert len(mine) == 1
    assert mine[0].device_id == device["id"]
    assert mine[0].actor_id == owner.id
    assert notifications(db, recipient_id=holder.id) == []


def test_return_notifies_device_owner(
    client: TestClient, make_user, db: Session
) -> None:
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], holder)
    client.cookies.clear()
    login_as(client, holder)

    response = client.post(
        f"/devices/{device['id']}/return", json={"condition_in": "ok"}
    )

    assert response.status_code == 200
    assert len(notifications(db, recipient_id=owner.id, type_="device_returned")) == 1
    assert notifications(db, recipient_id=holder.id, type_="device_returned") == []


def test_archive_by_user_notifies_active_admins(
    client: TestClient, make_user, db: Session
) -> None:
    first_admin = register_user(make_user, username="admin1", role="admin")
    second_admin = register_user(make_user, username="admin2", role="admin")
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)

    response = client.post(f"/devices/{device['id']}/archive")

    assert response.status_code == 200
    assert notification_recipients(db, "device_archived") == {first_admin.id, second_admin.id}
    assert notifications(db, recipient_id=owner.id) == []


def test_archive_by_admin_creates_no_notification(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    register_user(make_user, username="other-admin", role="admin")
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)
    client.cookies.clear()
    login_as(client, admin)

    response = client.post(f"/devices/{device['id']}/archive")

    assert response.status_code == 200
    assert notifications(db) == []


def test_restore_by_user_notifies_active_admins(
    client: TestClient, make_user, db: Session
) -> None:
    first_admin = register_user(make_user, username="admin1", role="admin")
    second_admin = register_user(make_user, username="admin2", role="admin")
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)
    assert client.post(f"/devices/{device['id']}/archive").status_code == 200

    response = client.post(f"/devices/{device['id']}/restore")

    assert response.status_code == 200
    assert notification_recipients(db, "device_restored") == {first_admin.id, second_admin.id}


def test_lost_status_notifies_admins(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    other_admin = register_user(make_user, username="other-admin", role="admin")
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)

    response = client.post(f"/devices/{device['id']}/status", json={"status": "lost"})

    assert response.status_code == 200
    assert notification_recipients(db, "device_lost") == {admin.id, other_admin.id}
    assert notifications(db, recipient_id=owner.id) == []


def test_lost_status_by_admin_reaches_every_admin(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    other_admin = register_user(make_user, username="other-admin", role="admin")
    owner = register_user(make_user, username="owner")
    login_as(client, owner)
    device = create_device(client)
    client.cookies.clear()
    login_as(client, admin)

    response = client.post(f"/devices/{device['id']}/status", json={"status": "lost"})

    assert response.status_code == 200
    # Правило «все администраторы» не делает исключения для инициатора.
    assert notification_recipients(db, "device_lost") == {admin.id, other_admin.id}


def test_requires_repair_report_notifies_admins_and_owner(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    other_admin = register_user(make_user, username="other-admin", role="admin")
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], holder)
    client.cookies.clear()
    login_as(client, holder)

    response = client.post(
        f"/devices/{device['id']}/condition-reports",
        json={"condition": "not_working", "requires_repair": True},
    )

    assert response.status_code == 201
    assert notification_recipients(db, "requires_repair") == {admin.id, other_admin.id}
    assert notification_recipients(db, "condition_reported") == {owner.id}


def test_plain_report_notifies_owner_only(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    owner = register_user(make_user, username="owner")
    holder = register_user(make_user, username="holder")
    login_as(client, owner)
    device = create_device(client)
    checkout(client, device["id"], holder)
    client.cookies.clear()
    login_as(client, holder)

    response = client.post(
        f"/devices/{device['id']}/condition-reports",
        json={"condition": "ok"},
    )

    assert response.status_code == 201
    assert notification_recipients(db, "condition_reported") == {owner.id}
    assert notifications(db, recipient_id=admin.id) == []


def test_deactivation_notifies_other_admins(
    client: TestClient, make_user, db: Session
) -> None:
    acting_admin = register_user(make_user, username="admin1", role="admin")
    other_admin = register_user(make_user, username="admin2", role="admin")
    employee = register_user(make_user, username="employee")
    login_as(client, acting_admin)

    response = client.post(f"/users/{employee.id}/deactivate")

    assert response.status_code == 200
    assert notification_recipients(db, "user_deactivated") == {other_admin.id}
    assert notifications(db, recipient_id=employee.id) == []


def test_role_change_notifies_employee(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    employee = register_user(make_user, username="employee")
    login_as(client, admin)

    response = client.patch(f"/users/{employee.id}", json={"role": "admin"})

    assert response.status_code == 200
    mine = notifications(db, recipient_id=employee.id, type_="role_changed")
    assert len(mine) == 1
    assert mine[0].payload == {"role": "admin"}
    assert notifications(db, recipient_id=admin.id) == []


def test_role_unchanged_creates_no_notification(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    employee = register_user(make_user, username="employee")
    login_as(client, admin)

    response = client.patch(
        f"/users/{employee.id}", json={"full_name": "Новое Имя"}
    )

    assert response.status_code == 200
    assert notifications(db) == []


def test_password_reset_notifies_employee(
    client: TestClient, make_user, db: Session
) -> None:
    admin = register_user(make_user, username="admin", role="admin")
    employee = register_user(make_user, username="employee")
    login_as(client, admin)

    response = client.post(
        f"/users/{employee.id}/password", json={"password": "newsecret123"}
    )

    assert response.status_code == 204
    assert notification_recipients(db, "password_reset") == {employee.id}
    assert notifications(db, recipient_id=admin.id) == []


def test_own_password_change_creates_no_notification(
    client: TestClient, make_user, db: Session
) -> None:
    user = register_user(make_user, username="employee")
    login_as(client, user)

    response = client.post(
        "/auth/change-password",
        json={"current_password": "secret123", "new_password": "newsecret123"},
    )

    assert response.status_code == 204
    assert notifications(db) == []
