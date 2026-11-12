"""Consultation booking use cases: offer slots, keep one, accept or cancel it.

Rules that matter and are easy to get wrong:

* A slot is one hour on a fixed grid, and one company holds it once.
* The diary looks 14 days ahead, today included.
* A customer holds at most one open appointment per company.
* Only the designer behind the company may accept it.
* Either party may cancel, and a cancelled slot returns to the grid.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.domain.account import Account
from app.domain.appointment import (
    BOOKING_DAYS,
    SLOT_TIMES,
    ConsultationAppointment,
    is_bookable_date,
)
from app.domain.enums import AppointmentState, ConsultationMode, Role
from app.domain.errors import (
    AppointmentNotFound,
    CompanyNotFound,
    InvalidState,
    NotPermitted,
)
from app.repositories.account_repository import AccountRepository
from app.repositories.appointment_repository import AppointmentRepository
from app.repositories.company_repository import CompanyRepository


class AppointmentService:
    """Applies the booking rules on top of the three stores."""

    def __init__(
        self,
        appointments: AppointmentRepository,
        companies: CompanyRepository,
        accounts: AccountRepository,
    ) -> None:
        self._appointments = appointments
        self._companies = companies
        self._accounts = accounts

    # --- customer side ----------------------------------------------------

    def available_slots(self, actor: Account, company_id: str, day: date) -> list[str]:
        """Return the hours still free on one company's day."""
        company = self._companies.get(company_id)
        if company is None:
            raise CompanyNotFound()
        if not is_bookable_date(day):
            raise ValueError(f"Choose a day inside the next {BOOKING_DAYS} days")
        blocked = self._appointments.taken_times(company.id, day)
        cutoff = self._cutoff(day)
        return [slot for slot in SLOT_TIMES if slot not in blocked and slot > cutoff]

    def book(
        self,
        actor: Account,
        company_id: str,
        day: date,
        time: str,
        mode: ConsultationMode = ConsultationMode.IN_PERSON,
        requirements: str = "",
    ) -> ConsultationAppointment:
        """Keep one slot for one customer, in person or on a call."""
        self._require_customer(actor)
        company = self._companies.get(company_id)
        if company is None:
            raise CompanyNotFound()
        for existing in self._appointments.list_by_customer(actor.id):
            if existing.company_id == company.id and existing.is_open:
                raise InvalidState(
                    "You already hold an appointment with this company"
                )
        place = company.meeting_place(mode is ConsultationMode.ONLINE)
        if not place:
            if mode is ConsultationMode.ONLINE:
                raise InvalidState("This designer has not set a call link yet")
            raise InvalidState("This designer has not set a meeting place yet")
        appointment = ConsultationAppointment(
            customer_id=actor.id,
            company_id=company.id,
            appointment_date=day,
            appointment_time=time,
            location=place,
            mode=mode,
            requirements=requirements,
        )
        if not self._appointments.add_if_free(appointment):
            raise InvalidState(
                "That time was taken while you were booking. Choose another time."
            )
        self._notify_designer(appointment)
        return appointment

    def list_for_customer(self, actor: Account) -> list[ConsultationAppointment]:
        """Return the caller's appointments, soonest first."""
        if actor.role is not Role.CUSTOMER:
            raise NotPermitted("Only a customer books a consultation")
        return self._sorted(self._appointments.list_by_customer(actor.id))

    def cancel(self, actor: Account, appointment_id: str) -> ConsultationAppointment:
        """Return a slot to the diary. Either party may cancel."""
        appointment = self._get(appointment_id)
        if not self._may_cancel(actor, appointment):
            raise NotPermitted("You may not cancel this appointment")
        try:
            appointment.cancel()
        except ValueError as exc:
            raise InvalidState(str(exc)) from exc
        return appointment

    # --- designer side ----------------------------------------------------

    def list_for_designer(self, actor: Account) -> list[ConsultationAppointment]:
        """Return the appointments sent to the caller's company, soonest first."""
        company = self._company_of(actor)
        return self._sorted(self._appointments.list_by_company(company.id))

    def accept(self, actor: Account, appointment_id: str) -> ConsultationAppointment:
        """Confirm a pending appointment."""
        appointment = self._get(appointment_id)
        company = self._company_of(actor)
        if appointment.company_id != company.id:
            raise NotPermitted("This appointment went to another company")
        try:
            appointment.accept()
        except ValueError as exc:
            raise InvalidState(str(exc)) from exc
        return appointment

    # --- reading ----------------------------------------------------------

    def customer_name(self, appointment: ConsultationAppointment) -> str:
        """Return the customer's display name for the designer's list."""
        account = self._accounts.get(appointment.customer_id)
        return "" if account is None else account.display_name

    # --- helpers ----------------------------------------------------------

    @staticmethod
    def _cutoff(day: date) -> str:
        """Return the clock time before which today's slots are gone."""
        now = datetime.now(timezone.utc).astimezone()
        return now.strftime("%H:%M") if day == now.date() else "00:00"

    @staticmethod
    def _sorted(
        appointments: list[ConsultationAppointment],
    ) -> list[ConsultationAppointment]:
        return sorted(
            appointments,
            key=lambda entry: (entry.appointment_date, entry.appointment_time),
        )

    def _get(self, appointment_id: str) -> ConsultationAppointment:
        appointment = self._appointments.get(appointment_id)
        if appointment is None:
            raise AppointmentNotFound()
        return appointment

    def _may_cancel(self, actor: Account, appointment: ConsultationAppointment) -> bool:
        if actor.role is Role.CUSTOMER:
            return appointment.customer_id == actor.id
        if actor.role is Role.DESIGNER:
            company = self._companies.get_by_owner(actor.id)
            return company is not None and company.id == appointment.company_id
        return False

    def _company_of(self, actor: Account):
        if actor.role is not Role.DESIGNER:
            raise NotPermitted("Only a designer has a company diary")
        company = self._companies.get_by_owner(actor.id)
        if company is None:
            raise CompanyNotFound()
        return company

    def _notify_designer(self, appointment: ConsultationAppointment) -> None:
        """Tell the designer.

        The platform has no mail server, so the inbox is the notification: the
        appointment appears in the designer's list and carries the time it was
        reported. Writing a fake email here would be a lie in the data.
        """
        appointment.mark_notified()

    @staticmethod
    def _require_customer(actor: Account) -> None:
        if actor.role is not Role.CUSTOMER:
            raise NotPermitted("Only a customer may book a consultation")
