"""Преобразование ORM-объектов в схемы ответа API."""

from collections.abc import Iterable, Sequence

from sqlalchemy import Row, select
from sqlalchemy.orm import Session

from app.models import Device, User
from app.schemas.devices import DeviceRead, UserBrief
from app.services.devices import get_device_row


def user_brief(user: User) -> UserBrief:
    return UserBrief.model_validate(user)


def users_by_id(db: Session, ids: Iterable[int | None]) -> dict[int, User]:
    unique = {user_id for user_id in ids if user_id is not None}
    if not unique:
        return {}
    users = db.scalars(select(User).where(User.id.in_(unique))).all()
    return {user.id: user for user in users}


def device_read(row: Row, users: dict[int, User]) -> DeviceRead:
    device: Device = row[0]
    return DeviceRead(
        id=device.id,
        inventory_no=device.inventory_no,
        serial_no=device.serial_no,
        imei=device.imei,
        brand=device.brand,
        model=device.model,
        os=device.os,
        os_version=device.os_version,
        storage=device.storage,
        color=device.color,
        device_type=device.device_type,
        purchase_year=device.purchase_year,
        status=device.status,
        notes=device.notes,
        accounts_note=device.accounts_note,
        owner=user_brief(users[device.owner_id]),
        holder=user_brief(users[row.holder_id]),
        overdue=bool(row.overdue),
        expected_return_at=row.expected_return_at,
        archived_at=device.archived_at,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


def device_reads(db: Session, rows: Sequence[Row]) -> list[DeviceRead]:
    users = users_by_id(
        db,
        [row[0].owner_id for row in rows] + [row.holder_id for row in rows],
    )
    return [device_read(row, users) for row in rows]


def device_card(db: Session, device_id: int) -> DeviceRead:
    return device_reads(db, [get_device_row(db, device_id)])[0]
