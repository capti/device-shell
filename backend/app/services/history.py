"""Обратный хронологический порядок записей, привязанных к устройству."""

from sqlalchemy import ColumnElement
from sqlalchemy.orm import Session
from sqlalchemy.sql import select


def device_history[T](
    db: Session,
    model: type[T],
    device_id: int,
    order_column: ColumnElement,
) -> list[T]:
    """Строки устройства: сначала новые, при равенстве времени — по id."""
    statement = (
        select(model)
        .where(model.device_id == device_id)
        .order_by(order_column.desc(), model.id.desc())
    )
    return list(db.scalars(statement).all())
