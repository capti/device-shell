"""Запуск в контейнере: миграции, администратор из окружения, uvicorn.

Один процесс, один порт (инвариант проекта): SQLite и rate limit попыток
входа рассчитаны на единственный uvicorn. Логи остаются JSON — `log_config`
uvicorn отключён, корневой обработчик задаёт `configure_logging`.
"""

import logging
import os
import subprocess
import sys

from app.config import BACKEND_DIR
from app.db import SessionLocal
from app.logs import configure_logging
from app.services.users import ensure_admin

# Логгер именованный: при запуске `python -m app.entrypoint` он попал бы в
# вывод как `__main__`.
logger = logging.getLogger("app.entrypoint")

DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8000


def upgrade_database() -> None:
    """Привести схему к head отдельным процессом.

    `alembic/env.py` вызывает `fileConfig(alembic.ini)`: тот вешает свой
    обработчик на корневой логгер, меняет его уровень и глушит уже созданные
    логгеры. В одном процессе с приложением это сломало бы JSON-формат и
    потеряло записи старта, поэтому миграции изолируются.
    """
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_DIR,
        check=True,
    )


def bootstrap_admin() -> None:
    """Создать администратора из окружения, если его ещё нет.

    Без `ADMIN_PASSWORD` ничего не создаётся — существующая база остаётся
    нетронутой. Уже существующий логин не перезаписывается.
    """
    password = os.environ.get("ADMIN_PASSWORD")
    if not password:
        logger.warning("admin_bootstrap_skipped", extra={"reason": "ADMIN_PASSWORD is not set"})
        return
    username = os.environ.get("ADMIN_USERNAME", "admin")
    full_name = os.environ.get("ADMIN_FULL_NAME", "Администратор")
    with SessionLocal() as db:
        user = ensure_admin(db, username=username, full_name=full_name, password=password)
    if user is None:
        logger.info("admin_unchanged", extra={"username": username})
    else:
        logger.info("admin_created", extra={"username": username, "user_id": user.id})


def main() -> None:
    configure_logging()
    upgrade_database()
    bootstrap_admin()

    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=os.environ.get("HOST", DEFAULT_HOST),
        port=int(os.environ.get("PORT", DEFAULT_PORT)),
        log_config=None,
    )


if __name__ == "__main__":
    main()
