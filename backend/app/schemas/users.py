"""Схемы справочника сотрудников и управления паролями."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Role = Literal["admin", "user"]


def _blank_to_none(value: Any) -> Any:
    return None if value == "" else value


class UserCreate(BaseModel):
    """Создание сотрудника администратором."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    username: str = Field(min_length=1, max_length=64)
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=256)
    role: Role = "user"
    email: str | None = Field(default=None, max_length=255)
    team: str | None = Field(default=None, max_length=128)
    telegram: str | None = Field(default=None, max_length=128)

    @field_validator("email", "team", "telegram", mode="after")
    @classmethod
    def _normalize_contact(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class UserUpdate(BaseModel):
    """Правка карточки. Логин не меняется: это идентификатор входа."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: str | None = Field(default=None, max_length=255)
    team: str | None = Field(default=None, max_length=128)
    telegram: str | None = Field(default=None, max_length=128)
    role: Role | None = None

    @field_validator("email", "team", "telegram", mode="after")
    @classmethod
    def _normalize_contact(cls, value: str | None) -> str | None:
        return _blank_to_none(value)


class PasswordReset(BaseModel):
    """Сброс пароля администратором: старый пароль не требуется."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    password: str = Field(min_length=1, max_length=256)


class PasswordChange(BaseModel):
    """Смена собственного пароля с подтверждением текущего."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    current_password: str = Field(min_length=1, max_length=256)
    new_password: str = Field(min_length=1, max_length=256)


class UserRead(BaseModel):
    """Профиль сотрудника со счётчиками устройств, без хеша пароля."""

    id: int
    username: str
    full_name: str
    email: str | None
    team: str | None
    telegram: str | None
    role: Role
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
    devices_owned: int
    devices_held: int
