"""Единое локальное время сервера (naive datetime, см. design.md)."""

from datetime import datetime


def now_local() -> datetime:
    """Текущее локальное время без часового пояса."""
    return datetime.now().replace(microsecond=0)


def start_of_day(value: datetime) -> datetime:
    """Начало суток, в которые попадает `value`."""
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(value: datetime) -> datetime:
    """Конец суток, в которые попадает `value`: границы диапазона включительны."""
    return value.replace(hour=23, minute=59, second=59, microsecond=999999)
