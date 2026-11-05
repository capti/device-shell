"""Резервное копирование и восстановление `data/`: база и media."""

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from shutil import copy2

import pytest
from sqlalchemy.orm import Session

from app.cli import main
from app.config import settings
from app.errors import AppError
from app.services import backup
from app.services.backup import KEEP_BACKUPS, create_backup, restore_backup


def _backup_names() -> list[str]:
    return sorted(path.name for path in settings.backup_dir.glob("qa-backup-*"))


def _usernames() -> list[str]:
    with closing(sqlite3.connect(backup.database_path())) as connection:
        return [row[0] for row in connection.execute("SELECT username FROM users")]


def test_create_backup_copies_database_and_media(db: Session, make_user) -> None:
    make_user(username="owner")
    media_file = settings.media_dir / "devices/1/pic.jpg"
    media_file.parent.mkdir(parents=True, exist_ok=True)
    media_file.write_bytes(b"photo")

    path = create_backup(now=datetime(2026, 10, 30, 12, 0, 0))

    assert path == settings.backup_dir / "qa-backup-2026-10-30_12-00-00"
    assert (path / "media/devices/1/pic.jpg").read_bytes() == b"photo"
    with closing(sqlite3.connect(path / "qa.db")) as connection:
        usernames = [row[0] for row in connection.execute("SELECT username FROM users")]
    assert usernames == ["owner"]


def test_create_backup_keeps_only_latest_copies() -> None:
    for hour in range(KEEP_BACKUPS + 2):
        create_backup(now=datetime(2026, 10, 1, hour))

    names = _backup_names()

    assert len(names) == KEEP_BACKUPS
    assert names[0] == "qa-backup-2026-10-01_02-00-00"
    assert names[-1] == "qa-backup-2026-10-01_15-00-00"


def test_create_backup_rejects_non_positive_keep() -> None:
    with pytest.raises(AppError) as excinfo:
        create_backup(keep=0)

    assert excinfo.value.code == "BACKUP_KEEP_INVALID"
    assert _backup_names() == []


