"""In memory storage for project reports."""

from __future__ import annotations

import threading

from app.domain.report import ProjectReport


class ReportRepository:
    """Keeps every project report in process memory, keyed by id."""

    def __init__(self) -> None:
        self._by_id: dict[str, ProjectReport] = {}
        self._lock = threading.Lock()

    def add(self, report: ProjectReport) -> bool:
        """Store ``report`` unless its id is already present."""
        with self._lock:
            if report.id in self._by_id:
                return False
            self._by_id[report.id] = report
            return True

    def get(self, report_id: str) -> ProjectReport | None:
        """Return the report with ``report_id``, or ``None``."""
        return self._by_id.get(report_id)

    def list_by_customer(self, customer_id: str) -> list[ProjectReport]:
        """Return the reports one customer raised."""
        return [
            entry
            for entry in self._by_id.values()
            if entry.customer_id == customer_id
        ]

    def list_by_project(self, project_id: str) -> list[ProjectReport]:
        """Return the reports raised about one project."""
        return [
            entry for entry in self._by_id.values() if entry.project_id == project_id
        ]

    def list_all(self) -> list[ProjectReport]:
        """Return every stored report."""
        return list(self._by_id.values())

    def count(self) -> int:
        """Return how many reports are stored."""
        return len(self._by_id)

    def clear(self) -> None:
        """Remove every stored report."""
        self._by_id.clear()
