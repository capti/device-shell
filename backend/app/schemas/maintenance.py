"""Схемы обслуживания устройства: статусы, ремонты, отчёты о состоянии."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.devices import UserBrief
from app.schemas.photos import PhotoRead
from app.schemas.rotation import ConditionValue

StatusValue = Literal["lost", "active"]


def _blank_to_none(value: Any) -> Any:
    return None if value == "" else value


class StatusChangeRequest(BaseModel):
    """Перевод в `lost` и возврат из `lost`; `repair` меняется только журналом."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    status: StatusValue
    comment: str | None = None

    @field_validator("comment", mode="after")
    @classmethod
    def _normalize_comment(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class RepairCreate(BaseModel):
    """Отправка устройства в ремонт."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    service: str | None = Field(default=None, max_length=255)
    description: str | None = None
    cost: Decimal | None = Field(default=None, ge=0)
    comment: str | None = None

    @field_validator("*", mode="after")
    @classmethod
    def _normalize_blank(cls, value: Any) -> Any:
        return _blank_to_none(value)


class RepairFinishRequest(BaseModel):
    """Завершение ремонта."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    returned_at: datetime | None = None
    comment: str | None = None

    @field_validator("comment", mode="after")
    @classmethod
    def _normalize_comment(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class RepairRead(BaseModel):
    """Запись журнала ремонтов."""

    id: int
    device_id: int
    sent_at: datetime
    returned_at: datetime | None
    service: str | None
    description: str | None
    cost: Decimal | None
    comment: str | None
    created_by: UserBrief | None


class ConditionReportCreate(BaseModel):
    """Отчёт о состоянии без закрытия выдачи."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    condition: ConditionValue
    requires_repair: bool = False
    comment: str | None = None

    @field_validator("comment", mode="after")
    @classmethod
    def _normalize_comment(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class ConditionReportRead(BaseModel):
    """Сохранённый отчёт о состоянии с автором."""

    id: int
    device_id: int
    checkout_id: int | None
    author: UserBrief
    condition: ConditionValue
    requires_repair: bool
    comment: str | None
    photos: list[PhotoRead] = Field(default_factory=list)
    created_at: datetime
