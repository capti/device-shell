"""Журнал входов: запись каждой попытки и чтение для админа.

Запись идёт отдельной сессией БД: `get_db` откатывает транзакцию запроса при
исключении, а попытка входа, отклонённая с 401 или 429, — ровно та запись,
ради которой журнал существует.
"""

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.clock import end_of_day, now_local, start_of_day
from app.db import SessionLocal
from app.models import LoginEvent

# Окно по умолчанию — как в журнале событий устройств: без фильтров журнал
# не должен возвращать всю историю.
DEFAULT_WINDOW_DAYS = 30

# Попытки входа плодятся пачками при переборе, поэтому выборка ограничена.
DEFAULT_LIMIT = 200
MAX_LIMIT = 1000

REASON_INVALID_CREDENTIALS = "invalid_credentials"
REASON_INACTIVE_USER = "inactive_user"
REASON_RATE_LIMITED = "rate_limited"

LOGIN_EVENT_REASON_LABELS = {
    REASON_INVALID_CREDENTIALS: "Неверные учётные данные",
    REASON_INACTIVE_USER: "Деактивированная учётная запись",
    REASON_RATE_LIMITED: "Слишком много попыток",
}


def record_login_attempt(
    *,
    username_attempted: str,
    success: bool,
    reason: str | None = None,
    user_id: int | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Пишет попытку входа в журнал собственной сессией и коммитит."""
    with SessionLocal() as db:
        db.add(
            LoginEvent(
                username_attempted=username_attempted[:64],
                user_id=user_id,
                success=success,
                reason=reason,
                ip_address=ip_address,
                user_agent=user_agent[:512] if user_agent else None,
            )
        )
        db.commit()


def build_login_events_query(
    *,
    from_at: datetime | None,
    to_at: datetime | None,
    success: bool | None,
    username: str | None,
) -> select:
    """Запрос попыток входа с фильтрами по дате, исходу и введённому логину."""
    query = select(LoginEvent)

    if from_at is not None:
        query = query.where(LoginEvent.created_at >= start_of_day(from_at))
    if to_at is not None:
        query = query.where(LoginEvent.created_at <= end_of_day(to_at))
    if not from_at and not to_at:
        # Без диапазона — последние 30 дней, как в журнале событий.
        query = query.where(
            LoginEvent.created_at >= now_local() - timedelta(days=DEFAULT_WINDOW_DAYS)
        )

    if success is not None:
        query = query.where(LoginEvent.success == success)

    if username:
        needle = username.strip().casefold()
        query = query.where(
            func.casefold(LoginEvent.username_attempted).contains(needle, autoescape=True)
        )

    return query.order_by(LoginEvent.created_at.desc(), LoginEvent.id.desc())


def list_login_events(
    db: Session,
    *,
    from_at: datetime | None,
    to_at: datetime | None,
    success: bool | None,
    username: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    """Возвращает ограничённую выборку строк и полное число подходящих записей."""
    query = build_login_events_query(
        from_at=from_at, to_at=to_at, success=success, username=username
    )
    total = db.scalar(
        select(func.count()).select_from(
            query.with_only_columns(LoginEvent.id).order_by(None).subquery()
        )
    )
    rows = db.scalars(query.limit(limit)).all()

    events = [
        {
            "event_id": row.id,
            "username_attempted": row.username_attempted,
            "user_id": row.user_id,
            "success": row.success,
            "reason": row.reason,
            "reason_label": LOGIN_EVENT_REASON_LABELS.get(row.reason or "", row.reason),
            "ip_address": row.ip_address,
            "user_agent": row.user_agent,
            "created_at": row.created_at,
        }
        for row in rows
    ]
    return events, int(total or 0)
