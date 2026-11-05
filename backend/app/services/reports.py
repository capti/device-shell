"""Отчёты «у кого что», «просроченные», дашборд и Excel-выгрузка.

Единственная формула просрочки — в `services/device_state`; сервис здесь
только размечает строки этого запроса (инвариант 6).
"""

from datetime import date, datetime
from io import BytesIO

from openpyxl import Workbook
from openpyxl.worksheet.worksheet import Worksheet
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import Checkout, Device, User
from app.services.device_state import device_state_query, today_start
from app.services.devices import (
    DeviceListParams,
    archived_conditions,
    scope_conditions,
    search_condition,
)

TILE_LIMIT = 5

_DEVICE_HEADERS = (
    "Инв. №",
    "Производитель",
    "Модель",
    "ОС",
    "Владелец",
    "Держатель",
    "Статус",
    "Дата выдачи",
    "Ожидаемый возврат",
    "Просрочка",
)
_OVERDUE_HEADERS = (
    "Инв. №",
    "Производитель",
    "Модель",
    "Владелец",
    "Держатель",
    "Дата выдачи",
    "Ожидаемый возврат",
    "Дней просрочки",
)
_HISTORY_HEADERS = (
    "Инв. №",
    "Производитель",
    "Модель",
    "Держатель",
    "Дата выдачи",
    "Дата возврата",
    "Причина закрытия",
    "Комментарий",
)
_STATUS_LABELS = {"active": "Активно", "repair": "В ремонте", "lost": "Утерян"}


def _users_by_id(db: Session, ids) -> dict[int, User]:
    """Одним запросом словарь `id → User` для строк отчётов."""
    unique = list(dict.fromkeys(ids))
    if not unique:
        return {}
    rows = db.scalars(select(User).where(User.id.in_(unique))).all()
    return {user.id: user for user in rows}


def _names_for_rows(db: Session, rows) -> dict[int, User]:
    """Данные сотрудников по строкам state-запроса: владельцы и держатели."""
    names = _users_by_id(db, (row[0].owner_id for row in rows))
    names.update(_users_by_id(db, (row.holder_id for row in rows)))
    return names


def _person(user: User) -> dict[str, object]:
    """Данные сотрудника для строки отчёта."""
    return {"id": user.id, "username": user.username, "full_name": user.full_name}


def days_overdue(expected_return_at: datetime, today: datetime | None = None) -> int:
    """Полные сутки просрочки: разница дат возврата и сегодняшней суток."""
    moment = today or today_start()
    return max((moment.date() - expected_return_at.date()).days, 0)


def dashboard_stats(db: Session) -> dict:
    """Счётчики и топ давних просрочек одним проходом по state-запросу."""
    state = device_state_query()
    counters = dict.fromkeys(
        (
            "total_active",
            "with_owners",
            "checked_out",
            "in_repair",
            "lost",
            "archived",
            "overdue",
        ),
        0,
    )
    overdue_rows = []
    for row in db.execute(state.statement):
        device: Device = row[0]
        has_checkout = row.checkout_id is not None
        if device.archived_at is not None:
            counters["archived"] += 1
        else:
            counters["total_active"] += 1
            counters["checked_out" if has_checkout else "with_owners"] += 1
            if device.status == "repair":
                counters["in_repair"] += 1
            if device.status == "lost":
                counters["lost"] += 1
        if row.overdue == 1:
            counters["overdue"] += 1
            overdue_rows.append(row)
    overdue_rows.sort(key=_return_at_key)
    names = _users_by_id(db, (row.holder_id for row in overdue_rows[:TILE_LIMIT]))
    return {
        "counters": counters,
        "top_overdue": [_overdue_tile(names, row) for row in overdue_rows[:TILE_LIMIT]],
    }


def _return_at_key(row) -> datetime:
    return row.expected_return_at


def _overdue_tile(names: dict[int, User], row) -> dict:
    device: Device = row[0]
    return {
        "device_id": device.id,
        "inventory_no": device.inventory_no,
        "model": device.model,
        "holder": _person(names[row.holder_id]),
        "days_overdue": days_overdue(row.expected_return_at),
    }


