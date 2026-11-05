"""Локальное время сервера: naive datetime с секундной точностью."""

from app.clock import now_local


def test_now_local_has_no_microseconds() -> None:
    moment = now_local()

    assert moment.tzinfo is None
    assert moment.microsecond == 0
