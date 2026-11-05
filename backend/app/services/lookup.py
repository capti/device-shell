"""Поиск ORM-объекта по id с единым ответом `404`."""

from collections.abc import Callable

from sqlalchemy.orm import Session

from app.db import Base
from app.errors import AppError
from app.models import Device, User


def _lookup_factory[ModelT: Base](
    model: type[ModelT], *, code: str, message: str
) -> Callable[[Session, int], ModelT]:
    """Собирает поиск по id с заданными кодом и сообщением ошибки."""

    def lookup(db: Session, entity_id: int) -> ModelT:
        entity = db.get(model, entity_id)
        if entity is None:
            raise AppError(code, message, 404)
        return entity

    return lookup


get_device = _lookup_factory(
    Device, code="DEVICE_NOT_FOUND", message="Устройство не найдено"
)
get_user = _lookup_factory(
    User, code="USER_NOT_FOUND", message="Сотрудник не найден"
)
