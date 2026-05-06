"""
Field-level encryption for sensitive personal data at rest.
Satisfies CTRL-0000001066 (encryption at rest for sensitive PD).

Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
Key is loaded from FIELD_ENCRYPTION_KEY env var — must be a 32-byte
URL-safe base64-encoded key. Generate with:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings
from django.db import models
import logging

logger = logging.getLogger(__name__)

_fernet_instance = None


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        key = getattr(settings, 'FIELD_ENCRYPTION_KEY', None)
        if not key:
            raise ValueError(
                "FIELD_ENCRYPTION_KEY is not set. "
                "Generate one with: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
            )
        _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet_instance


def encrypt_value(plaintext: str) -> str:
    """Encrypt a string value. Returns a Fernet token as a string."""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode('utf-8')).decode('utf-8')


def decrypt_value(ciphertext: str) -> str:
    """
    Decrypt a Fernet-encrypted string. Returns plaintext.
    Falls back to the original value if decryption fails (handles
    legacy unencrypted data that existed before encryption was enabled).
    """
    if not ciphertext:
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode('utf-8')).decode('utf-8')
    except (InvalidToken, Exception):
        # Legacy unencrypted data — return as-is and log for ops awareness
        logger.warning("decrypt_value: failed to decrypt field value; returning raw value (may be legacy unencrypted data)")
        return ciphertext


class EncryptedTextField(models.TextField):
    """
    Drop-in replacement for CharField/TextField that transparently
    encrypts on write and decrypts on read using Fernet.

    The encrypted ciphertext is longer than the plaintext (~100 bytes overhead),
    so the underlying DB column is TextField (unbounded).

    Usage:
        passport_number = EncryptedTextField(blank=True, null=True)
    """

    def from_db_value(self, value, expression, connection):
        if value is None or value == '':
            return value
        return decrypt_value(value)

    def to_python(self, value):
        if value is None or value == '':
            return value
        return decrypt_value(value)

    def get_prep_value(self, value):
        if value is None or value == '':
            return value
        return encrypt_value(value)
