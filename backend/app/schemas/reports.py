"""Схемы дашборда и отчётов «у кого что» и «просроченные»."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.schemas.devices import UserBrief

DeviceStatus = Literal["active", "repair", "lost"]


class Counters(BaseModel):
    """Счётчики дашборда по вычисляемому состоянию устройств."""

    total_active: int
    with_owners: int
    checked_out: int
    in_repair: int
    lost: int
    archived: int
    overdue: int


class DashboardRow(BaseModel):
    """Строка топа просрочек дашборда: «самая давная» просрочка на экране."""

    device_id: int
    inventory_no: str
    model: str
    holder: UserBrief
    days_overdue: int


class DashboardStats(BaseModel):
    """Ответ дашборда: счётчики и топ-5 просрочек."""

    counters: Counters
    top_overdue: list[DashboardRow]


class TurnoverPoint(BaseModel):
    """Месяц динамики: сколько устройств выдали и сколько вернули."""

    month: str
    checked_out: int
    returned: int


class OverdueBucket(BaseModel):
    """Корзина возраста просрочки: полные дни срока возврата."""

    bucket: str
    count: int


class DashboardCharts(BaseModel):
    """Агрегаты для графиков дашборда."""

    turnover: list[TurnoverPoint]
    overdue_buckets: list[OverdueBucket]


class HolderRow(BaseModel):
    """Строка отчёта «у кого что»: устройство, владелец и держатель."""

    model_config = ConfigDict(from_attributes=True)

    device_id: int
    inventory_no: str
    model: str
    status: DeviceStatus
    owner: UserBrief
    holder: UserBrief


class HoldersReport(BaseModel):
    """Ответ отчёта «у кого что»."""

    items: list[HolderRow]


class OverdueRow(BaseModel):
    """Строка отчёта «просроченные»: выдача, срок и длительность просрочки."""

    model_config = ConfigDict(from_attributes=True)

    device_id: int
    inventory_no: str
    model: str
    owner: UserBrief
    holder: UserBrief
    taken_at: datetime
    expected_return_at: datetime
    days_overdue: int


class OverdueReport(BaseModel):
    """Ответ отчёта «просроченные»."""

    items: list[OverdueRow]

