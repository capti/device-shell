"""Эндпоинты справочника сотрудников."""

from fastapi import APIRouter, Depends, status
from sqlalchemy import Row
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_admin
from app.api.reject import reject_deletion
from app.db import get_db
from app.models import User
from app.schemas.users import (
    PasswordReset,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])


def _user_read(row: Row) -> UserRead:
    user: User = row[0]
    return UserRead(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        email=user.email,
        team=user.team,
        telegram=user.telegram,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        devices_owned=row[1],
        devices_held=row[2],
    )


@router.get("", response_model=list[UserRead])
def list_users(
    include_inactive: bool = False,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[UserRead]:
    rows = users_service.list_users(db, include_inactive=include_inactive)
    return [_user_read(row) for row in rows]


@router.get("/{user_id}", response_model=UserRead)
def read_user(
    user_id: int,
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserRead:
    return _user_read(users_service.get_user_row(db, user_id))


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserRead:
    user = users_service.create_user(db, **payload.model_dump())
    return _user_read(users_service.get_user_row(db, user.id))


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserRead:
    user = users_service.get_user(db, user_id)
    users_service.update_user(db, user, payload, actor=admin)
    return _user_read(users_service.get_user_row(db, user_id))


@router.delete("/{user_id}", status_code=status.HTTP_405_METHOD_NOT_ALLOWED)
def delete_user(user_id: int, _user: User = Depends(get_current_user)) -> None:
    reject_deletion("Удаление не поддерживается. Деактивируйте сотрудника")


@router.post("/{user_id}/deactivate", response_model=UserRead)
def deactivate_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserRead:
    user = users_service.get_user(db, user_id)
    users_service.deactivate_user(db, user, admin)
    return _user_read(users_service.get_user_row(db, user_id))


@router.post("/{user_id}/activate", response_model=UserRead)
def activate_user(
    user_id: int,
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserRead:
    user = users_service.get_user(db, user_id)
    users_service.activate_user(db, user)
    return _user_read(users_service.get_user_row(db, user_id))


@router.post("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    user_id: int,
    payload: PasswordReset,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> None:
    user = users_service.get_user(db, user_id)
    users_service.set_password(db, user, payload.password, actor=admin)
