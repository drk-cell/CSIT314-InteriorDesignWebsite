"""In memory storage for companies, one per designer."""

from __future__ import annotations

import threading

from app.domain.company import Company


class CompanyRepository:
    """Keeps every company in process memory.

    Two dictionaries are maintained: one keyed by company id, one keyed by the
    owner so the "one company per designer" rule is a single lookup. There is no
    database in this project, so the repository is the whole store.
    """

    def __init__(self) -> None:
        self._by_id: dict[str, Company] = {}
        self._id_by_owner: dict[str, str] = {}
        self._lock = threading.Lock()

    def add(self, company: Company) -> bool:
        """Store ``company`` unless its designer already has one.

        Returns whether the company was stored.
        """
        with self._lock:
            if company.owner_id in self._id_by_owner:
                return False
            self._by_id[company.id] = company
            self._id_by_owner[company.owner_id] = company.id
            return True

    def get(self, company_id: str) -> Company | None:
        """Return the company with ``company_id``, or ``None``."""
        return self._by_id.get(company_id)

    def get_by_owner(self, owner_id: str) -> Company | None:
        """Return the company owned by ``owner_id``, or ``None``."""
        company_id = self._id_by_owner.get(owner_id)
        if company_id is None:
            return None
        return self._by_id.get(company_id)

    def list_all(self) -> list[Company]:
        """Return every stored company."""
        return list(self._by_id.values())

    def count(self) -> int:
        """Return how many companies are stored."""
        return len(self._by_id)

    def clear(self) -> None:
        """Remove every stored company."""
        self._by_id.clear()
        self._id_by_owner.clear()