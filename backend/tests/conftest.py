"""Общие фикстуры тестов.

Переменные окружения выставляются до импорта приложения, чтобы SQLite-файл
тестов не пересекался с рабочей базой `data/qa.db`.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

TEST_DIR = Path(tempfile.mkdtemp(prefix="qa-test-staff-"))
os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_DIR / 'test.db').as_posix()}"
os.environ["APP_ENV"] = "test"
os.environ["DATA_DIR"] = str(TEST_DIR / "data")
os.environ["APP_BASE_URL"] = "http://localhost:8000"
os.environ["COOKIE_SECURE"] = "false"
# Сборка фронтенда тестам не нужна: поведение SPA проверяется на временных
# каталогах через monkeypatch, а без каталога действует обычный JSON-404.
os.environ["FRONTEND_DIST"] = str(TEST_DIR / "dist")

from collections.abc import Callable, Iterator  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

import app.models  # noqa: E402,F401
from app.config import settings  # noqa: E402
from app.db import Base, SessionLocal, engine  # noqa: E402
from app.main import app as fastapi_app  # noqa: E402
from app.models import Device, User  # noqa: E402
from app.services.rate_limit import login_rate_limiter  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    """Чистая схема, пустой media-каталог и каталог копий перед каждым тестом."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    shutil.rmtree(settings.media_dir, ignore_errors=True)
    shutil.rmtree(settings.backup_dir, ignore_errors=True)
    login_rate_limiter.clear()
    yield
    login_rate_limiter.clear()


@pytest.fixture()
def client() -> TestClient:
    return TestClient(fastapi_app)


@pytest.fixture()
def make_client() -> Callable[[], TestClient]:
    """Независимый клиент со своей cookie-сессией (для проверки двух ролей)."""
    return lambda: TestClient(fastapi_app)


@pytest.fixture()
def db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def make_user(db: Session) -> Callable[..., User]:
    def factory(
        *,
        username: str = "tester",
        full_name: str = "Тестовый Пользователь",
        role: str = "user",
        is_active: bool = True,
        password_hash: str = "not-a-real-hash",
    ) -> User:
        user = User(
            username=username,
            full_name=full_name,
            role=role,
            is_active=is_active,
            password_hash=password_hash,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return factory


@pytest.fixture()
def make_device(db: Session) -> Callable[..., Device]:
    def factory(
        *,
        owner: User,
        inventory_no: str = "QA-PH-001",
        imei: str | None = None,
        serial_no: str | None = None,
        status: str = "active",
    ) -> Device:
        device = Device(
            inventory_no=inventory_no,
            brand="Samsung",
            model="Galaxy S23",
            owner_id=owner.id,
            created_by=owner.id,
            imei=imei,
            serial_no=serial_no,
            status=status,
        )
        db.add(device)
        db.commit()
        db.refresh(device)
        return device

    return factory
