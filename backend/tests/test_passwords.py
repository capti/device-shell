from app.services.passwords import hash_password, verify_password


def test_password_is_hashed_with_argon2id() -> None:
    password = "secret123"
    password_hash = hash_password(password)

    assert password_hash.startswith("$argon2id$")
    assert password not in password_hash
    assert verify_password(password_hash, password) is True
    assert verify_password(password_hash, "wrong-password") is False


def test_invalid_hash_is_rejected() -> None:
    assert verify_password("not-a-hash", "secret123") is False
