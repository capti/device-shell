"""Схемы авторизации и профиля."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


class UserProfile(BaseModel):
    """Публичный профиль — без `password_hash`."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    full_name: str
    email: str | None
    team: str | None
    telegram: str | None
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None
