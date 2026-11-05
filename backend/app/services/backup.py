"""Резервное копирование и восстановление `data/`: базы и каталога media.

Копия базы снимается через SQLite backup API, а не копированием файла: в режиме
WAL часть закоммиченных страниц ещё лежит в журнале, и файловая копия была бы
устаревшей. Копия пишется в отдельный каталог; при ошибке он удаляется целиком,
чтобы не оставалось полупустых копий.
"""

import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path
from shutil import copytree, rmtree

from sqlalchemy.engine import make_url

from app.clock import now_local
from app.config import settings
from app.errors import AppError

KEEP_BACKUPS = 14
BACKUP_PREFIX = "qa-backup-"
_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"


def database_path() -> Path:
    """Файл SQLite, который обслуживает приложение."""
    url = make_url(settings.database_url)
    if url.get_backend_name() != "sqlite" or not url.database:
        raise AppError(
            "BACKUP_UNSUPPORTED",
            "Бэкап поддерживает только файловую базу SQLite",
            500,
        )
    return Path(url.database).expanduser().resolve()


def _copy_database(source: Path, target: Path) -> None:
    """Согласованный снимок базы средствами SQLite."""
    with closing(sqlite3.connect(source)) as source_connection, closing(
        sqlite3.connect(target)
    ) as target_connection:
        source_connection.backup(target_connection)


def _check_keep(keep: int) -> None:
    if keep < 1:
        raise AppError(
            "BACKUP_KEEP_INVALID",
            "Нужно хранить хотя бы одну резервную копию",
            400,
        )


def list_backups() -> list[Path]:
    """Копии от старых к новым: имя содержит сортируемую метку времени."""
    if not settings.backup_dir.exists():
        return []
    paths = settings.backup_dir.glob(f"{BACKUP_PREFIX}*")
    return sorted(path for path in paths if path.is_dir())


def prune_backups(keep: int = KEEP_BACKUPS) -> list[Path]:
    """Удаляет старые копии, оставляя `keep` самых новых."""
    _check_keep(keep)
    backups = list_backups()
    removed = backups[:-keep] if len(backups) > keep else []
    for path in removed:
        rmtree(path, ignore_errors=True)
    return removed


def create_backup(keep: int = KEEP_BACKUPS, now: datetime | None = None) -> Path:
    """Создаёт копию базы и media, затем чистит копии сверх `keep`."""
    _check_keep(keep)
    source_db = database_path()
    if not source_db.exists():
        raise AppError("BACKUP_NO_DATABASE", "Файл базы не найден", 500)

    stamp = (now or now_local()).strftime(_TIMESTAMP_FORMAT)
    target = settings.backup_dir / f"{BACKUP_PREFIX}{stamp}"
    try:
        target.mkdir(parents=True)
    except FileExistsError as exc:
        raise AppError(
            "BACKUP_EXISTS",
            "Резервная копия за эту секунду уже создана",
            409,
        ) from exc

    try:
        _copy_database(source_db, target / "qa.db")
        if settings.media_dir.exists():
            copytree(settings.media_dir, target / "media")
        else:
            (target / "media").mkdir()
    except Exception:
        rmtree(target, ignore_errors=True)
        raise

    prune_backups(keep)
    return target


def restore_backup(source: Path) -> None:
    """Возвращает базу и media из копии; приложение должно быть остановлено."""
    backup = Path(source)
    source_db = backup / "qa.db"
    if not source_db.is_file():
        raise AppError("BACKUP_INVALID", "В копии нет файла базы", 422)

    _copy_database(source_db, database_path())

    media_source = backup / "media"
    rmtree(settings.media_dir, ignore_errors=True)
    if media_source.is_dir():
        copytree(media_source, settings.media_dir)
    else:
        settings.media_dir.mkdir(parents=True, exist_ok=True)
