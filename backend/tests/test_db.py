from pathlib import Path

from sqlalchemy import text

from app.db import _ensure_sqlite_dir, engine


def test_ensure_sqlite_dir_creates_nested_parents(tmp_path: Path) -> None:
    database = tmp_path / "nested" / "deep" / "qa.db"

    _ensure_sqlite_dir(f"sqlite:///{database.as_posix()}")

    assert database.parent.is_dir()


def test_ensure_sqlite_dir_skips_non_file_databases(monkeypatch) -> None:
    created: list[Path] = []
    monkeypatch.setattr(
        Path, "mkdir", lambda self, *args, **kwargs: created.append(self)
    )

    _ensure_sqlite_dir("postgresql://user@localhost/qa")
    _ensure_sqlite_dir("sqlite://")
    _ensure_sqlite_dir("sqlite:///:memory:")
    _ensure_sqlite_dir("sqlite:///file:memdb?mode=memory&cache=shared")

    assert created == []


def test_sqlite_uses_wal() -> None:
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA journal_mode")).scalar() == "wal"


def test_sqlite_foreign_keys_enabled() -> None:
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1


def test_sqlite_busy_timeout() -> None:
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA busy_timeout")).scalar() == 5000
