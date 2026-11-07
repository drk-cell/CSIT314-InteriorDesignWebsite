"""In memory storage for quote requests and quotes."""

from __future__ import annotations

import threading

from app.domain.quote import Quote
from app.domain.quote_request import QuoteRequest


class QuoteRequestRepository:
    """Keeps every request in process memory, keyed by id."""

    def __init__(self) -> None:
        self._by_id: dict[str, QuoteRequest] = {}
        self._lock = threading.Lock()

    def add(self, request: QuoteRequest) -> bool:
        """Store ``request`` unless its id is already present."""
        with self._lock:
            if request.id in self._by_id:
                return False
            self._by_id[request.id] = request
            return True

    def get(self, request_id: str) -> QuoteRequest | None:
        """Return the request with ``request_id``, or ``None``."""
        return self._by_id.get(request_id)

    def list_by_customer(self, customer_id: str) -> list[QuoteRequest]:
        """Return the requests a customer sent."""
        return [entry for entry in self._by_id.values() if entry.customer_id == customer_id]

    def list_by_company(self, company_id: str) -> list[QuoteRequest]:
        """Return the requests a company received."""
        return [entry for entry in self._by_id.values() if entry.company_id == company_id]

    def list_all(self) -> list[QuoteRequest]:
        """Return every stored request."""
        return list(self._by_id.values())

    def count(self) -> int:
        """Return how many requests are stored."""
        return len(self._by_id)

    def clear(self) -> None:
        """Remove every stored request."""
        self._by_id.clear()


class QuoteRepository:
    """Keeps every quote version, keyed by id."""

    def __init__(self) -> None:
        self._by_id: dict[str, Quote] = {}
        self._lock = threading.Lock()

    def add(self, quote: Quote) -> bool:
        """Store ``quote`` unless its id is already present."""
        with self._lock:
            if quote.id in self._by_id:
                return False
            self._by_id[quote.id] = quote
            return True

    def get(self, quote_id: str) -> Quote | None:
        """Return the quote with ``quote_id``, or ``None``."""
        return self._by_id.get(quote_id)

    def list_by_request(self, request_id: str) -> list[Quote]:
        """Return every version of a request's quote, oldest first."""
        versions = [
            entry for entry in self._by_id.values() if entry.request_id == request_id
        ]
        return sorted(versions, key=lambda entry: entry.version)

    def latest_for_request(self, request_id: str) -> Quote | None:
        """Return the newest version of a request's quote."""
        versions = self.list_by_request(request_id)
        return versions[-1] if versions else None

    def list_all(self) -> list[Quote]:
        """Return every stored quote."""
        return list(self._by_id.values())

    def count(self) -> int:
        """Return how many quotes are stored."""
        return len(self._by_id)

    def clear(self) -> None:
        """Remove every stored quote."""
        self._by_id.clear()