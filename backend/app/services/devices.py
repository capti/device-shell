"""Бизнес-логика карточки устройства: создание, правка, архив, поиск, история."""

from dataclasses import dataclass

from sqlalchemy import ColumnElement, Row, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import now_local
from app.errors import AppError
from app.models import Checkout, Device, DeviceEvent, User
from app.schemas.devices import DeviceCreate, DeviceUpdate, RestoreRequest
from app.services.access import ensure_can_manage
from app.services.device_state import (
    DeviceStateQuery,
    active_checkout,
    device_state_query,
    record_event,
)
from app.services.history import device_history
from app.services.lookup import get_device
from app.services.notifications import (
    DEVICE_ARCHIVED,
    DEVICE_RESTORED,
    notify_admins,
)

INVENTORY_PREFIX = "QA-PH-"

_SEARCH_COLUMNS = (
    Device.inventory_no,
    Device.imei,
    Device.serial_no,
    Device.model,
    Device.brand,
)

_SORT_COLUMNS = {
    "inventory_no": Device.inventory_no.asc(),
    "-inventory_no": Device.inventory_no.desc(),
    "model": Device.model.asc(),
    "-model": Device.model.desc(),
    "updated_at": Device.updated_at.asc(),
    "-updated_at": Device.updated_at.desc(),
}

_UNIQUE_CHECKS = (
    (
        Device.inventory_no,
        "inventory_no",
        "INVENTORY_TAKEN",
        "Устройство с инвентарным номером {value} уже существует",
    ),
    (Device.imei, "imei", "IMEI_TAKEN", "Устройство с IMEI {value} уже существует"),
    (
        Device.serial_no,
        "serial_no",
        "SERIAL_TAKEN",
        "Устройство с serial {value} уже существует",
    ),
)


@dataclass(frozen=True)
class DeviceListParams:
    query: str | None = None
    status: str | None = None
    owner_id: int | None = None
    holder_id: int | None = None
    overdue: bool | None = None
    mine: bool = False
    archived: str = "false"
    sort: str = "inventory_no"
    page: int = 1
    page_size: int = 25


def get_device_row(db: Session, device_id: int) -> Row:
    state = device_state_query()
    row = db.execute(state.statement.where(Device.id == device_id)).first()
    if row is None:
        raise AppError("DEVICE_NOT_FOUND", "Устройство не найдено", 404)
    return row


def next_inventory_no(db: Session) -> str:
    """Следующий свободный номер `QA-PH-NNN`, учитывая архивные устройства."""
    existing = db.scalars(
        select(Device.inventory_no).where(Device.inventory_no.like(f"{INVENTORY_PREFIX}%"))
    ).all()
    highest = 0
    for value in existing:
        suffix = value[len(INVENTORY_PREFIX) :]
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"{INVENTORY_PREFIX}{highest + 1:03d}"


def _ensure_unique(
    db: Session,
    *,
    inventory_no: str | None,
    imei: str | None,
    serial_no: str | None,
    exclude_id: int | None = None,
) -> None:
    values = {"inventory_no": inventory_no, "imei": imei, "serial_no": serial_no}
    for column, field, code, message in _UNIQUE_CHECKS:
        value = values[field]
        if value is None:
            continue
        statement = select(Device.id).where(column == value)
        if exclude_id is not None:
            statement = statement.where(Device.id != exclude_id)
        if db.scalar(statement) is not None:
            raise AppError(code, message.format(value=value), 409)


def _resolve_owner(db: Session, owner_id: int | None, actor: User) -> User:
    target_id = actor.id if owner_id is None else owner_id
    if target_id != actor.id and actor.role != "admin":
        raise AppError(
            "FORBIDDEN",
            "Назначать владельцем другого сотрудника может только администратор",
            403,
        )
    owner = db.get(User, target_id)
    if owner is None or not owner.is_active:
        raise AppError("OWNER_INACTIVE", "Владелец не найден или деактивирован", 422)
    return owner


