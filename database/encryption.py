import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

ENCRYPTED_PREFIX = "enc:v1:"


class DataEncryptionError(RuntimeError):
    """Raised when encrypted ticket data cannot be processed safely."""


@lru_cache(maxsize=8)
def _build_fernet(key: str) -> Fernet:
    try:
        return Fernet(key.encode("ascii"))
    except (TypeError, ValueError) as exc:
        raise DataEncryptionError(
            "DATA_ENCRYPTION_KEY has an invalid format. "
            "Run scripts/generate_encryption_key.py to create it."
        ) from exc


def _cipher() -> Fernet:
    key = os.getenv("DATA_ENCRYPTION_KEY", "").strip()
    if not key:
        raise DataEncryptionError(
            "DATA_ENCRYPTION_KEY is missing. "
            "Run scripts/generate_encryption_key.py before starting the bot."
        )
    return _build_fernet(key)


def validate_encryption_key() -> None:
    """Fail fast during startup when the encryption key is missing or invalid."""
    _cipher()


def encrypt_value(value: str | int | None) -> str | None:
    """Encrypt a value, preserving None and validating existing ciphertext."""
    if value is None:
        return None

    text = str(value)
    if text.startswith(ENCRYPTED_PREFIX):
        decrypt_value(text)
        return text

    token = _cipher().encrypt(text.encode("utf-8")).decode("ascii")
    return f"{ENCRYPTED_PREFIX}{token}"


def decrypt_value(value: str | int | None) -> str | None:
    """Decrypt a value while accepting legacy plaintext during migration."""
    if value is None:
        return None

    text = str(value)
    if not text.startswith(ENCRYPTED_PREFIX):
        return text

    token = text.removeprefix(ENCRYPTED_PREFIX)
    try:
        return _cipher().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeError) as exc:
        raise DataEncryptionError(
            "Ticket data cannot be decrypted. DATA_ENCRYPTION_KEY may be wrong."
        ) from exc


def decrypt_int(value: str | int | None) -> int | None:
    text = decrypt_value(value)
    return int(text) if text is not None else None
