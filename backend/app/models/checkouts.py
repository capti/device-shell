"""История выдач устройства. Активная выдача — `returned_at IS NULL`."""

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from app.clock import now_local
from app.db import Base

_CONDITIONS = "'ok', 'scratches', 'damaged', 'not_working'"
_CLOSED_REASONS = "'returned', 'transferred', 'ownership_transferred'"


class Checkout(Base):
    __tablename__ = "checkouts"
    __table_args__ = (
        CheckConstraint(
            f"condition_out IS NULL OR condition_out IN ({_CONDITIONS})",
            name="ck_checkouts_condition_out",
        ),
        CheckConstraint(
            f"condition_in IS NULL OR condition_in IN ({_CONDITIONS})",
            name="ck_checkouts_condition_in",
        ),
        CheckConstraint(
            f"closed_reason IS NULL OR closed_reason IN ({_CLOSED_REASONS})",
            name="ck_checkouts_closed_reason",
        ),
        # Активная выдача не имеет причины закрытия, закрытая — имеет.
        CheckConstraint(
            "(returned_at IS NULL AND closed_reason IS NULL) "
            "OR (returned_at IS NOT NULL AND closed_reason IS NOT NULL)",
            name="ck_checkouts_returned_closed_reason",
        ),
        # Не более одной активной выдачи на устройство.
        Index(
            "uq_checkouts_active_device",
            "device_id",
            unique=True,
            sqlite_where=text("returned_at IS NULL"),
        ),
        Index("ix_checkouts_device_id", "device_id"),
        Index("ix_checkouts_user_id", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int] = mapped_column(
        ForeignKey("devices.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    taken_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=now_local)
    expected_return_at: Mapped[datetime | None] = mapped_column(DateTime)
    returned_at: Mapped[datetime | None] = mapped_column(DateTime)
    condition_out: Mapped[str | None] = mapped_column(String(16))
    condition_in: Mapped[str | None] = mapped_column(String(16))
    comment_out: Mapped[str | None] = mapped_column(Text)
    comment_in: Mapped[str | None] = mapped_column(Text)
    closed_reason: Mapped[str | None] = mapped_column(String(32))
    created_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
