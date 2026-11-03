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