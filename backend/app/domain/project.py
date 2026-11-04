"""The Project entity: one finished or running interior design job.

A project belongs to a designer and to that designer's company. It carries the
photos, the style, the category and the budget band a customer filters on, plus
the two interest counters the designer reads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.domain.enums import ProjectStatus

MAX_TITLE_LENGTH: int = 120
MAX_IMAGES: int = 8


@dataclass
class Project:
    """One entry in a designer's portfolio."""

    owner_id: str
    company_id: str
    title: str
    description: str = ""
    style: str = ""
    category: str = ""
    budget_min: int = 0
    budget_max: int = 0
    status: ProjectStatus = ProjectStatus.CURRENT
    images: list[str] = field(default_factory=list)
    view_count: int = 0
    shortlist_count: int = 0
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = None

    def __post_init__(self) -> None:
        """Check the values a project cannot be created without."""
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("Project title must not be empty")
        if len(self.title) > MAX_TITLE_LENGTH:
            raise ValueError(f"Project title must be {MAX_TITLE_LENGTH} characters or fewer")
        self.description = self.description.strip()
        self.style = self.style.strip()
        self.category = self.category.strip()
        self._require_valid_budget(self.budget_min, self.budget_max)
        self.images = [url.strip() for url in self.images if url.strip()]
        if self.updated_at is None:
            self.updated_at = self.created_at

    def rename(self, title: str) -> None:
        """Replace the project title."""
        candidate = title.strip()
        if not candidate:
            raise ValueError("Project title must not be empty")
        if len(candidate) > MAX_TITLE_LENGTH:
            raise ValueError(f"Project title must be {MAX_TITLE_LENGTH} characters or fewer")
        self.title = candidate
        self._touch()

    def update_details(
        self,
        *,
        description: str,
        style: str,
        category: str,
        budget_min: int,
        budget_max: int,
    ) -> None:
        """Replace the searchable details after checking them."""
        clean_style = style.strip()
        clean_category = category.strip()
        if not clean_style:
            raise ValueError("Style must not be empty")
        if not clean_category:
            raise ValueError("Category must not be empty")
        self._require_valid_budget(budget_min, budget_max)
        self.description = description.strip()
        self.style = clean_style
        self.category = clean_category
        self.budget_min = budget_min
        self.budget_max = budget_max
        self._touch()

    def mark_past(self) -> None:
        """Mark the job as finished."""
        self.status = ProjectStatus.PAST
        self._touch()

    def mark_current(self) -> None:
        """Mark the job as still running."""
        self.status = ProjectStatus.CURRENT
        self._touch()

    def add_image(self, url: str) -> None:
        """Attach a photo address. A repeated address changes nothing."""
        candidate = url.strip()
        if not candidate:
            raise ValueError("Image address must not be empty")
        if candidate in self.images:
            return
        if len(self.images) >= MAX_IMAGES:
            raise ValueError(f"A project may hold at most {MAX_IMAGES} images")
        self.images.append(candidate)
        self._touch()

    def remove_image(self, url: str) -> None:
        """Detach a photo address when it is present."""
        candidate = url.strip()
        if candidate in self.images:
            self.images.remove(candidate)
            self._touch()

    def replace_images(self, urls: list[str]) -> None:
        """Replace the whole photo list, dropping blank and repeated entries."""
        cleaned = list(dict.fromkeys(url.strip() for url in urls if url.strip()))
        if len(cleaned) > MAX_IMAGES:
            raise ValueError(f"A project may hold at most {MAX_IMAGES} images")
        self.images = cleaned
        self._touch()

    def record_view(self) -> None:
        """Count one look at the detail page."""
        self.view_count += 1

    def record_shortlist(self) -> None:
        """Count one customer saving this project."""
        self.shortlist_count += 1

    def withdraw_shortlist(self) -> None:
        """Count one customer removing it. The count never falls below zero."""
        self.shortlist_count = max(0, self.shortlist_count - 1)

    def is_owned_by(self, account_id: str) -> bool:
        """Return ``True`` when ``account_id`` is the designer behind this project."""
        return self.owner_id == account_id

    @staticmethod
    def _require_valid_budget(minimum: int, maximum: int) -> None:
        if minimum < 0 or maximum < 0:
            raise ValueError("Budget must not be negative")
        if minimum > maximum:
            raise ValueError("Minimum budget must not exceed the maximum")

    def _touch(self) -> None:
        self.updated_at = datetime.now(timezone.utc)