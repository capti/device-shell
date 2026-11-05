"""Отчёты о состоянии, журнал ремонтов и фотографии устройств."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.clock import now_local
from app.db import Base

_CONDITIONS = "'ok', 'scratches', 'damaged', 'not_working'"


class ConditionReport(Base):
    __tablename__ = "condition_reports"
    __table_args__ = (
        CheckConstraint(
            f"condition IN ({_CONDITIONS})",
            name="ck_condition_reports_condition",
        ),
        Index("ix_condition_reports_device_id", "device_id"),
        Index("ix_condition_reports_checkout_id", "checkout_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False
    )
    checkout_id: Mapped[int | None] = mapped_column(
        ForeignKey("checkouts.id", ondelete="RESTRICT")
    )
    author_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    condition: Mapped[str] = mapped_column(String(16), nullable=False)
    requires_repair: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("0")
    )
    comment: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_local)


class Repair(Base):
    __tablename__ = "repairs"
    __table_args__ = (
        Index("ix_repairs_device_id", "device_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_local)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime)
    service: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    cost: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    comment: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )


class DevicePhoto(Base):
    __tablename__ = "device_photos"
    __table_args__ = (
        Index("ix_device_photos_device_id", "device_id"),
        Index("ix_device_photos_report_id", "report_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False
    )
    report_id: Mapped[int | None] = mapped_column(
        ForeignKey("condition_reports.id", ondelete="RESTRICT")
    )
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    thumb_path: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_local)