def test_create_backup_requires_database(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(backup, "database_path", lambda: tmp_path / "missing.db")

    with pytest.raises(AppError) as excinfo:
        create_backup()

    assert excinfo.value.code == "BACKUP_NO_DATABASE"
    assert _backup_names() == []


def test_create_backup_refuses_duplicate_in_same_second() -> None:
    moment = datetime(2026, 10, 30, 12, 0, 0)
    create_backup(now=moment)

    with pytest.raises(AppError) as excinfo:
        create_backup(now=moment)

    assert excinfo.value.code == "BACKUP_EXISTS"
    assert _backup_names() == ["qa-backup-2026-10-30_12-00-00"]


def test_backup_requires_sqlite(monkeypatch) -> None:
    monkeypatch.setattr(settings, "database_url", "postgresql://user@localhost/db")

    with pytest.raises(AppError) as excinfo:
        backup.database_path()

    assert excinfo.value.code == "BACKUP_UNSUPPORTED"


def test_create_backup_removes_partial_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.services.backup as backup_module

    def boom(*_args, **_kwargs):
        raise RuntimeError("имитация сбоя копирования media")

    monkeypatch.setattr(backup_module, "copytree", boom)
    settings.media_dir.mkdir(parents=True, exist_ok=True)

    with pytest.raises(RuntimeError):
        create_backup(now=datetime(2026, 10, 30, 12, 0, 0))

    assert _backup_names() == []


def test_restore_replaces_database_and_media(db: Session, make_user) -> None:
    make_user(username="owner")
    path = create_backup(now=datetime(2026, 10, 30, 9, 0, 0))
    make_user(username="later")
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    fresh = settings.media_dir / "fresh.txt"
    fresh.write_text("new", encoding="utf-8")

    restore_backup(path)

    assert _usernames() == ["owner"]
    assert not fresh.exists()


def test_restore_rejects_copy_without_database(
    tmp_path: Path, make_user
) -> None:
    make_user(username="owner")
    broken = tmp_path / "qa-backup-broken"
    broken.mkdir()

    with pytest.raises(AppError) as excinfo:
        restore_backup(broken)

    assert excinfo.value.code == "BACKUP_INVALID"
    assert _usernames() == ["owner"]


def test_cli_backup_creates_copy(capsys) -> None:
    assert main(["backup"]) == 0

    assert "Резервная копия создана" in capsys.readouterr().out
    assert len(_backup_names()) == 1


def test_cli_backup_reports_error(
    capsys, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(backup, "database_path", lambda: tmp_path / "missing.db")

    assert main(["backup"]) == 1

    assert "Ошибка" in capsys.readouterr().err


def test_cli_restore_without_confirmation_changes_nothing(
    db: Session, make_user, capsys, monkeypatch: pytest.MonkeyPatch
) -> None:
    make_user(username="owner")
    path = create_backup(now=datetime(2026, 10, 30, 9, 0, 0))
    make_user(username="later")
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")

    assert main(["restore", str(path)]) == 1

    assert "отменено" in capsys.readouterr().out.lower()
    assert _usernames() == ["later", "owner"]


def test_cli_restore_with_yes_applies_backup(
    db: Session, make_user, capsys
) -> None:
    make_user(username="owner")
    path = create_backup(now=datetime(2026, 10, 30, 9, 0, 0))
    make_user(username="later")

    assert main(["restore", str(path), "--yes"]) == 0

    assert "восстановлены" in capsys.readouterr().out.lower()
    assert _usernames() == ["owner"]


def test_cli_restore_reports_error(capsys, tmp_path: Path) -> None:
    broken = tmp_path / "qa-backup-broken"
    broken.mkdir()

    assert main(["restore", str(broken), "--yes"]) == 1

    assert "Ошибка" in capsys.readouterr().err


def test_create_backup_allows_keeping_single_copy() -> None:
    create_backup(now=datetime(2026, 10, 1, 1, 0, 0))
    create_backup(keep=1, now=datetime(2026, 10, 1, 2, 0, 0))

    assert _backup_names() == ["qa-backup-2026-10-01_02-00-00"]


def test_list_backups_is_empty_without_directory() -> None:
    assert backup.list_backups() == []


def test_restore_brings_media_back(db: Session, make_user) -> None:
    make_user(username="owner")
    media_file = settings.media_dir / "devices/1/pic.jpg"
    media_file.parent.mkdir(parents=True, exist_ok=True)
    media_file.write_bytes(b"original")
    path = create_backup(now=datetime(2026, 10, 30, 9, 0, 0))
    media_file.write_bytes(b"changed")

    restore_backup(path)

    assert media_file.read_bytes() == b"original"


def test_restore_creates_empty_media_when_copy_has_none(
    tmp_path: Path, make_user
) -> None:
    make_user(username="owner")
    path = create_backup(now=datetime(2026, 10, 30, 9, 0, 0))
    database_only = tmp_path / "qa-backup-database-only"
    database_only.mkdir()
    copy2(path / "qa.db", database_only / "qa.db")

    restore_backup(database_only)

    assert settings.media_dir.is_dir()
    assert list(settings.media_dir.iterdir()) == []


def test_restore_survives_media_that_cannot_be_removed(
    tmp_path: Path, make_user, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Если media не удалился, восстановление базы всё равно проходит."""
    make_user(username="owner")
    path = create_backup(now=datetime(2026, 10, 30, 9, 0, 0))
    database_only = tmp_path / "qa-backup-database-only"
    database_only.mkdir()
    copy2(path / "qa.db", database_only / "qa.db")
    settings.media_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(backup, "rmtree", lambda *_args, **_kwargs: None)

    restore_backup(database_only)

    assert settings.media_dir.is_dir()
