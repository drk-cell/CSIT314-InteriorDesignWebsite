"""The Shortlist entity: the projects one customer saved.

One list per customer. It keeps project ids only, because a project can be
deleted or unpublished while the list stays.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

MAX_ENTRIES: int = 100


@dataclass
class Shortlist:
    """The saved projects of one customer, oldest first."""

    customer_id: str
    project_ids: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Drop blank and repeated entries, and refuse an oversized list."""
        self.customer_id = self.customer_id.strip()
        if not self.customer_id:
            raise ValueError("A shortlist needs a customer")
        cleaned = list(dict.fromkeys(entry.strip() for entry in self.project_ids if entry.strip()))
        if len(cleaned) > MAX_ENTRIES:
            raise ValueError(f"A shortlist may hold at most {MAX_ENTRIES} projects")
        self.project_ids = cleaned
        if self.updated_at is None:
            self.updated_at = self.created_at

    def add(self, project_id: str) -> bool:
        """Save a project. Returns ``False`` when it was already saved."""
        key = project_id.strip()
        if not key:
            raise ValueError("A project id must not be empty")
        if key in self.project_ids:
            return False
        if len(self.project_ids) >= MAX_ENTRIES:
            raise ValueError(f"A shortlist may hold at most {MAX_ENTRIES} projects")
        self.project_ids.append(key)
        self._touch()
        return True

    def remove(self, project_id: str) -> bool:
        """Drop a project. Returns ``False`` when it was not saved."""
        key = project_id.strip()
        if key not in self.project_ids:
            return False
        self.project_ids.remove(key)
        self._touch()
        return True

    def contains(self, project_id: str) -> bool:
        """Return whether the project is saved."""
        return project_id.strip() in self.project_ids

    def __len__(self) -> int:
        return len(self.project_ids)

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)