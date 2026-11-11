"""The Quote entity: one priced answer to one request.

The quote holds a single total and a note, as agreed. Itemised quoting is a
later addition: it adds a line list to this entity, and the request and the
endpoints stay as they are.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from app.domain.enums import QuoteState
from app.domain.money import GST_RATE_BP, MAX_AMOUNT_CENTS, gst_component, grand_total

MAX_NOTE: int = 500
MAX_VERSIONS: int = 3
MIN_VALID_DAYS: int = 1
MAX_VALID_DAYS: int = 90


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    """Return the business date on the local calendar.

    Timestamps stay in UTC, but a validity window is a calendar promise to the
    person who made it. In Singapore the UTC date is still yesterday until 08:00
    local, which would shorten every quote by one day.
    """
    return datetime.now(timezone.utc).astimezone().date()


@dataclass
class Quote:
    """One total, one validity date, one state."""

    request_id: str
    total_cents: int
    valid_until: date
    gst_included: bool = False
    gst_rate_bp: int = GST_RATE_BP
    note: str = ""
    version: int = 1
    state: QuoteState = QuoteState.OFFERED
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime | None = None
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        """Check the amount, the note and the validity window."""
        if not self.request_id.strip():
            raise ValueError("A quote needs a request")
        if self.total_cents <= 0:
            raise ValueError("A quote total must be above zero")
        if self.total_cents > MAX_AMOUNT_CENTS:
            raise ValueError("A quote total is above the allowed ceiling")
        if self.gst_rate_bp < 0 or self.gst_rate_bp > 2000:
            raise ValueError("A tax rate must sit between 0 and 20 percent")
        self.note = self.note.strip()
        if len(self.note) > MAX_NOTE:
            raise ValueError(f"A note must be {MAX_NOTE} characters or fewer")
        window = (self.valid_until - _today()).days
        if window < MIN_VALID_DAYS or window > MAX_VALID_DAYS:
            raise ValueError(
                f"A quote must be valid for {MIN_VALID_DAYS} to {MAX_VALID_DAYS} days"
            )
        if self.version < 1 or self.version > MAX_VERSIONS:
            raise ValueError(f"A request may hold at most {MAX_VERSIONS} versions")
        if self.updated_at is None:
            self.updated_at = self.created_at

    @property
    def gst_cents(self) -> int:
        """Return the tax inside or on top of the total."""
        return gst_component(self.total_cents, self.gst_rate_bp, self.gst_included)

    @property
    def grand_total_cents(self) -> int:
        """Return what the customer pays."""
        return grand_total(self.total_cents, self.gst_rate_bp, self.gst_included)

    def is_expired(self, today: date | None = None) -> bool:
        """Return whether the validity date passed."""
        return (today or _today()) > self.valid_until

    def supersede(self) -> None:
        """Retire this version because a newer one exists."""
        if self.state is not QuoteState.OFFERED:
            raise ValueError("Only an offered quote can be superseded")
        self.state = QuoteState.SUPERSEDED
        self._touch()

    def accept(self) -> None:
        """The customer takes this quote."""
        if self.state is not QuoteState.OFFERED:
            raise ValueError("Only an offered quote can be accepted")
        if self.is_expired():
            raise ValueError("An expired quote cannot be accepted")
        self.state = QuoteState.ACCEPTED
        self._touch()

    def decline(self, reason: str = "") -> None:
        """The customer turns this quote down."""
        if self.state is not QuoteState.OFFERED:
            raise ValueError("Only an offered quote can be declined")
        self.state = QuoteState.DECLINED
        if reason.strip():
            self.note = f"{self.note}\nDeclined: {reason.strip()}".strip()[:MAX_NOTE]
        self._touch()

    def expire(self) -> None:
        """Close a quote whose validity date passed."""
        if self.state is QuoteState.OFFERED:
            self.state = QuoteState.EXPIRED
            self._touch()

    @classmethod
    def validity_date(cls, days: int, today: date | None = None) -> date:
        """Return the date ``days`` from now, after checking the window."""
        if days < MIN_VALID_DAYS or days > MAX_VALID_DAYS:
            raise ValueError(
                f"A quote must be valid for {MIN_VALID_DAYS} to {MAX_VALID_DAYS} days"
            )
        return (today or _today()) + timedelta(days=days)

    def _touch(self) -> None:
        self.updated_at = _now()