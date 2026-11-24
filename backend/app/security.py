"""Password hashing, tokens and field-level encryption.

Design notes (POPIA s19, security safeguards):
- Passwords: Argon2id, never stored or logged in plaintext.
- Access tokens: short lived JWT. Refresh tokens: random, stored only as SHA-256 hashes,
  rotated on every use, and the whole family is revoked if an old one is replayed.
- Health data (weight, height, date of birth, notes, food restrictions) is encrypted per field
  with Fernet before it reaches PostgreSQL, so a database leak alone does not expose it.
"""
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from sqlalchemy.types import Text, TypeDecorator

from .config import get_settings

_ph = PasswordHasher()  # argon2id defaults (RFC 9106 low-memory profile)
_DUMMY_HASH = _ph.hash("dummy-password-for-timing")


def hash_password(pw: str) -> str:
    return _ph.hash(pw)


def verify_password(pw: str, hashed: str | None) -> bool:
    """Constant-ish time: always does one Argon2 verify, even for unknown users."""
    try:
        return _ph.verify(hashed or _DUMMY_HASH, pw) and hashed is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


def password_problem(pw: str, email: str = "") -> str | None:
    if len(pw) < 10:
        return "Use at least 10 characters."
    if len(pw) > 128:
        return "Use at most 128 characters."
    if pw.lower() in {"password123", "1234567890", "qwerty12345", "password1234"}:
        return "That password is too common."
    local = email.split("@")[0].lower()
    if local and len(local) >= 4 and local in pw.lower():
        return "Do not include your email name in your password."
    if len(set(pw)) < 5:
        return "Use a wider mix of characters."
    return None


def email_hash(email: str) -> str:
    pepper = get_settings().email_hash_pepper.encode()
    return hmac.new(pepper, email.strip().lower().encode(), hashlib.sha256).hexdigest()


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()


def new_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_access_token(user_id: str, session_id: str) -> str:
    s = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "sid": session_id,
        "iat": now,
        "exp": now + timedelta(minutes=s.access_token_minutes),
        "typ": "access",
    }
    return jwt.encode(payload, s.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> dict | None:
    s = get_settings()
    try:
        data = jwt.decode(token, s.jwt_secret, algorithms=["HS256"], options={"require": ["exp", "sub", "sid"]})
    except jwt.PyJWTError:
        return None
    return data if data.get("typ") == "access" else None


# ---------- field encryption ----------
_fernet: MultiFernet | None = None


def _get_fernet() -> MultiFernet:
    global _fernet
    if _fernet is None:
        s = get_settings()
        keys = [k.strip() for k in s.field_encryption_keys.split(",") if k.strip()]
        if not keys:
            # Development fallback derived from the JWT secret. Production refuses to start without keys.
            import base64

            keys = [base64.urlsafe_b64encode(hashlib.sha256(("dev:" + s.jwt_secret).encode()).digest()).decode()]
        _fernet = MultiFernet([Fernet(k.encode()) for k in keys])
    return _fernet


def reset_crypto_cache() -> None:
    global _fernet
    _fernet = None


def encrypt_str(plain: str) -> str:
    return _get_fernet().encrypt(plain.encode()).decode()


def decrypt_str(token: str) -> str:
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken as e:  # wrong key or tampered data: fail closed
        raise ValueError("Cannot decrypt stored value") from e


class EncryptedJSON(TypeDecorator):
    """Stores any JSON value as Fernet ciphertext in a TEXT column."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return None if value is None else encrypt_str(json.dumps(value, separators=(",", ":")))

    def process_result_value(self, value, dialect):
        return None if value is None else json.loads(decrypt_str(value))
