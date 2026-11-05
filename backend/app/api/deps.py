"""Зависимости FastAPI: текущий пользователь и проверка роли."""

from fastapi import Depends, Request, Response
from sqlalchemy.orm import Session

from app.api.cookies import set_session_cookie
from app.config import settings
from app.db import get_db
from app.errors import AppError
from app.models import User
from app.services.sessions import validate_session


def get_current_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    token = request.cookies.get(settings.session_cookie_name)
    if not token:
        raise AppError("UNAUTHORIZED", "Требуется вход в систему", 401)

    session = validate_session(db, token)
    if session is None:
        raise AppError("SESSION_EXPIRED", "Сессия истекла, войдите снова", 401)

    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        raise AppError("USER_INACTIVE", "Учётная запись деактивирована", 401)

    # Продлеваем и серверную сессию, и cookie: 7 дней от последней активности.
    set_session_cookie(response, token)
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise AppError("FORBIDDEN", "Недостаточно прав", 403)
    return user
