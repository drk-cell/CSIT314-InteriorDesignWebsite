"""The ConsultationAppointment entity: one hour a designer kept for a customer.

A booking names a company, a day and one slot from a fixed grid. The entity
owns the rules that need no other record: the slot must exist, the day must sit
inside the booking window, and the state moves forward only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

from app.domain.enums import AppointmentState

SLOT_TIMES: tuple[str, ...] = (
    "09:00",
    "10:00",
    "11:00",
    "12:00",
    "13:00",
    "14:00",
    "15:00",
    "16:00",
    "17:00",
)
"""The hours a designer may be booked for. One appointment fills one hour."""

BOOKING_DAYS: int = 14
"""How far ahead a customer may book, counting today as day one."""

MAX_REQUIREMENTS: int = 1000


def _now() -> datetime:
    return datetime.now(timezone.utc)


def local_today() -> date:
    """Return today on the local calendar.

    Timestamps stay in UTC, but "today" is a promise to the person booking. In
    Singapore the UTC date is still yesterday until 08:00 local.
    """
    return datetime.now(timezone.utc).astimezone().date()


def is_bookable_date(day: date, today: date | None = None) -> bool:
    """Return ``True`` when ``day`` sits inside the booking window."""
    start = today or local_today()
    return start <= day < start + timedelta(days=BOOKING_DAYS)


@dataclass
class ConsultationAppointment:
    """One slot a customer asked a designer to keep."""

    customer_id: str
    company_id: str
    appointment_date: date
    appointment_time: str
    requirements: str = ""
    state: AppointmentState = AppointmentState.PENDING
    notified_at: datetime | None = None
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime | None = None
    id: str = field(default_factory=lambda: str(uuid4()))

    def __post_init__(self) -> None:
        """Check the identifiers, the slot and the day."""
        if not self.customer_id.strip():
            raise ValueError("An appointment needs a customer")
        if not self.company_id.strip():
            raise ValueError("An appointment needs a company")
        if self.appointment_time not in SLOT_TIMES:
            raise ValueError("Choose one of the offered times")
        if not is_bookable_date(self.appointment_date):
            raise ValueError(
                f"Choose a day inside the next {BOOKING_DAYS} days"
            )
        self.requirements = self.requirements.strip()
        if len(self.requirements) > MAX_REQUIREMENTS:
            raise ValueError(
                f"Requirements must be {MAX_REQUIREMENTS} characters or fewer"
            )
        if self.updated_at is None:
            self.updated_at = self.created_at

    @property
    def is_open(self) -> bool:
        """Return ``True`` while the slot still blocks the diary."""
        return self.state in (AppointmentState.PENDING, AppointmentState.ACCEPTED)

    def is_pending(self) -> bool:
        """Return ``True`` until the designer answers."""
        return self.state is AppointmentState.PENDING

    def accept(self) -> None:
        """The designer confirms the slot."""
        if self.state is not AppointmentState.PENDING:
            raise ValueError("Only a pending appointment can be accepted")
        self.state = AppointmentState.ACCEPTED
        self._touch()

    def cancel(self) -> None:
        """Either party gives the slot back."""
        if self.state is AppointmentState.CANCELLED:
            raise ValueError("This appointment is already cancelled")
        self.state = AppointmentState.CANCELLED
        self._touch()

    def mark_notified(self) -> None:
        """Record that the designer was told about the new booking."""
        self.notified_at = _now()

    def _touch(self) -> None:
        self.updated_at = _now()
