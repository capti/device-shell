"""Хеширование и проверка паролей (argon2id)."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Возвращает argon2id-хеш пароля."""
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Проверяет пароль по хешу, не раскрывая причину несовпадения."""
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False
