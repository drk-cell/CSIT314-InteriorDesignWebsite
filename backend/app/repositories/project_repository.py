"""In memory storage for portfolio projects."""

from __future__ import annotations

import threading

from app.domain.project import Project


class ProjectRepository:
    """Keeps every project in process memory, keyed by id.

    A designer may hold many projects, so there is no unique key per owner.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, Project] = {}
        self._lock = threading.Lock()

    def add(self, project: Project) -> bool:
        """Store ``project`` unless its id is already present."""
        with self._lock:
            if project.id in self._by_id:
                return False
            self._by_id[project.id] = project
            return True

    def get(self, project_id: str) -> Project | None:
        """Return the project with ``project_id``, or ``None``."""
        return self._by_id.get(project_id)

    def list_by_owner(self, owner_id: str) -> list[Project]:
        """Return the projects owned by ``owner_id``."""
        return [project for project in self._by_id.values() if project.owner_id == owner_id]

    def list_by_company(self, company_id: str) -> list[Project]:
        """Return the projects published under ``company_id``."""
        return [
            project for project in self._by_id.values() if project.company_id == company_id
        ]

    def list_all(self) -> list[Project]:
        """Return every stored project."""
        return list(self._by_id.values())

    def count(self) -> int:
        """Return how many projects are stored."""
        return len(self._by_id)

    def remove(self, project_id: str) -> bool:
        """Drop the project with ``project_id``. Returns whether it was present."""
        with self._lock:
            return self._by_id.pop(project_id, None) is not None

    def clear(self) -> None:
        """Remove every stored project."""
        self._by_id.clear()