TURNOVER_MONTHS = 12
OVERDUE_BUCKET_LABELS = ("1-7", "8-14", "15-30", "31+")


def _month_keys(moment: datetime) -> list[tuple[int, int]]:
    """Последние 12 локальных месяцев (включая текущий), старший впереди."""
    keys = []
    year, month = moment.year, moment.month
    for _ in range(TURNOVER_MONTHS):
        keys.append((year, month))
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    return list(reversed(keys))


def _monthly_counts(
    db: Session, column, months: list[tuple[int, int]]
) -> dict[tuple[int, int], int]:
    """Сколько событий пришлось на каждый месяц периода."""
    start_year, start_month = months[0]
    start = datetime(start_year, start_month, 1)
    end_year, end_month = months[-1]
    if end_month == 12:
        end = datetime(end_year + 1, 1, 1)
    else:
        end = datetime(end_year, end_month + 1, 1)
    rows = db.execute(
        select(
            func.extract("year", column),
            func.extract("month", column),
            func.count(),
        )
        .where(column.is_not(None), column >= start, column < end)
        .group_by(func.extract("year", column), func.extract("month", column))
    ).all()
    return {(int(year), int(month)): count for year, month, count in rows}


def dashboard_charts(db: Session) -> dict:
    """Динамика выдач/возвратов за 12 месяцев и корзины возраста просрочки.

    Возвраты учитываются по дате возврата независимо от даты выдачи.
    Просрочка берётся из единого state-запроса (инвариант 6).
    """
    months = _month_keys(now_local())
    issued = _monthly_counts(db, Checkout.taken_at, months)
    returned = _monthly_counts(db, Checkout.returned_at, months)

    buckets = dict.fromkeys(OVERDUE_BUCKET_LABELS, 0)
    state = device_state_query()
    for row in db.execute(state.statement.where(state.overdue == 1)):
        days = days_overdue(row.expected_return_at)
        if days <= 7:
            buckets["1-7"] += 1
        elif days <= 14:
            buckets["8-14"] += 1
        elif days <= 30:
            buckets["15-30"] += 1
        else:
            buckets["31+"] += 1

    return {
        "turnover": [
            {
                "month": f"{year:04d}-{month:02d}",
                "checked_out": issued.get((year, month), 0),
                "returned": returned.get((year, month), 0),
            }
            for year, month in months
        ],
        "overdue_buckets": [
            {"bucket": label, "count": buckets[label]} for label in OVERDUE_BUCKET_LABELS
        ],
    }


def holders_report(db: Session) -> dict:
    """«У кого что»: активные устройства с владельцем и текущим держателем."""
    state = device_state_query()
    rows = db.execute(
        state.statement.where(Device.archived_at.is_(None)).order_by(
            Device.inventory_no, Device.id
        )
    ).all()
    names = _names_for_rows(db, rows)
    items = []
    for row in rows:
        device: Device = row[0]
        items.append(
            {
                "device_id": device.id,
                "inventory_no": device.inventory_no,
                "model": device.model,
                "status": device.status,
                "owner": _person(names[device.owner_id]),
                "holder": _person(names[row.holder_id]),
            }
        )
    return {"items": items}


def overdue_report(db: Session) -> dict:
    """«Просроченные»: только устройства, удовлетворяющие правилу просрочки."""
    state = device_state_query()
    rows = db.execute(
        state.statement.where(state.overdue == 1).order_by(
            state.checkout_taken_at, Device.id
        )
    ).all()
    names = _names_for_rows(db, rows)
    items = []
    for row in rows:
        device: Device = row[0]
        items.append(
            {
                "device_id": device.id,
                "inventory_no": device.inventory_no,
                "model": device.model,
                "owner": _person(names[device.owner_id]),
                "holder": _person(names[row.holder_id]),
                "taken_at": row.checkout_taken_at,
                "expected_return_at": row.expected_return_at,
                "days_overdue": days_overdue(row.expected_return_at),
            }
        )
    return {"items": items}


