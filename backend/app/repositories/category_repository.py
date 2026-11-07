"""In memory storage for room categories, seeded from the default list."""

from __future__ import annotations

import threading

from app.domain import catalogue
from app.domain.category import Category


class CategoryRepository:
    """Keeps every category, active or archived."""

    def __init__(self) -> None:
        self._by_id: dict[str, Category] = {}
        self._lock = threading.Lock()
        self.reset_defaults()

    def reset_defaults(self) -> None:
        """Replace the store with the ten default categories."""
        with self._lock:
            self._by_id = {}
            for name in catalogue.CATEGORIES:
                category = Category(name=name)
                self._by_id[category.id] = category

    def list_all(self) -> list[Category]:
        """Return every category, sorted by name."""
        return sorted(self._by_id.values(), key=lambda entry: entry.name.casefold())

    def list_active(self) -> list[Category]:
        """Return the categories a dropdown should show."""
        return [entry for entry in self.list_all() if entry.active]

    def get(self, category_id: str) -> Category | None:
        """Return the category with ``category_id``, or ``None``."""
        return self._by_id.get(category_id)

    def find_by_name(self, name: str) -> Category | None:
        """Return the category whose label matches, ignoring case."""
        wanted = name.strip().casefold()
        for entry in self._by_id.values():
            if entry.name.casefold() == wanted:
                return entry
        return None

    def add(self, category: Category) -> bool:
        """Store a category unless its id or its name is already present."""
        with self._lock:
            if category.id in self._by_id:
                return False
            if any(
                entry.name.casefold() == category.name.casefold()
                for entry in self._by_id.values()
            ):
                return False
            self._by_id[category.id] = category
            return True

    def count(self) -> int:
        """Return how many categories exist."""
        return len(self._by_id)