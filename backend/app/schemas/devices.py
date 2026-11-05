"""Схемы карточки, списка и истории устройства."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

DeviceStatus = Literal["active", "repair", "lost"]
DeviceSort = Literal[
    "inventory_no",
    "-inventory_no",
    "model",
    "-model",
    "updated_at",
    "-updated_at",
]
ArchivedFilter = Literal["false", "true", "all"]


class UserBrief(BaseModel):
    """Минимальные данные сотрудника внутри карточки устройства."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str


class DeviceCreate(BaseModel):
    """Создание устройства: пустой номер получает следующий `QA-PH-NNN`."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    inventory_no: str | None = Field(default=None, max_length=64)
    serial_no: str | None = Field(default=None, max_length=64)
    imei: str | None = Field(default=None, max_length=32)
    brand: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=128)
    os: str | None = Field(default=None, max_length=64)
    os_version: str | None = Field(default=None, max_length=64)
    storage: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=64)
    device_type: str | None = Field(default=None, max_length=64)
    purchase_year: int | None = Field(default=None, ge=1980, le=2100)
    notes: str | None = None
    accounts_note: str | None = None
    owner_id: int | None = None

    @field_validator("*", mode="after")
    @classmethod
    def _blank_to_none(cls, value: Any) -> Any:
        return None if value == "" else value


class DeviceUpdate(BaseModel):
    """Изменение карточки. Владелец и статус меняются отдельными операциями."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    inventory_no: str | None = Field(default=None, max_length=64)
    serial_no: str | None = Field(default=None, max_length=64)
    imei: str | None = Field(default=None, max_length=32)
    brand: str | None = Field(default=None, min_length=1, max_length=128)
    model: str | None = Field(default=None, min_length=1, max_length=128)
    os: str | None = Field(default=None, max_length=64)
    os_version: str | None = Field(default=None, max_length=64)
    storage: str | None = Field(default=None, max_length=64)
    color: str | None = Field(default=None, max_length=64)
    device_type: str | None = Field(default=None, max_length=64)
    purchase_year: int | None = Field(default=None, ge=1980, le=2100)
    notes: str | None = None
    accounts_note: str | None = None

    @field_validator("*", mode="after")
    @classmethod
    def _blank_to_none(cls, value: Any) -> Any:
        return None if value == "" else value


class DeviceRead(BaseModel):
    """Карточка устройства вместе с вычисленным состоянием."""

    id: int
    inventory_no: str
    serial_no: str | None
    imei: str | None
    brand: str
    model: str
    os: str | None
    os_version: str | None
    storage: str | None
    color: str | None
    device_type: str | None
    purchase_year: int | None
    status: DeviceStatus
    notes: str | None
    accounts_note: str | None
    owner: UserBrief
    holder: UserBrief
    overdue: bool
    expected_return_at: datetime | None
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class DeviceListResponse(BaseModel):
    items: list[DeviceRead]
    total: int
    page: int
    page_size: int


class RestoreRequest(BaseModel):
    """Восстановление из архива: новый владелец и целевой статус."""

    model_config = ConfigDict(extra="forbid")

    owner_id: int | None = None
    status: DeviceStatus = "active"


class DeviceEventRead(BaseModel):
    id: int
    type: str
    actor: UserBrief | None
    payload: dict[str, Any] | None
    created_at: datetime