def export_workbook(
    db: Session,
    *,
    viewer: User,
    params: DeviceListParams,
    from_date: date,
    to_date: date,
) -> Workbook:
    """Excel с листами «Все устройства», «Просроченные», «История выдач»."""
    workbook = Workbook()
    first_sheet = workbook.active
    first_sheet.title = "Все устройства"
    _device_sheet(db, viewer, params, first_sheet)
    _overdue_sheet(db, workbook.create_sheet("Просроченные"))
    _history_sheet(db, workbook.create_sheet("История выдач"), from_date, to_date)
    return workbook


def _rows_header(worksheet: Worksheet, headers: tuple[str, ...]) -> None:
    worksheet.append(headers)
    worksheet.freeze_panes = "A2"


def _append_row(worksheet: Worksheet, values: tuple[object, ...]) -> None:
    worksheet.append(values)
    for cell in worksheet[worksheet.max_row]:
        if isinstance(cell.value, str):
            cell.data_type = "s"


def _device_sheet(
    db: Session, viewer: User, params: DeviceListParams, worksheet: Worksheet
) -> None:
    """Лист «Все устройства» с теми же фильтрами, что список устройств."""
    state = device_state_query()
    conditions = archived_conditions(params.archived) + scope_conditions(
        state, viewer, params
    )
    if params.query:
        conditions.append(search_condition(params.query))
    rows = db.execute(
        state.statement.where(*conditions).order_by(Device.inventory_no, Device.id)
    ).all()
    names = _names_for_rows(db, rows)
    _rows_header(worksheet, _DEVICE_HEADERS)
    for row in rows:
        device: Device = row[0]
        _append_row(
            worksheet,
            (
                device.inventory_no,
                device.brand,
                device.model,
                _os_title(device),
                names[device.owner_id].full_name,
                names[row.holder_id].full_name,
                _STATUS_LABELS.get(device.status, device.status),
                _fmt_date(row.checkout_taken_at),
                _fmt_date(row.expected_return_at),
                "Да" if row.overdue == 1 else "Нет",
            )
        )


def _os_title(device: Device) -> str:
    return " ".join(part for part in (device.os, device.os_version) if part)


def _fmt_date(value: datetime | None) -> str:
    return "" if value is None else value.strftime("%d.%m.%Y")


def _overdue_sheet(db: Session, worksheet: Worksheet) -> None:
    """Лист «Просроченные» — те же строки, что отчёт `overdue_report`."""
    _rows_header(worksheet, _OVERDUE_HEADERS)
    items = overdue_report(db)["items"]
    brands = (
        dict(
            db.execute(
                select(Device.id, Device.brand).where(
                    Device.id.in_([item["device_id"] for item in items])
                )
            ).all()
        )
        if items
        else {}
    )
    for item in items:
        _append_row(
            worksheet,
            (
                item["inventory_no"],
                brands[item["device_id"]],
                item["model"],
                item["owner"]["full_name"],
                item["holder"]["full_name"],
                _fmt_date(item["taken_at"]),
                _fmt_date(item["expected_return_at"]),
                item["days_overdue"],
            )
        )


def _history_sheet(
    db: Session, worksheet: Worksheet, from_date: date, to_date: date
) -> None:
    """Лист «История выдач» за период по дате выдачи."""
    from_moment = datetime(from_date.year, from_date.month, from_date.day)
    to_moment = datetime(to_date.year, to_date.month, to_date.day, 23, 59, 59, 999999)
    statement = (
        select(Device, Checkout, User)
        .join(Device, Device.id == Checkout.device_id)
        .join(User, User.id == Checkout.user_id)
        .where(Checkout.taken_at >= from_moment, Checkout.taken_at <= to_moment)
        .order_by(Checkout.taken_at.desc(), Checkout.id.desc())
    )
    _rows_header(worksheet, _HISTORY_HEADERS)
    for device, checkout, holder_user in db.execute(statement):
        _append_row(
            worksheet,
            (
                device.inventory_no,
                device.brand,
                device.model,
                holder_user.full_name,
                _fmt_date(checkout.taken_at),
                _fmt_date(checkout.returned_at),
                checkout.closed_reason or "",
                checkout.comment_in or "",
            )
        )


def workbook_bytes(workbook: Workbook) -> bytes:
    """Сохранение книги в xlsx-байты для ответа API."""
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
