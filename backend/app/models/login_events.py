"""Журнал входов: append-only, хранит каждую попытку входа.

Спека `audit-log` требует бессрочного хранения записей аудита, поэтому
таблица защищена теми же триггерами, что `device_events`.
"""

from datetime import datetime

from sqlalchemy import (
    DDL,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    event,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.clock import now_local
from app.db import Base


class LoginEvent(Base):
    __tablename__ = "login_events"
    __table_args__ = (
        Index("ix_login_events_created_at", "created_at"),
        Index("ix_login_events_username_attempted", "username_attempted"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Введённый логин: сохраняется как есть, даже если пользователя нет.
    # Длина совпадает с users.username и с max_length в LoginRequest.
    username_attempted: Mapped[str] = mapped_column(String(64), nullable=False)
    # NULL — под этим логином пользователя нет.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Причина отказа: invalid_credentials / inactive_user / rate_limited.
    # При успехе — NULL.
    reason: Mapped[str | None] = mapped_column(String(32))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_local)


# SQLite не умеет запрещать UPDATE/DELETE декларативно, поэтому триггеры.
# Alembic не автогенерирует триггеры: те же операторы продублированы в миграции.
_APPEND_ONLY_TRIGGERS = (
    """
    CREATE TRIGGER trg_login_events_no_update
    BEFORE UPDATE ON login_events
    BEGIN
        SELECT RAISE(ABORT, 'login_events is append-only');
    END
    """,
    """
    CREATE TRIGGER trg_login_events_no_delete
    BEFORE DELETE ON login_events
    BEGIN
        SELECT RAISE(ABORT, 'login_events is append-only');
    END
    """,
)

for _statement in _APPEND_ONLY_TRIGGERS:
    event.listen(LoginEvent.__table__, "after_create", DDL(_statement))
