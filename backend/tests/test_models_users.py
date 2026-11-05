from datetime import timedelta

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import User, UserSession


def test_user_and_session_are_created(db: Session, make_user) -> None:
    user = make_user(username="ivanov")
    token_session = UserSession(
        user_id=user.id,
        token_hash="a" * 64,
        expires_at=now_local() + timedelta(days=7),
    )
    db.add(token_session)
    db.commit()

    stored = db.get(UserSession, token_session.id)
    assert stored is not None
    assert stored.user_id == user.id
    assert stored.token_hash == "a" * 64


def test_username_is_unique(db: Session, make_user) -> None:
    make_user(username="ivanov")

    with pytest.raises(IntegrityError):
        make_user(username="ivanov")


def test_role_is_limited_by_check_constraint(db: Session, make_user) -> None:
    with pytest.raises(IntegrityError):
        make_user(username="boss", role="superadmin")
    db.rollback()


def test_session_token_hash_is_unique(db: Session, make_user) -> None:
    user = make_user()
    expires_at = now_local() + timedelta(days=7)
    db.add(UserSession(user_id=user.id, token_hash="b" * 64, expires_at=expires_at))
    db.commit()

    with pytest.raises(IntegrityError):
        db.add(UserSession(user_id=user.id, token_hash="b" * 64, expires_at=expires_at))
        db.commit()
    db.rollback()


def test_user_is_linked_to_session(db: Session, make_user) -> None:
    user = make_user(username="petrov")
    session = UserSession(
        user_id=user.id,
        token_hash="c" * 64,
        expires_at=now_local() + timedelta(days=7),
    )
    db.add(session)
    db.commit()

    assert session.user_id == user.id
    assert db.query(User).filter(User.username == "petrov").one().is_active is True
