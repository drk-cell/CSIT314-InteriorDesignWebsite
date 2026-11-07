"""The QuoteRequest entity: one customer asking one company for a price.

A request is total-priced on purpose. The quote carries one figure and a note.
The seam for itemised quoting is ``Quote.note``: when line items arrive, they
hang off the quote and the request does not change.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from app.domain.enums import QuoteRequestState

MAX_TITLE: int = 120
MAX_SCOPE: int = 2000
MAX_NOTE: int = 500
MAX_COUNTERS: int = 3
OPEN_DAYS: int = 30


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Counter:
    """One target price the customer named, with a note."""

    target_cents: int
    note: str
    created_at: datetime
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        if self.target_cents <= 0:
            raise ValueError("A target price must be above zero")
        if len(self.note) > MAX_NOTE:
            raise ValueError(f"A note must be {MAX_NOTE} characters or fewer")


@dataclass
class QuoteRequest:
    """One customer's request to one company."""

    customer_id: str
    company_id: str
    title: str
    scope: str
    budget_min_cents: int = 0
    budget_max_cents: int = 0
    target_cents: int | None = None
    project_id: str | None = None
    state: QuoteRequestState = QuoteRequestState.PENDING
    counters: list[Counter] = field(default_factory=list)
    closed_reason: str = ""
    consent_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime | None = None
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        """Check what a request cannot be created without."""
        self.customer_id = self.customer_id.strip()
        self.company_id = self.company_id.strip()
        if not self.customer_id or not self.company_id:
            raise ValueError("A request needs a customer and a company")
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("A request needs a title")
        if len(self.title) > MAX_TITLE:
            raise ValueError(f"A title must be {MAX_TITLE} characters or fewer")
        self.scope = self.scope.strip()
        if not self.scope:
            raise ValueError("A request needs a scope")
        if len(self.scope) > MAX_SCOPE:
            raise ValueError(f"A scope must be {MAX_SCOPE} characters or fewer")
        if self.budget_min_cents < 0 or self.budget_max_cents < 0:
            raise ValueError("A budget must not be negative")
        if self.budget_max_cents < self.budget_min_cents:
            raise ValueError("The budget floor must not exceed the ceiling")
        if self.target_cents is not None and self.target_cents <= 0:
            raise ValueError("A target price must be above zero")
        if len(self.counters) > MAX_COUNTERS:
            raise ValueError(f"A request may hold at most {MAX_COUNTERS} counters")
        if self.consent_at is None:
            self.consent_at = self.created_at
        if self.updated_at is None:
            self.updated_at = self.created_at

    @property
    def is_open(self) -> bool:
        """Return whether the request still accepts an answer."""
        return self.state in (QuoteRequestState.PENDING, QuoteRequestState.ANSWERED)

    def counter(self, target_cents: int, note: str) -> Counter:
        """Record one target price from the customer."""
        if not self.is_open:
            raise ValueError("A closed request cannot take a counter")
        if len(self.counters) >= MAX_COUNTERS:
            raise ValueError(f"A request may hold at most {MAX_COUNTERS} counters")
        entry = Counter(target_cents=target_cents, note=note.strip(), created_at=_now())
        self.counters.append(entry)
        if self.target_cents is None:
            self.target_cents = target_cents
        self._touch()
        return entry

    def mark_answered(self) -> None:
        """Move to answered after the designer sends a quote."""
        if self.state is not QuoteRequestState.PENDING:
            raise ValueError("Only a pending request can be answered")
        self.state = QuoteRequestState.ANSWERED
        self._touch()

    def refuse(self, reason: str) -> None:
        """The designer declines to quote."""
        if self.state is not QuoteRequestState.PENDING:
            raise ValueError("Only a pending request can be refused")
        self.state = QuoteRequestState.REFUSED
        self.closed_reason = reason.strip()[:MAX_NOTE]
        self._touch()

    def cancel(self, reason: str) -> None:
        """The customer stops the request."""
        if not self.is_open:
            raise ValueError("Only an open request can be cancelled")
        self.state = QuoteRequestState.CANCELLED
        self.closed_reason = reason.strip()[:MAX_NOTE]
        self._touch()

    def accept(self) -> None:
        """The customer accepts the answer."""
        if self.state is not QuoteRequestState.ANSWERED:
            raise ValueError("Only an answered request can be accepted")
        self.state = QuoteRequestState.ACCEPTED
        self._touch()

    def decline(self, reason: str) -> None:
        """The customer turns the answer down."""
        if self.state is not QuoteRequestState.ANSWERED:
            raise ValueError("Only an answered request can be declined")
        self.state = QuoteRequestState.DECLINED
        self.closed_reason = reason.strip()[:MAX_NOTE]
        self._touch()

    def expire(self) -> None:
        """Close a request that ran out of time."""
        if not self.is_open:
            return
        self.state = QuoteRequestState.EXPIRED
        self._touch()

    def is_overdue(self, now: datetime | None = None) -> bool:
        """Return whether a pending request passed its open window."""
        if self.state is not QuoteRequestState.PENDING:
            return False
        moment = now or _now()
        return moment > self.updated_at + timedelta(days=OPEN_DAYS)

    def _touch(self) -> None:
        self.updated_at = _now()