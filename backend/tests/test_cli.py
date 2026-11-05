import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.cli import main
from app.models import User
from app.services.passwords import verify_password


def test_cli_requires_command(capsys) -> None:
    with pytest.raises(SystemExit):
        main([])

    # argparse объясняет, что не хватает обязательного аргумента; без
    # `required=True` сюда попадает «Неизвестная команда: None».
    assert "required" in capsys.readouterr().err


@pytest.mark.parametrize(
    "args",
    [
        ["create-admin", "--full-name", "Иван Админов"],
        ["create-admin", "--username", "admin"],
    ],
)
def test_create_admin_requires_username_and_full_name(args: list[str]) -> None:
    with pytest.raises(SystemExit):
        main(args)


def test_create_admin_creates_active_admin(db: Session, capsys) -> None:
    exit_code = main(
        [
            "create-admin",
            "--username",
            "admin",
            "--full-name",
            "Иван Админов",
            "--password",
            "secret123",
        ]
    )

    assert exit_code == 0
    admin = db.scalar(select(User).where(User.username == "admin"))
    assert admin is not None
    assert admin.role == "admin"
    assert admin.is_active is True
    assert verify_password(admin.password_hash, "secret123") is True
    assert "создан" in capsys.readouterr().out


def test_create_admin_rejects_duplicate_username(db: Session, capsys) -> None:
    args = [
        "create-admin",
        "--username",
        "admin",
        "--full-name",
        "Иван Админов",
        "--password",
        "secret123",
    ]
    assert main(args) == 0

    exit_code = main(args)

    assert exit_code == 1
    assert "уже существует" in capsys.readouterr().err


def test_create_admin_accepts_minimum_password_length(db: Session) -> None:
    exit_code = main(
        [
            "create-admin",
            "--username",
            "admin",
            "--full-name",
            "Иван Админов",
            "--password",
            "12345678",
        ]
    )

    assert exit_code == 0
    admin = db.scalar(select(User).where(User.username == "admin"))
    assert verify_password(admin.password_hash, "12345678") is True


def test_create_admin_rejects_short_password(db: Session, capsys) -> None:
    exit_code = main(
        [
            "create-admin",
            "--username",
            "admin",
            "--full-name",
            "Иван Админов",
            "--password",
            "short",
        ]
    )

    assert exit_code == 1
    assert "не менее 8" in capsys.readouterr().err
