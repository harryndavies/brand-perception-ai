"""Symmetric encryption for sensitive user data (e.g. API keys).

Uses a dedicated ENCRYPTION_KEY (Fernet), separate from the JWT SECRET_KEY,
so a JWT leak does not compromise stored secrets.
"""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import settings

# Derive a valid 32-byte Fernet key from ENCRYPTION_KEY via SHA-256.
# This lets ENCRYPTION_KEY be any string (including a raw Fernet key).
_fernet_key = base64.urlsafe_b64encode(hashlib.sha256(settings.encryption_key.encode()).digest())
_fernet = Fernet(_fernet_key)


def encrypt(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode()).decode()
