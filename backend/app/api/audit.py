"""Аудит: глобальный журнал событий устройств с фильтрами по дате и устройству."""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.db import get_db
from app.errors import AppError
from app.models import User
from app.schemas.audit import (
    AuditEvent,
    AuditEventsResponse,
    LoginEvent,
    LoginEventsResponse,
)
from app.services import audit as audit_service
from app.services import login_audit

router = APIRouter(tags=["audit"])


def _require_admin(user: User = Depends(get_current_user)) -> User:
    """Тонкая обёртка над общим `require_admin` из `deps.py`.

    Проверку роли выполняет общая зависимость, здесь лишь сохраняется
    специфичное для журнала сообщение об ошибке: на него опираются текущий
    ответ API и тесты. Общий `require_admin` отдаёт «Недостаточно прав»,
    поэтому заменить им зависимость напрямую без изменения контракта нельзя.
    """
    try:
        return require_admin(user)
    except AppError as exc:
        if exc.code == "FORBIDDEN":
            raise AppError(
                "FORBIDDEN",
                "Доступ к журналу аудита только для администраторов",
                status_code=403,
            ) from exc
        raise


@router.get("/audit/events", response_model=AuditEventsResponse)
def list_audit_events(
    device_id: int | None = Query(default=None, description="Идентификатор устройства"),
    from_at: datetime | None = Query(default=None, description="Начало диапазона (включительно)"),
    to_at: datetime | None = Query(default=None, description="Конец диапазона (включительно)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
) -> AuditEventsResponse:
    """Глобальный журнал аудита: события устройств с фильтрами по дате и устройству."""
    events = audit_service.list_audit_events(
        db, device_id=device_id, from_at=from_at, to_at=to_at
    )
    return AuditEventsResponse(
        events=[AuditEvent.model_validate(event) for event in events],
        total=len(events),
        filtered_device_id=device_id,
        from_at=from_at,
        to_at=to_at,
    )


@router.get("/audit/logins", response_model=LoginEventsResponse)
def list_login_events(
    from_at: datetime | None = Query(default=None, description="Начало диапазона (включительно)"),
    to_at: datetime | None = Query(default=None, description="Конец диапазона (включительно)"),
    success: bool | None = Query(default=None, description="Исход попытки: истина или ложь"),
    username: str | None = Query(default=None, description="Введённый логин, часть строки"),
    limit: int = Query(default=login_audit.DEFAULT_LIMIT, ge=1, le=login_audit.MAX_LIMIT),
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
) -> LoginEventsResponse:
    """Журнал входов: попытки с фильтрами по дате, логину и исходу."""
    events, total = login_audit.list_login_events(
        db,
        from_at=from_at,
        to_at=to_at,
        success=success,
        username=username,
        limit=limit,
    )
    return LoginEventsResponse(
        events=[LoginEvent.model_validate(event) for event in events],
        total=total,
        from_at=from_at,
        to_at=to_at,
        limit=limit,
    )
