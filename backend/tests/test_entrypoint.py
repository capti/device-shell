"""Старт контейнера: администратор берётся из окружения и создаётся один раз."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.entrypoint import bootstrap_admin
from app.models import User
from app.services.passwords import verify_password


def _count(db: Session) -> int:
    return db.scalar(select(func.count()).select_from(User))


def test_bootstrap_creates_admin_from_environment(
    db: Session, monkeypatch
) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_FULL_NAME", "Иван Админов")
    monkeypatch.setenv("ADMIN_PASSWORD", "Admin12345")

    bootstrap_admin()

    admin = db.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    assert admin.role == "admin"
    assert verify_password(admin.password_hash, "Admin12345") is True
    assert _count(db) == 1


def test_bootstrap_creates_nothing_without_password(db: Session, monkeypatch) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

    bootstrap_admin()

    assert _count(db) == 0


def test_bootstrap_does_not_reset_password_on_restart(
    db: Session, monkeypatch
) -> None:
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_FULL_NAME", "Иван Админов")
    monkeypatch.setenv("ADMIN_PASSWORD", "Admin12345")
    bootstrap_admin()
    monkeypatch.setenv("ADMIN_PASSWORD", "OtherPass1")

    bootstrap_admin()

    assert _count(db) == 1
    admin = db.scalar(select(User).where(User.username == "admin"))
    assert verify_password(admin.password_hash, "Admin12345") is True
    assert verify_password(admin.password_hash, "OtherPass1") is False
