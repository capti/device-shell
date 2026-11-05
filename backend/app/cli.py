"""CLI-команды обслуживания.

Пример:
    uv run python -m app.cli create-admin --username admin --full-name "Иван Иванов"
"""

import argparse
import getpass
import sys
from collections.abc import Sequence
from pathlib import Path

from app.db import SessionLocal
from app.errors import AppError
from app.services.backup import KEEP_BACKUPS, create_backup, restore_backup
from app.services.users import create_user


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    create_admin = subparsers.add_parser(
        "create-admin", help="Создать активного администратора"
    )
    create_admin.add_argument("--username", required=True, help="Логин")
    create_admin.add_argument("--full-name", required=True, help="ФИО")
    create_admin.add_argument(
        "--password", help="Пароль (если не указан, будет запрошен интерактивно)"
    )

    backup = subparsers.add_parser("backup", help="Скопировать базу и media")
    backup.add_argument(
        "--keep",
        type=int,
        default=KEEP_BACKUPS,
        help=f"Сколько копий хранить (по умолчанию {KEEP_BACKUPS})",
    )

    restore = subparsers.add_parser("restore", help="Восстановить данные из копии")
    restore.add_argument("path", help="Каталог резервной копии")
    restore.add_argument("--yes", action="store_true", help="Без подтверждения")
    return parser


def _create_admin(args: argparse.Namespace) -> int:
    password = args.password or getpass.getpass("Пароль: ")
    with SessionLocal() as db:
        try:
            user = create_user(
                db,
                username=args.username,
                full_name=args.full_name,
                password=password,
                role="admin",
            )
        except AppError as exc:
            print(f"Ошибка: {exc.message}", file=sys.stderr)
            return 1
    print(f"Администратор {user.username} создан (id={user.id})")
    return 0


def _backup(args: argparse.Namespace) -> int:
    try:
        path = create_backup(keep=args.keep)
    except AppError as exc:
        print(f"Ошибка: {exc.message}", file=sys.stderr)
        return 1
    print(f"Резервная копия создана: {path}")
    return 0


def _restore(args: argparse.Namespace) -> int:
    if not args.yes:
        answer = input(f"Восстановить данные из {args.path}? [y/N] ").strip().lower()
        if answer not in {"y", "yes", "д", "да"}:
            print("Восстановление отменено")
            return 1
    try:
        restore_backup(Path(args.path))
    except AppError as exc:
        print(f"Ошибка: {exc.message}", file=sys.stderr)
        return 1
    print(f"Данные восстановлены из {args.path}")
    return 0


_COMMANDS = {
    "create-admin": _create_admin,
    "backup": _backup,
    "restore": _restore,
}


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handler = _COMMANDS.get(args.command)
    if handler is None:
        parser.error(f"Неизвестная команда: {args.command}")
    return handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
