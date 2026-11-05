"""Устройство: обязательный владелец, статус и уникальные идентификаторы."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.clock import now_local
from app.db import Base


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'repair', 'lost')", name="ck_devices_status"),
        # Пустые IMEI/serial не считаются дубликатами — уникальность только для заполненных.
        Index(
            "uq_devices_imei",
            "imei",
            unique=True,
            sqlite_where=text("imei IS NOT NULL AND imei <> ''"),
        ),
        Index(
            "uq_devices_serial_no",
            "serial_no",
            unique=True,
            sqlite_where=text("serial_no IS NOT NULL AND serial_no <> ''"),
        ),
        Index("ix_devices_owner_id", "owner_id"),
        Index("ix_devices_archived_at", "archived_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    inventory_no: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    serial_no: Mapped[str | None] = mapped_column(String(64))
    imei: Mapped[str | None] = mapped_column(String(32))
    brand: Mapped[str] = mapped_column(String(128), nullable=False)
    model: Mapped[str] = mapped_column(String(128), nullable=False)
    os: Mapped[str | None] = mapped_column(String(64))
    os_version: Mapped[str | None] = mapped_column(String(64))
    storage: Mapped[str | None] = mapped_column(String(64))
    color: Mapped[str | None] = mapped_column(String(64))
    device_type: Mapped[str | None] = mapped_column(String(64))
    purchase_year: Mapped[int | None] = mapped_column(Integer)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="active", server_default=text("'active'")
    )
    notes: Mapped[str | None] = mapped_column(Text)
    accounts_note: Mapped[str | None] = mapped_column(Text)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_local)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=now_local, onupdate=now_local
    )
