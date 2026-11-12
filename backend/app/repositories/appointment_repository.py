"""In memory storage for consultation appointments."""

from __future__ import annotations

import threading
from datetime import date

from app.domain.appointment import ConsultationAppointment
from app.domain.enums import AppointmentState


class AppointmentRepository:
    """Keeps every appointment in process memory, keyed by id."""

    def __init__(self) -> None:
        self._by_id: dict[str, ConsultationAppointment] = {}
        self._lock = threading.Lock()

    def add(self, appointment: ConsultationAppointment) -> bool:
        """Store ``appointment`` unless its id is already present."""
        with self._lock:
            if appointment.id in self._by_id:
                return False
            self._by_id[appointment.id] = appointment
            return True

    def add_if_free(self, appointment: ConsultationAppointment) -> bool:
        """Store ``appointment`` only when the slot is still free.

        The check and the insert happen under one lock, so two customers cannot
        both win the same slot.
        """
        with self._lock:
            for entry in self._by_id.values():
                if (
                    entry.company_id == appointment.company_id
                    and entry.appointment_date == appointment.appointment_date
                    and entry.appointment_time == appointment.appointment_time
                    and entry.is_open
                ):
                    return False
            if appointment.id in self._by_id:
                return False
            self._by_id[appointment.id] = appointment
            return True

    def get(self, appointment_id: str) -> ConsultationAppointment | None:
        """Return the appointment with ``appointment_id``, or ``None``."""
        return self._by_id.get(appointment_id)

    def list_by_customer(self, customer_id: str) -> list[ConsultationAppointment]:
        """Return the appointments one customer booked."""
        return [
            entry
            for entry in self._by_id.values()
            if entry.customer_id == customer_id
        ]

    def list_by_company(self, company_id: str) -> list[ConsultationAppointment]:
        """Return the appointments one company received."""
        return [
            entry for entry in self._by_id.values() if entry.company_id == company_id
        ]

    def taken_times(self, company_id: str, day: date) -> set[str]:
        """Return the times already held on one company's day."""
        return {
            entry.appointment_time
            for entry in self._by_id.values()
            if entry.company_id == company_id
            and entry.appointment_date == day
            and entry.state
            in (AppointmentState.PENDING, AppointmentState.ACCEPTED)
        }

    def list_all(self) -> list[ConsultationAppointment]:
        """Return every stored appointment."""
        return list(self._by_id.values())

    def count(self) -> int:
        """Return how many appointments are stored."""
        return len(self._by_id)

    def clear(self) -> None:
        """Remove every stored appointment."""
        self._by_id.clear()
