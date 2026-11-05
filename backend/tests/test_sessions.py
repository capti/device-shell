from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.clock import now_local
from app.models import UserSession
from app.services.sessions import (
    create_session,
    hash_token,
    revoke_session,
    validate_session,
)


def test_create_session_stores_only_token_hash(db: Session, make_user) -> None:
    user = make_user()

    token, session = create_session(db, user, user_agent="pytest")

    assert token
    assert session.token_hash == hash_token(token)
    assert session.token_hash != token
    assert session.user_id == user.id
    assert session.expires_at > now_local()
    assert session.user_agent == "pytest"


def test_validate_session_extends_lifetime(db: Session, make_user) -> None:
    user = make_user()
    token, session = create_session(db, user)
    session.last_seen_at = now_local() - timedelta(days=6)
    session.expires_at = now_local() + timedelta(hours=1)
    db.commit()
    previous_expiry = session.expires_at

    validated = validate_session(db, token)

    assert validated is not None
    assert validated.id == session.id
    assert validated.expires_at > previous_expiry
    assert validated.last_seen_at > now_local() - timedelta(minutes=1)


def test_expired_session_is_rejected_and_removed(db: Session, make_user) -> None:
    user = make_user()
    token, session = create_session(db, user)
    session.expires_at = now_local() - timedelta(minutes=1)
    db.commit()
    session_id = session.id

    assert validate_session(db, token) is None
    assert db.get(UserSession, session_id) is None


def test_session_expiring_exactly_now_is_rejected(
    db: Session, make_user, monkeypatch
) -> None:
    moment = datetime(2026, 1, 1, 12, 0, 0)
    monkeypatch.setattr("app.services.sessions.now_local", lambda: moment)
    user = make_user()
    token, session = create_session(db, user)
    session.expires_at = moment
    db.commit()
    session_id = session.id

    assert validate_session(db, token) is None
    assert db.get(UserSession, session_id) is None


def test_revoke_session(db: Session, make_user) -> None:
    user = make_user()
    token, _session = create_session(db, user)

    assert revoke_session(db, token) is True
    assert validate_session(db, token) is None
    assert revoke_session(db, token) is False
    assert db.scalar(select(UserSession).where(UserSession.user_id == user.id)) is None
