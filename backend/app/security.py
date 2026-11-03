"""Password hashing and access token primitives.

Passwords are stored as ``pbkdf2_sha256$iterations$salt$hash`` using only the
standard library. Tokens are signed JSON Web Tokens carrying the account id,
the account role and the usual timing claims.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app import config

SCHEME: str = "pbkdf2_sha256"
PBKDF2_ITERATIONS: int = 120_000
SALT_BYTES: int = 16
ALGORITHM: str = "HS256"


def hash_password(raw: str) -> str:
    """Return a salted PBKDF2-SHA256 hash of ``raw`` in a self describing format."""
    salt = os.urandom(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"{SCHEME}${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(raw: str, stored: str) -> bool:
    """Return ``True`` when ``raw`` matches ``stored``.

    A malformed or truncated stored value simply yields ``False`` so callers
    never have to guard against corrupt records.
    """
    try:
        scheme, iterations_raw, salt_hex, hash_hex = stored.split("$")
        if scheme != SCHEME:
            return False
        iterations = int(iterations_raw)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(hash_hex)
    except (AttributeError, TypeError, ValueError):
        return False
    if iterations <= 0 or not salt or not expected:
        return False
    digest = hashlib.pbkdf2_hmac(
        "sha256", raw.encode("utf-8"), salt, iterations, dklen=len(expected)
    )
    return hmac.compare_digest(digest, expected)


def create_access_token(account_id: str, role: str, expires_minutes: int) -> str:
    """Return a signed HS256 token for ``account_id`` holding ``role``."""
    issued_at = datetime.now(timezone.utc)
    claims: dict[str, Any] = {
        "sub": account_id,
        "role": role,
        "iat": issued_at,
        "exp": issued_at + timedelta(minutes=expires_minutes),
    }
    return jwt.encode(claims, config.get_secret_key(), algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Return the claims of ``token``.

    Raises ``ValueError`` for anything the API layer should treat as an
    unauthenticated request: bad signature, expired token, missing subject.
    """
    try:
        claims = jwt.decode(token, config.get_secret_key(), algorithms=[ALGORITHM])
    except (jwt.PyJWTError, TypeError, ValueError) as exc:
        raise ValueError("Invalid or expired token") from exc
    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise ValueError("Invalid or expired token")
    return claims