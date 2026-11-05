"""Подключение к SQLite, сессии SQLAlchemy и PRAGMA-настройки."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    """Базовый класс всех ORM-моделей."""


def _connect_args(database_url: str) -> dict[str, Any]:
    if database_url.startswith("sqlite"):
        # Один процесс uvicorn, но FastAPI может работать в пуле потоков.
        return {"check_same_thread": False}
    return {}


def _ensure_sqlite_dir(database_url: str) -> None:
    """Создаёт каталог для файла базы, чтобы SQLite не падал на подключении."""
    url = make_url(database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        return
    if url.database == ":memory:" or url.database.startswith("file:"):
        return
    Path(url.database).expanduser().resolve().parent.mkdir(parents=True, exist_ok=True)


_ensure_sqlite_dir(settings.database_url)

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args(settings.database_url),
)


@event.listens_for(engine, "connect")
def _set_sqlite_pragmas(dbapi_connection: Any, _connection_record: Any) -> None:
    """На каждом новом соединении включает WAL, внешние ключи и busy_timeout."""
    if not settings.database_url.startswith("sqlite"):
        return
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()
    # SQLite-функция lower() не понимает кириллицу, а поиск по ФИО обязан
    # игнорировать регистр. Регистрируем casefold() на каждом соединении.
    dbapi_connection.create_function("casefold", 1, _casefold)


def _casefold(value: Any) -> Any:
    return value.casefold() if isinstance(value, str) else value


SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """FastAPI-зависимость: сессия БД на один запрос."""
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
