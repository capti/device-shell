"""Схемы оборота устройства: выдача, возврат, передача, смена владельца."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.schemas.devices import UserBrief

ConditionValue = Literal["ok", "scratches", "damaged", "not_working"]
ClosedReason = Literal["returned", "transferred", "ownership_transferred"]


def _blank_to_none(value: Any) -> Any:
    return None if value == "" else value


class CheckoutCreate(BaseModel):
    """Выдача устройства другому сотруднику."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    holder_id: int
    expected_return_at: datetime | None = None
    condition_out: ConditionValue | None = None
    comment_out: str | None = None

    @field_validator("comment_out", mode="after")
    @classmethod
    def _normalize_comment(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class ReturnRequest(BaseModel):
    """Возврат: состояние обязательно, отчёт создаётся вместе с закрытием."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    condition_in: ConditionValue
    comment_in: str | None = None
    requires_repair: bool = False

    @field_validator("comment_in", mode="after")
    @classmethod
    def _normalize_comment(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class TransferRequest(BaseModel):
    """Передача телефона другому держателю без участия владельца."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    holder_id: int
    expected_return_at: datetime | None = None
    condition_in: ConditionValue | None = None
    comment: str | None = None

    @field_validator("comment", mode="after")
    @classmethod
    def _normalize_comment(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class OwnerChangeRequest(BaseModel):
    """Смена владельца устройства."""

    model_config = ConfigDict(extra="forbid")

    owner_id: int


class CheckoutRead(BaseModel):
    """Запись истории выдач с держателем и автором."""

    id: int
    device_id: int
    holder: UserBrief
    taken_at: datetime
    expected_return_at: datetime | None
    returned_at: datetime | None
    closed_reason: ClosedReason | None
    condition_out: ConditionValue | None
    condition_in: ConditionValue | None
    comment_out: str | None
    comment_in: str | None
    created_by: UserBrief | None
