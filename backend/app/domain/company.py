"""The Company entity: the profile a designer presents to customers.

One designer holds one company. The entity owns the invariants: a name that is
not blank, a contact address with a domain, and an update timestamp that moves
whenever a field changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

MAX_NAME_LENGTH: int = 120


@dataclass
class Company:
    """A designer's company profile."""

    owner_id: str
    name: str
    description: str = ""
    contact_email: str = ""
    contact_phone: str = ""
    location: str = ""
    logo_url: str = ""
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Normalise the values customers will read."""
        self.name = self.name.strip()
        self.description = self.description.strip()
        self.contact_email = self.contact_email.strip().lower()
        self.contact_phone = self.contact_phone.strip()
        self.location = self.location.strip()
        self.logo_url = self.logo_url.strip()
        if self.updated_at is None:
            self.updated_at = self.created_at

    def rename(self, name: str) -> None:
        """Replace the company name."""
        candidate = name.strip()
        if not candidate:
            raise ValueError("Company name must not be empty")
        if len(candidate) > MAX_NAME_LENGTH:
            raise ValueError(
                f"Company name must be {MAX_NAME_LENGTH} characters or fewer"
            )
        self.name = candidate
        self._touch()

    def update_description(self, text: str) -> None:
        """Replace the description customers read."""
        self.description = text.strip()
        self._touch()

    def update_contact(self, email: str, phone: str) -> None:
        """Replace the contact pair after checking the address has a domain."""
        candidate = email.strip().lower()
        local_part, _, domain = candidate.partition("@")
        if not local_part or "." not in domain:
            raise ValueError("Enter a valid contact email address")
        self.contact_email = candidate
        self.contact_phone = phone.strip()
        self._touch()

    def set_location(self, location: str) -> None:
        """Replace the service area."""
        self.location = location.strip()
        self._touch()

    def attach_logo(self, url: str) -> None:
        """Point the profile at a logo image."""
        candidate = url.strip()
        if not candidate:
            raise ValueError("Logo address must not be empty")
        self.logo_url = candidate
        self._touch()

    def is_owned_by(self, account_id: str) -> bool:
        """Return ``True`` when ``account_id`` is the designer behind this company."""
        return self.owner_id == account_id

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)