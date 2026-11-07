"""The Category entity: one room category the catalogue offers.

Categories live in a store rather than a constant, because platform staff
manage them. A category is archived, never deleted, so old projects keep a
label that still reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

MAX_NAME: int = 60


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class Category:
    """One room category, active or archived."""

    name: str
    active: bool = True
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        self.name = self._clean(self.name)
        if self.updated_at is None:
            self.updated_at = self.created_at

    def rename(self, name: str) -> None:
        """Replace the label."""
        self.name = self._clean(name)
        self.updated_at = _now()

    def archive(self) -> None:
        """Hide the category from the dropdowns."""
        self.active = False
        self.updated_at = _now()

    def restore(self) -> None:
        """Show the category again."""
        self.active = True
        self.updated_at = _now()

    @staticmethod
    def _clean(name: str) -> str:
        candidate = name.strip()
        if not candidate:
            raise ValueError("A category name must not be empty")
        if len(candidate) > MAX_NAME:
            raise ValueError(f"A category name must be {MAX_NAME} characters or fewer")
        return candidate