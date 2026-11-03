"""The Account entity.

The entity owns both its state and the rules that govern it: password
checking, lifecycle transitions and role based privilege. Services arrange
work, but only the entity decides what a valid account operation is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.domain.enums import AccountStatus, Role
from app.domain.passwords import verify_password


@dataclass
class Account:
    """A single platform account."""

    email: str
    display_name: str
    password_hash: str
    role: Role
    status: AccountStatus = AccountStatus.PENDING
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Normalise the values identity depends on."""
        self.email = self.email.strip().lower()
        self.display_name = self.display_name.strip()

    def check_password(self, raw: str) -> bool:
        """Return ``True`` when ``raw`` is this account's password."""
        return verify_password(raw, self.password_hash)

    def activate(self) -> None:
        """Move the account into the ACTIVE status."""
        self.status = AccountStatus.ACTIVE

    def suspend(self) -> None:
        """Move the account into the SUSPENDED status."""
        self.status = AccountStatus.SUSPENDED

    def can_login(self) -> bool:
        """Return ``True`` only while the account is ACTIVE."""
        return self.status is AccountStatus.ACTIVE

    def change_display_name(self, name: str) -> None:
        """Replace the display name with ``name``.

        Raises ``ValueError`` when the new name is blank; that guard is a
        programming error rather than a flow the API is expected to surface.
        """
        candidate = name.strip()
        if not candidate:
            raise ValueError("Display name must not be empty")
        self.display_name = candidate

    def is_privileged(self) -> bool:
        """Return ``True`` for administrators and platform managers."""
        return self.role.is_privileged