"""Хелперы интеграционных тестов устройств: вход и вызовы API."""

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Checkout, Device, Notification, User
from app.services.passwords import hash_password

PASSWORD = "secret123"


def register_user(
    make_user,
    *,
    username: str,
    role: str = "user",
    full_name: str | None = None,
    is_active: bool = True,
) -> User:
    return make_user(
        username=username,
        full_name=full_name or username,
        role=role,
        is_active=is_active,
        password_hash=hash_password(PASSWORD),
    )


def login_as(client: TestClient, user: User) -> TestClient:
    response = client.post(
        "/auth/login", json={"username": user.username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    return client


def create_device(
    client: TestClient,
    *,
    inventory_no: str | None = None,
    brand: str = "Samsung",
    model: str = "Galaxy S23",
    **extra,
) -> dict:
    payload = {"brand": brand, "model": model, **extra}
    if inventory_no is not None:
        payload["inventory_no"] = inventory_no
    response = client.post("/devices", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def add_checkout(
    db: Session,
    device: Device,
    holder: User,
    *,
    expected_return_at: datetime | None = None,
    returned_at: datetime | None = None,
) -> Checkout:
    checkout = Checkout(
        device_id=device.id,
        user_id=holder.id,
        taken_at=now_local(),
        expected_return_at=expected_return_at,
        returned_at=returned_at,
        closed_reason="returned" if returned_at is not None else None,
    )
    db.add(checkout)
    db.commit()
    return checkout


def checkout(
    client: TestClient,
    device_id: int,
    holder: User,
    **extra,
) -> dict:
    """Выдаёт устройство через API и возвращает карточку."""
    payload = {"holder_id": holder.id, **extra}
    response = client.post(f"/devices/{device_id}/checkout", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def notifications(
    db: Session, *, recipient_id: int | None = None, type_: str | None = None
) -> list[Notification]:
    """Уведомления из БД: фильтры по адресату и типу, порядок по id."""
    statement = select(Notification)
    if recipient_id is not None:
        statement = statement.where(Notification.recipient_id == recipient_id)
    if type_ is not None:
        statement = statement.where(Notification.type == type_)
    return list(db.scalars(statement.order_by(Notification.id)).all())


def notification_recipients(db: Session, type_: str) -> set[int]:
    """Кто получил уведомления данного типа."""
    return {item.recipient_id for item in notifications(db, type_=type_)}

