"""Вход, выход и профиль текущего пользователя."""

from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session

from app.api.cookies import clear_session_cookie, set_session_cookie
from app.api.deps import get_current_user
from app.clock import now_local
from app.config import settings
from app.db import get_db
from app.errors import AppError
from app.models import User
from app.schemas.auth import LoginRequest, UserProfile
from app.schemas.users import PasswordChange
from app.services import login_audit
from app.services import users as users_service
from app.services.passwords import verify_password
from app.services.rate_limit import login_rate_limiter
from app.services.sessions import create_session, revoke_session
from app.services.users import get_user_by_username

router = APIRouter(prefix="/auth", tags=["auth"])


def _rate_limit_key(request: Request, username: str) -> str:
    client_host = request.client.host if request.client else "unknown"
    return f"{client_host}:{username.strip().lower()}"


def _record_attempt(
    request: Request,
    *,
    username: str,
    success: bool,
    reason: str | None = None,
    user_id: int | None = None,
) -> None:
    """Пишет попытку в журнал входов отдельной сессией — см. design.md."""
    login_audit.record_login_attempt(
        username_attempted=username,
        success=success,
        reason=reason,
        user_id=user_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )


@router.post("/login", response_model=UserProfile)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> User:
    key = _rate_limit_key(request, payload.username)
    try:
        login_rate_limiter.check(key)
    except AppError:
        _record_attempt(
            request,
            username=payload.username,
            success=False,
            reason=login_audit.REASON_RATE_LIMITED,
        )
        raise

    user = get_user_by_username(db, payload.username)
    if (
        user is None
        or not user.is_active
        or not verify_password(user.password_hash, payload.password)
    ):
        login_rate_limiter.register_failure(key)
        reason = (
            login_audit.REASON_INACTIVE_USER
            if user is not None and not user.is_active
            else login_audit.REASON_INVALID_CREDENTIALS
        )
        _record_attempt(
            request,
            username=payload.username,
            success=False,
            reason=reason,
            user_id=user.id if user is not None else None,
        )
        raise AppError("INVALID_CREDENTIALS", "Неверный логин или пароль", 401)

    login_rate_limiter.reset(key)
    token, _session = create_session(db, user, request.headers.get("user-agent"))

    user.last_login_at = now_local()
    db.commit()
    db.refresh(user)

    _record_attempt(request, username=user.username, success=True, user_id=user.id)

    set_session_cookie(response, token)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> None:
    token = request.cookies.get(settings.session_cookie_name)
    if token:
        revoke_session(db, token)
    clear_session_cookie(response)


@router.get("/me", response_model=UserProfile)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    payload: PasswordChange,
    request: Request,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    users_service.change_password(
        db,
        user,
        current_password=payload.current_password,
        new_password=payload.new_password,
        session_token=request.cookies[settings.session_cookie_name],
    )
