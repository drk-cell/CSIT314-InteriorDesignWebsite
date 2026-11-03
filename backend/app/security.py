"""JSON Web Token creation and decoding.

Password hashing lives in ``app.domain.passwords`` so the entity layer does not
depend on this module, which needs configuration and a JWT library.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from app import config

ALGORITHM: str = "HS256"


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