def _commit_device(db: Session, device: Device) -> Device:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            "CONFLICT",
            "Устройство с такими идентификаторами уже существует",
            409,
        ) from exc
    db.refresh(device)
    return device


def create_device(db: Session, payload: DeviceCreate, actor: User) -> Device:
    owner = _resolve_owner(db, payload.owner_id, actor)
    inventory_no = payload.inventory_no or next_inventory_no(db)
    _ensure_unique(
        db, inventory_no=inventory_no, imei=payload.imei, serial_no=payload.serial_no
    )

    device = Device(
        inventory_no=inventory_no,
        serial_no=payload.serial_no,
        imei=payload.imei,
        brand=payload.brand,
        model=payload.model,
        os=payload.os,
        os_version=payload.os_version,
        storage=payload.storage,
        color=payload.color,
        device_type=payload.device_type,
        purchase_year=payload.purchase_year,
        notes=payload.notes,
        accounts_note=payload.accounts_note,
        owner_id=owner.id,
        status="active",
        created_by=actor.id,
    )
    db.add(device)
    try:
        db.flush()
        record_event(
            db,
            device_id=device.id,
            actor_id=actor.id,
            event_type="created",
            payload={"inventory_no": inventory_no, "owner_id": owner.id},
        )
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            "CONFLICT",
            "Устройство с такими идентификаторами уже существует",
            409,
        ) from exc
    return _commit_device(db, device)


def update_device(
    db: Session, device: Device, payload: DeviceUpdate, actor: User
) -> Device:
    ensure_can_manage(device, actor)
    if device.archived_at is not None:
        raise AppError(
            "DEVICE_ARCHIVED",
            "Устройство в архиве: сначала восстановите его",
            409,
        )

    changes = payload.model_dump(exclude_unset=True)
    if "inventory_no" in changes and not changes["inventory_no"]:
        raise AppError("VALIDATION_ERROR", "Укажите инвентарный номер", 422)

    _ensure_unique(
        db,
        inventory_no=changes.get("inventory_no"),
        imei=changes.get("imei"),
        serial_no=changes.get("serial_no"),
        exclude_id=device.id,
    )

    diff: dict[str, dict[str, object]] = {}
    for field, value in changes.items():
        previous = getattr(device, field)
        if previous != value:
            diff[field] = {"from": previous, "to": value}
            setattr(device, field, value)
    if not diff:
        return device

    record_event(
        db,
        device_id=device.id,
        actor_id=actor.id,
        event_type="updated",
        payload={"changes": diff},
    )
    return _commit_device(db, device)


def has_active_checkout(db: Session, device_id: int) -> bool:
    return active_checkout(db, device_id) is not None


def archive_device(db: Session, device: Device, actor: User) -> Device:
    ensure_can_manage(device, actor)
    if device.archived_at is not None:
        raise AppError("ALREADY_ARCHIVED", "Устройство уже в архиве", 409)
    if has_active_checkout(db, device.id):
        raise AppError(
            "ACTIVE_CHECKOUT",
            "Сначала примите телефон у держателя",
            409,
        )

    device.archived_at = now_local()
    record_event(db, device_id=device.id, actor_id=actor.id, event_type="archived")
    if actor.role != "admin":
        notify_admins(db, device, type=DEVICE_ARCHIVED, actor_id=actor.id)
    return _commit_device(db, device)


