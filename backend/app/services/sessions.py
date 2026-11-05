"""Серверные сессии: непрозрачный токен в cookie, SHA-256 в БД."""

import hashlib
import secrets

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.clock import now_local
from app.config import settings
from app.models import User, UserSession


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(
    db: Session, user: User, user_agent: str | None = None
) -> tuple[str, UserSession]:
    """Создаёт сессию и возвращает сырой токен (в БД попадает только хеш)."""
    token = secrets.token_urlsafe(32)
    now = now_local()
    session = UserSession(
        user_id=user.id,
        token_hash=hash_token(token),
        created_at=now,
        last_seen_at=now,
        expires_at=now + settings.session_ttl,
        user_agent=user_agent[:512] if user_agent else None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return token, session


def validate_session(db: Session, token: str) -> UserSession | None:
    """Возвращает живую сессию и продлевает её; истёкшую удаляет."""
    session = db.scalar(
        select(UserSession).where(UserSession.token_hash == hash_token(token))
    )
    if session is None:
        return None

    now = now_local()
    if session.expires_at <= now:
        db.delete(session)
        db.commit()
        return None

    session.last_seen_at = now
    session.expires_at = now + settings.session_ttl
    db.commit()
    db.refresh(session)
    return session


def revoke_session(db: Session, token: str) -> bool:
    """Удаляет сессию. Возвращает True, если сессия существовала."""
    session = db.scalar(
        select(UserSession).where(UserSession.token_hash == hash_token(token))
    )
    if session is None:
        return False
    db.delete(session)
    db.commit()
    return True


def revoke_user_sessions(
    db: Session, user_id: int, *, except_token: str | None = None
) -> None:
    statement = delete(UserSession).where(UserSession.user_id == user_id)
    if except_token is not None:
        statement = statement.where(
            UserSession.token_hash != hash_token(except_token)
        )
    db.execute(statement)
