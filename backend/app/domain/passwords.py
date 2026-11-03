"""Password hashing, standard library only.

This module sits inside the domain package on purpose. The Account entity owns
the rule "this password belongs to this account", so it may not depend on the
token module, which needs configuration and a JWT library.
"""

from __future__ import annotations

import hashlib
import hmac
import os

SCHEME: str = "pbkdf2_sha256"
PBKDF2_ITERATIONS: int = 120_000
SALT_BYTES: int = 16


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