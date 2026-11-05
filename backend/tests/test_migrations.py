import os
import sqlite3
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
DOMAIN_TABLES = {
    "users",
    "sessions",
    "devices",
    "checkouts",
    "condition_reports",
    "repairs",
    "device_photos",
    "device_events",
    "login_events",
    "notifications",
}


def _run_alembic(*args: str, env: dict[str, str]) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env={**env, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"},
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr


def _tables(database: Path) -> set[str]:
    with sqlite3.connect(database) as connection:
        return {
            row[0]
            for row in connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }


def _triggers(connection: sqlite3.Connection) -> set[str]:
    return {
        row[0]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'trigger'"
        )
    }


def test_upgrade_head_and_downgrade_base(tmp_path: Path) -> None:
    database = tmp_path / "migration.db"
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{database.as_posix()}"}

    _run_alembic("upgrade", "head", env=env)
    assert DOMAIN_TABLES <= _tables(database)

    with sqlite3.connect(database) as connection:
        index_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'uq_checkouts_active_device'"
        ).fetchone()[0]
        checkouts_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'checkouts'"
        ).fetchone()[0]
        triggers = _triggers(connection)
    assert "returned_at IS NULL" in index_sql
    assert "ck_checkouts_returned_closed_reason" in checkouts_sql
    assert triggers == {
        "trg_device_events_no_update",
        "trg_device_events_no_delete",
        "trg_login_events_no_update",
        "trg_login_events_no_delete",
    }

    _run_alembic("downgrade", "0001", env=env)
    with sqlite3.connect(database) as connection:
        checkouts_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE name = 'checkouts'"
        ).fetchone()[0]
        triggers = _triggers(connection)
    assert "ck_checkouts_returned_closed_reason" not in checkouts_sql
    assert triggers == set()

    _run_alembic("downgrade", "base", env=env)
    assert not (DOMAIN_TABLES & _tables(database))
