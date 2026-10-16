"""Вспомогательные функции для работы с данными и паролями."""

import binascii
import hashlib
import hmac
import os

HASH_ALGORITHM = "sha256"
HASH_ITERATIONS = 100_000
SALT_BYTES = 16
PASSWORD_MIN_LENGTH = 4


def create_password_hash(password: str, salt: str | None = None) -> tuple[str, str]:
    """Создаёт соль и хэш пароля с использованием PBKDF2-HMAC."""
    if len(password) < PASSWORD_MIN_LENGTH:
        raise ValueError(
            f"Пароль должен содержать не менее {PASSWORD_MIN_LENGTH} символов."
        )

    if salt is None:
        salt = binascii.hexlify(os.urandom(SALT_BYTES)).decode("ascii")

    password_hash = hashlib.pbkdf2_hmac(
        HASH_ALGORITHM,
        password.encode("utf-8"),
        salt.encode("utf-8"),
        HASH_ITERATIONS,
    ).hex()

    return salt, password_hash


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Проверяет пароль по сохранённой соли и хэшу."""
    _, actual_hash = create_password_hash(password, salt)
    return hmac.compare_digest(actual_hash, expected_hash)
