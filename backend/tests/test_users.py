import pytest
from sqlalchemy.orm import Session

from app.errors import AppError
from app.schemas.users import UserUpdate
from app.services import users
from app.services.users import create_user, get_user, update_user


def _payload(**overrides):
    data = {
        "username": "new-user",
        "full_name": "Новый Пользователь",
        "password": "secret123",
    }
    data.update(overrides)
    return data


def test_create_user_rejects_blank_username(db: Session) -> None:
    with pytest.raises(AppError) as excinfo:
        create_user(db, **_payload(username="   "))

    assert excinfo.value.code == "VALIDATION_ERROR"
    assert excinfo.value.message == "Укажите логин"
    assert excinfo.value.status_code == 422


def test_create_user_rejects_blank_full_name(db: Session) -> None:
    with pytest.raises(AppError) as excinfo:
        create_user(db, **_payload(full_name="   "))

    assert excinfo.value.code == "VALIDATION_ERROR"
    assert excinfo.value.message == "Укажите ФИО"
    assert excinfo.value.status_code == 422


def test_create_user_rejects_unknown_role(db: Session) -> None:
    with pytest.raises(AppError) as excinfo:
        create_user(db, **_payload(role="superuser"))

    assert excinfo.value.code == "VALIDATION_ERROR"
    assert excinfo.value.message == "Недопустимая роль"
    assert excinfo.value.status_code == 422


def test_create_user_reports_username_race(
    db: Session, make_user, monkeypatch
) -> None:
    make_user(username="taken")
    monkeypatch.setattr(users, "get_user_by_username", lambda _db, _name: None)

    with pytest.raises(AppError) as excinfo:
        create_user(db, **_payload(username="taken"))

    assert excinfo.value.code == "USERNAME_TAKEN"
    assert excinfo.value.status_code == 409


def test_get_user_rejects_unknown_id(db: Session) -> None:
    with pytest.raises(AppError) as excinfo:
        get_user(db, 9999)

    assert excinfo.value.code == "USER_NOT_FOUND"
    assert excinfo.value.status_code == 404


def test_update_user_rejects_null_full_name(db: Session, make_user) -> None:
    user = make_user()

    with pytest.raises(AppError) as excinfo:
        update_user(db, user, UserUpdate(full_name=None))

    assert excinfo.value.code == "VALIDATION_ERROR"


def test_update_user_clears_empty_contact(db: Session, make_user) -> None:
    user = make_user()
    user.email = "old@example.com"
    db.commit()

    updated = update_user(db, user, UserUpdate(email=""))

    assert updated.email is None
