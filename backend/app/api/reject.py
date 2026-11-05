"""Общие отказы API, не зависящие от конкретного ресурса."""

from typing import NoReturn

from fastapi import status

from app.errors import AppError


def reject_deletion(message: str) -> NoReturn:
    """Физическое удаление не поддерживается ни для одного ресурса."""
    raise AppError("METHOD_NOT_ALLOWED", message, status.HTTP_405_METHOD_NOT_ALLOWED)
