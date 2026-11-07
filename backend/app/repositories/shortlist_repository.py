"""In memory storage for customer shortlists, one per customer."""

from __future__ import annotations

import threading

from app.domain.shortlist import Shortlist


class ShortlistRepository:
    """Keeps one shortlist per customer id."""

    def __init__(self) -> None:
        self._by_customer: dict[str, Shortlist] = {}
        self._lock = threading.Lock()

    def add(self, shortlist: Shortlist) -> bool:
        """Store ``shortlist`` unless that customer already has one."""
        with self._lock:
            if shortlist.customer_id in self._by_customer:
                return False
            self._by_customer[shortlist.customer_id] = shortlist
            return True

    def get_by_customer(self, customer_id: str) -> Shortlist | None:
        """Return the shortlist of ``customer_id``, or ``None``."""
        return self._by_customer.get(customer_id)

    def count(self) -> int:
        """Return how many shortlists exist."""
        return len(self._by_customer)

    def clear(self) -> None:
        """Remove every shortlist."""
        self._by_customer.clear()