def _restore_owner(
    db: Session, device: Device, owner_id: int | None, actor: User
) -> None:
    """Проверяет владельца при восстановлении и пишет событие при смене."""
    if owner_id is None:
        owner = db.get(User, device.owner_id)
        if owner is None or not owner.is_active:
            raise AppError(
                "OWNER_REQUIRED",
                "Прежний владелец деактивирован — выберите нового",
                422,
            )
        return

    if actor.role != "admin" and owner_id != device.owner_id:
        raise AppError(
            "FORBIDDEN",
            "Назначать нового владельца может только администратор",
            403,
        )
    new_owner = db.get(User, owner_id)
    if new_owner is None or not new_owner.is_active:
        raise AppError("OWNER_INACTIVE", "Владелец не найден или деактивирован", 422)
    if new_owner.id == device.owner_id:
        return

    previous_owner_id = device.owner_id
    device.owner_id = new_owner.id
    record_event(
        db,
        device_id=device.id,
        actor_id=actor.id,
        event_type="owner_changed",
        payload={"from": previous_owner_id, "to": new_owner.id},
    )


def restore_device(
    db: Session, device: Device, payload: RestoreRequest, actor: User
) -> Device:
    ensure_can_manage(device, actor)
    if device.archived_at is None:
        raise AppError("NOT_ARCHIVED", "Устройство не в архиве", 409)

    _restore_owner(db, device, payload.owner_id, actor)
    device.archived_at = None
    device.status = payload.status
    record_event(
        db,
        device_id=device.id,
        actor_id=actor.id,
        event_type="restored",
        payload={"status": payload.status},
    )
    if actor.role != "admin":
        notify_admins(db, device, type=DEVICE_RESTORED, actor_id=actor.id)
    return _commit_device(db, device)


def _text_match(column: ColumnElement[str], needle: str) -> ColumnElement[bool]:
    return func.casefold(column).contains(needle, autoescape=True)


def _user_match(needle: str) -> ColumnElement[bool]:
    return or_(
        _text_match(User.full_name, needle),
        _text_match(User.username, needle),
    )


def search_condition(query: str) -> ColumnElement[bool]:
    """Поиск по идентификаторам, модели, бренду и ФИО владельца или держателя."""
    needle = query.strip().casefold()
    device_match = or_(*[_text_match(column, needle) for column in _SEARCH_COLUMNS])
    owner_match = Device.owner_id.in_(select(User.id).where(_user_match(needle)))
    holder_match = Device.id.in_(
        select(Checkout.device_id)
        .join(User, User.id == Checkout.user_id)
        .where(Checkout.returned_at.is_(None), _user_match(needle))
    )
    return or_(device_match, owner_match, holder_match)


def archived_conditions(archived: str) -> list[ColumnElement[bool]]:
    if archived == "true":
        return [Device.archived_at.is_not(None)]
    if archived == "all":
        return []
    return [Device.archived_at.is_(None)]


def scope_conditions(
    state: DeviceStateQuery, viewer: User, params: DeviceListParams
) -> list[ColumnElement[bool]]:
    conditions: list[ColumnElement[bool]] = []
    if params.status is not None:
        conditions.append(Device.status == params.status)
    if params.owner_id is not None:
        conditions.append(Device.owner_id == params.owner_id)
    if params.holder_id is not None:
        conditions.append(state.holder_id == params.holder_id)
    if params.overdue is not None:
        conditions.append(state.overdue == (1 if params.overdue else 0))
    if params.mine:
        conditions.append(
            or_(Device.owner_id == viewer.id, state.holder_id == viewer.id)
        )
    return conditions


def list_devices(
    db: Session, viewer: User, params: DeviceListParams
) -> tuple[list[Row], int]:
    state = device_state_query()
    conditions = archived_conditions(params.archived) + scope_conditions(
        state, viewer, params
    )
    if params.query:
        conditions.append(search_condition(params.query))

    base = state.statement.where(*conditions)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    rows = db.execute(
        base.order_by(_SORT_COLUMNS[params.sort], Device.id)
        .offset((params.page - 1) * params.page_size)
        .limit(params.page_size)
    ).all()
    return rows, total


def get_history(db: Session, device_id: int) -> list[DeviceEvent]:
    get_device(db, device_id)
    return device_history(db, DeviceEvent, device_id, DeviceEvent.created_at)
