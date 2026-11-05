"""`ensure_admin`: первый старт создаёт администратора, повторы ничего не меняют."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import User
from app.services.passwords import verify_password
from app.services.users import ensure_admin


def _count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User))


def test_ensure_admin_creates_active_admin(db: Session) -> None:
    user = ensure_admin(
        db, username="admin", full_name="Иван Админов", password="secret123"
    )

    assert user is not None
    assert user.role == "admin"
    assert user.is_active is True
    assert verify_password(user.password_hash, "secret123") is True
    assert _count(db) == 1


def test_ensure_admin_keeps_existing_account_untouched(db: Session) -> None:
    first = ensure_admin(
        db, username="admin", full_name="Иван Админов", password="secret123"
    )
    second = ensure_admin(
        db, username="admin", full_name="Другое Имя", password="another456"
    )

    assert first is not None
    assert second is None
    assert _count(db) == 1
    stored = db.scalar(select(User).where(User.username == "admin"))
    assert stored.full_name == "Иван Админов"
    assert verify_password(stored.password_hash, "secret123") is True
    assert verify_password(stored.password_hash, "another456") is False


def test_ensure_admin_does_not_elevate_existing_user(db: Session) -> None:
    ensure_admin(db, username="admin", full_name="Иван Админов", password="secret123")
    stored = db.scalar(select(User).where(User.username == "admin"))
    stored.role = "user"
    db.commit()

    result = ensure_admin(
        db, username="admin", full_name="Иван Админов", password="another456"
    )

    assert result is None
    db.refresh(stored)
    assert stored.role == "user"
    assert verify_password(stored.password_hash, "secret123") is True
