"""Справочник сотрудников: чтение, правка, деактивация, пароли."""

from typing import Any

from sqlalchemy import Row, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import now_local
from app.errors import AppError
from app.models import Checkout, Device, User
from app.schemas.users import UserUpdate
from app.services.device_state import record_event
from app.services.lookup import get_user as get_user
from app.services.notifications import (
    PASSWORD_RESET,
    ROLE_CHANGED,
    USER_DEACTIVATED,
    active_admin_ids,
    notify,
    notify_employee,
)
from app.services.passwords import hash_password, verify_password
from app.services.sessions import revoke_user_sessions

MIN_PASSWORD_LENGTH = 8


def get_user_by_username(db: Session, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username.strip()))


def _ensure_password_strength(password: str) -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AppError(
            "WEAK_PASSWORD",
            f"Пароль должен содержать не менее {MIN_PASSWORD_LENGTH} символов",
            422,
        )


def create_user(
    db: Session,
    *,
    username: str,
    full_name: str,
    password: str,
    role: str = "user",
    email: str | None = None,
    team: str | None = None,
    telegram: str | None = None,
) -> User:
    username = username.strip()
    full_name = full_name.strip()

    if not username:
        raise AppError("VALIDATION_ERROR", "Укажите логин", 422)
    if not full_name:
        raise AppError("VALIDATION_ERROR", "Укажите ФИО", 422)
    _ensure_password_strength(password)
    if role not in ("admin", "user"):
        raise AppError("VALIDATION_ERROR", "Недопустимая роль", 422)
    if get_user_by_username(db, username) is not None:
        raise AppError("USERNAME_TAKEN", "Пользователь с таким логином уже существует", 409)

    user = User(
        username=username,
        full_name=full_name,
        password_hash=hash_password(password),
        role=role,
        email=email,
        team=team,
        telegram=telegram,
        is_active=True,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AppError(
            "USERNAME_TAKEN", "Пользователь с таким логином уже существует", 409
        ) from exc
    db.refresh(user)
    return user


def ensure_admin(
    db: Session, *, username: str, full_name: str, password: str
) -> User | None:
    """Создать администратора, если логина ещё нет; иначе ничего не менять.

    Нужен для первого старта в контейнере: повторный запуск не перезаписывает
    ни пароль, ни роль — существующая учётная запись остаётся как есть.
    """
    if get_user_by_username(db, username) is not None:
        return None
    return create_user(
        db, username=username, full_name=full_name, password=password, role="admin"
    )


def _user_counters() -> tuple:
    """Подзапросы счётчиков: владение (включая архив) и активные выдачи."""
    owned = (
        select(Device.owner_id.label("user_id"), func.count(Device.id).label("owned"))
        .group_by(Device.owner_id)
        .subquery()
    )
    held = (
        select(Checkout.user_id.label("user_id"), func.count(Checkout.id).label("held"))
        .where(Checkout.returned_at.is_(None))
        .group_by(Checkout.user_id)
        .subquery()
    )
    return owned, held


def _user_query() -> tuple:
    owned, held = _user_counters()
    statement = (
        select(
            User,
            func.coalesce(owned.c.owned, 0).label("devices_owned"),
            func.coalesce(held.c.held, 0).label("devices_held"),
        )
        .outerjoin(owned, owned.c.user_id == User.id)
        .outerjoin(held, held.c.user_id == User.id)
    )
    return statement


def list_users(db: Session, *, include_inactive: bool) -> list[Row]:
    """Все сотрудники со счётчиками; только активные, если include_inactive=False."""
    statement = _user_query()
    if not include_inactive:
        statement = statement.where(User.is_active.is_(True))
    return list(db.execute(statement.order_by(User.full_name, User.id)).all())


def get_user_row(db: Session, user_id: int) -> Row:
    row = db.execute(_user_query().where(User.id == user_id)).first()
    if row is None:
        raise AppError("USER_NOT_FOUND", "Сотрудник не найден", 404)
    return row


def _active_admin_count(db: Session) -> int:
    return db.scalar(
        select(func.count())
        .select_from(User)
        .where(User.role == "admin", User.is_active.is_(True))
    )


def ensure_not_last_admin(db: Session, user: User) -> None:
    """Последнего активного admin нельзя разжаловать или деактивировать."""
    if user.role == "admin" and user.is_active and _active_admin_count(db) <= 1:
        raise AppError(
            "LAST_ADMIN",
            "Нельзя разжаловать или деактивировать последнего администратора",
            409,
        )


_PROFILE_FIELDS = ("full_name", "email", "team", "telegram")


def _ensure_full_name(changes: dict[str, Any]) -> None:
    if "full_name" in changes and changes["full_name"] is None:
        raise AppError("VALIDATION_ERROR", "Укажите ФИО", 422)


def _apply_role(db: Session, user: User, changes: dict[str, Any]) -> None:
    role = changes.get("role")
    if role is None:
        return
    if role == "user":
        ensure_not_last_admin(db, user)
    user.role = role


def _apply_fields(user: User, changes: dict[str, Any]) -> None:
    for field in _PROFILE_FIELDS:
        if field in changes and getattr(user, field) != changes[field]:
            setattr(user, field, changes[field])


def update_user(
    db: Session, user: User, payload: UserUpdate, *, actor: User | None = None
) -> User:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return user

    _ensure_full_name(changes)
    previous_role = user.role
    _apply_role(db, user, changes)
    _apply_fields(user, changes)
    if user.role != previous_role:
        notify_employee(
            db,
            type=ROLE_CHANGED,
            employee_id=user.id,
            actor=actor,
            payload={"role": user.role},
        )
    db.commit()
    db.refresh(user)
    return user


def _devices_in_circulation(db: Session, user_id: int) -> list[str]:
    """Инвентарные номера устройств, мешающих деактивации."""
    active_ids = select(Checkout.device_id).where(Checkout.returned_at.is_(None))
    held_ids = select(Checkout.device_id).where(
        Checkout.returned_at.is_(None), Checkout.user_id == user_id
    )
    statement = (
        select(Device.inventory_no)
        .where(Device.id.in_(active_ids))
        .where(or_(Device.owner_id == user_id, Device.id.in_(held_ids)))
        .order_by(Device.inventory_no)
    )
    return list(db.scalars(statement).all())


def _archive_owned_devices(db: Session, user: User, actor: User) -> None:
    owned = db.scalars(
        select(Device).where(
            Device.owner_id == user.id,
            Device.archived_at.is_(None),
        )
    ).all()
    archived_at = now_local()
    for device in owned:
        device.archived_at = archived_at
        record_event(
            db,
            device_id=device.id,
            actor_id=actor.id,
            event_type="archived",
            payload={"reason": "owner_deactivated"},
        )


def deactivate_user(db: Session, user: User, actor: User) -> User:
    """Закрывает доступ и архивирует устройства; при обороте — 409."""
    if not user.is_active:
        raise AppError("ALREADY_INACTIVE", "Сотрудник уже деактивирован", 409)
    ensure_not_last_admin(db, user)

    blocked = _devices_in_circulation(db, user.id)
    if blocked:
        raise AppError(
            "HAS_DEVICES",
            f"Сначала верните устройства: {', '.join(blocked)}",
            409,
        )

    _archive_owned_devices(db, user, actor)
    user.is_active = False
    notify(
        db,
        type=USER_DEACTIVATED,
        recipients=[
            admin_id for admin_id in active_admin_ids(db) if admin_id != actor.id
        ],
        actor_id=actor.id,
        payload={"username": user.username, "full_name": user.full_name},
    )
    db.commit()
    db.refresh(user)
    return user


def activate_user(db: Session, user: User) -> User:
    if user.is_active:
        raise AppError("ALREADY_ACTIVE", "Сотрудник уже активен", 409)
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


def set_password(
    db: Session,
    user: User,
    password: str,
    *,
    actor: User | None = None,
    preserve_session_token: str | None = None,
) -> None:
    _ensure_password_strength(password)
    user.password_hash = hash_password(password)
    revoke_user_sessions(db, user.id, except_token=preserve_session_token)
    notify_employee(
        db,
        type=PASSWORD_RESET,
        employee_id=user.id,
        actor=actor,
        payload={"username": user.username},
    )
    db.commit()


def change_password(
    db: Session,
    user: User,
    *,
    current_password: str,
    new_password: str,
    session_token: str,
) -> None:
    if not verify_password(user.password_hash, current_password):
        raise AppError("INVALID_PASSWORD", "Текущий пароль неверен", 422)
    set_password(
        db,
        user,
        new_password,
        preserve_session_token=session_token,
    )
