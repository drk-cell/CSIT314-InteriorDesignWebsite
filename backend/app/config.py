"""Environment backed application settings.

Only two values are configurable at this stage: the JWT signing secret and
the lifetime of an access token. Both read from ``os.environ`` and fall back
to development defaults so the project runs without any setup.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_SECRET_KEY: str = "dev-only-change-me-32-bytes-minimum!!"
DEFAULT_TOKEN_MINUTES: int = 480
APP_VERSION: str = "0.1.0"
DEFAULT_ENVIRONMENT: str = "development"


def app_environment() -> str:
    """Return the deployment environment name, defaulting to development."""
    return os.environ.get("APP_ENV", DEFAULT_ENVIRONMENT).strip().lower()


def is_production() -> bool:
    """Return ``True`` when the process is not running in development."""
    return app_environment() != DEFAULT_ENVIRONMENT


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of the runtime configuration."""

    secret_key: str
    token_minutes: int

    def is_default_secret(self) -> bool:
        """Return ``True`` when the development secret is still in use."""
        return self.secret_key == DEFAULT_SECRET_KEY


def load_settings() -> Settings:
    """Build settings from the environment, ignoring unusable values."""
    secret_key = os.environ.get("APP_SECRET_KEY") or DEFAULT_SECRET_KEY
    raw_minutes = os.environ.get("APP_TOKEN_MINUTES", "")
    try:
        token_minutes = int(raw_minutes)
    except ValueError:
        token_minutes = DEFAULT_TOKEN_MINUTES
    if token_minutes <= 0:
        token_minutes = DEFAULT_TOKEN_MINUTES
    return Settings(secret_key=secret_key, token_minutes=token_minutes)


def get_secret_key() -> str:
    """Return the secret used to sign and verify tokens."""
    return load_settings().secret_key


def get_token_minutes() -> int:
    """Return the access token lifetime in minutes."""
    return load_settings().token_minutes


def is_default_secret() -> bool:
    """Return ``True`` when no real secret has been configured."""
    return load_settings().is_default_secret()


def get_bootstrap_admin_email() -> str:
    """Return the address of the first administrator, or an empty string."""
    return os.environ.get("APP_ADMIN_EMAIL", "").strip().lower()


def get_bootstrap_admin_password() -> str:
    """Return the starting password for the first administrator."""
    return os.environ.get("APP_ADMIN_PASSWORD", "")


STAFF_ROLE_NAMES: frozenset[str] = frozenset({"ADMIN", "PLATFORM_MANAGER"})


def get_bootstrap_admins() -> list[tuple[str, str, str, str]]:
    """Return the staff accounts to create at startup.

    Each entry is ``(email, password, display_name, role_name)``. When
    ``APP_ADMIN_ACCOUNTS`` is set it supplies the list as comma separated
    ``email:password:name:role`` items. Otherwise the single
    ``APP_ADMIN_EMAIL`` and ``APP_ADMIN_PASSWORD`` pair is used, when both
    are set.
    """
    raw_list = os.environ.get("APP_ADMIN_ACCOUNTS", "").strip()
    if raw_list:
        entries = _parse_admin_list(raw_list)
        if entries:
            return entries
    email = get_bootstrap_admin_email()
    password = get_bootstrap_admin_password()
    if email and password:
        return [(email, password, "Administrator", "ADMIN")]
    return []


def _parse_admin_list(raw: str) -> list[tuple[str, str, str, str]]:
    """Parse ``email:password:name:role`` entries separated by commas.

    Malformed entries and unprivileged roles are skipped. The password must
    not contain a colon.
    """
    entries: list[tuple[str, str, str, str]] = []
    for chunk in raw.split(","):
        parts = [part.strip() for part in chunk.split(":")]
        if len(parts) != 4:
            continue
        email, password, name, role = parts
        if not email or not password:
            continue
        if role.upper() not in STAFF_ROLE_NAMES:
            continue
        entries.append((email.lower(), password, name or "Administrator", role.upper()))
    return entries