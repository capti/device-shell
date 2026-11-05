"""Аудит и таймлайн устройства: append-only, JSON payload."""

from datetime import datetime
from typing import Any

from sqlalchemy import DDL, JSON, DateTime, ForeignKey, Index, Integer, String, event
from sqlalchemy.orm import Mapped, mapped_column

from app.clock import now_local
from app.db import Base


class DeviceEvent(Base):
    __tablename__ = "device_events"
    __table_args__ = (
        Index("ix_device_events_device_created", "device_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False
    )
    # NULL — системное событие (например, автоматическая архивация).
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_local)


# SQLite не умеет запрещать UPDATE/DELETE декларативно, поэтому триггеры.
# Alembic не автогенерирует триггеры: те же операторы продублированы в миграции.
_APPEND_ONLY_TRIGGERS = (
    """
    CREATE TRIGGER trg_device_events_no_update
    BEFORE UPDATE ON device_events
    BEGIN
        SELECT RAISE(ABORT, 'device_events is append-only');
    END
    """,
    """
    CREATE TRIGGER trg_device_events_no_delete
    BEFORE DELETE ON device_events
    BEGIN
        SELECT RAISE(ABORT, 'device_events is append-only');
    END
    """,
)

for _statement in _APPEND_ONLY_TRIGGERS:
    event.listen(DeviceEvent.__table__, "after_create", DDL(_statement))
