"""Appointment boundary: show free hours, keep one, accept or cancel it."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import get_consultation_service, get_current_account
from app.domain.account import Account
from app.domain.enums import AppointmentState, ConsultationMode, Role
from app.domain.errors import (
    AppointmentNotFound,
    CompanyNotFound,
    InvalidState,
    NotPermitted,
)
from app.schemas.appointment import AppointmentPublic, BookRequest, SlotsPublic
from app.services.consultation_service import ConsultationService

router = APIRouter(prefix="/appointments", tags=["appointments"])

ServiceDep = Annotated[ConsultationService, Depends(get_consultation_service)]
CurrentAccountDep = Annotated[Account, Depends(get_current_account)]


def _fail(exc: Exception) -> HTTPException:
    """Map a domain refusal to the matching response."""
    if isinstance(exc, (AppointmentNotFound, CompanyNotFound)):
        return HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail=exc.message
        )
    if isinstance(exc, NotPermitted):
        return HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN, detail=exc.message
        )
    if isinstance(exc, InvalidState):
        return HTTPException(
            status_code=http_status.HTTP_409_CONFLICT, detail=exc.message
        )
    return HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _public(
    service: ConsultationService, appointment, actor: Account
) -> AppointmentPublic:
    """Return one appointment with the customer's name and the visible place.

    A customer does not see the room address of an online booking until the
    designer accepts it. The designer always sees it.
    """
    public = AppointmentPublic.model_validate(appointment)
    public.customer_name = service.customer_name(appointment)
    if (
        actor.role is Role.CUSTOMER
        and appointment.mode is ConsultationMode.ONLINE
        and appointment.state is not AppointmentState.ACCEPTED
    ):
        public.location = ""
    return public


@router.get(
    "/slots",
    response_model=SlotsPublic,
    summary="Show the free hours on one company's day",
)
def read_slots(
    actor: CurrentAccountDep,
    service: ServiceDep,
    company_id: str,
    day: date = Query(..., alias="date"),
) -> SlotsPublic:
    """Return the hours a customer may still pick."""
    try:
        slots = service.available_slots(actor, company_id, day)
    except (CompanyNotFound, ValueError) as exc:
        raise _fail(exc) from exc
    return SlotsPublic(date=day, slots=slots)


@router.post(
    "",
    response_model=AppointmentPublic,
    status_code=http_status.HTTP_201_CREATED,
    summary="Book a consultation",
)
def book(
    payload: BookRequest,
    actor: CurrentAccountDep,
    service: ServiceDep,
) -> AppointmentPublic:
    """A customer keeps one hour in a designer's diary."""
    try:
        appointment = service.book(
            actor,
            payload.company_id,
            payload.date,
            payload.time,
            payload.mode,
            payload.requirements,
        )
    except (NotPermitted, CompanyNotFound, InvalidState, ValueError) as exc:
        raise _fail(exc) from exc
    return _public(service, appointment, actor)


@router.get(
    "",
    response_model=list[AppointmentPublic],
    summary="List the appointments you may see",
)
def list_appointments(
    actor: CurrentAccountDep, service: ServiceDep
) -> list[AppointmentPublic]:
    """Customers see their bookings; designers see their company diary."""
    try:
        if actor.role.value == "CUSTOMER":
            appointments = service.list_for_customer(actor)
        else:
            appointments = service.list_for_designer(actor)
    except (NotPermitted, CompanyNotFound) as exc:
        raise _fail(exc) from exc
    return [_public(service, entry, actor) for entry in appointments]


@router.post(
    "/{appointment_id}/accept",
    response_model=AppointmentPublic,
    summary="Accept a consultation",
)
def accept_appointment(
    appointment_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> AppointmentPublic:
    """The designer confirms the hour."""
    try:
        appointment = service.accept(actor, appointment_id)
    except (AppointmentNotFound, NotPermitted, CompanyNotFound, InvalidState) as exc:
        raise _fail(exc) from exc
    return _public(service, appointment, actor)


@router.post(
    "/{appointment_id}/cancel",
    response_model=AppointmentPublic,
    summary="Cancel a consultation",
)
def cancel_appointment(
    appointment_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> AppointmentPublic:
    """Either party gives the hour back."""
    try:
        appointment = service.cancel(actor, appointment_id)
    except (AppointmentNotFound, NotPermitted, InvalidState) as exc:
        raise _fail(exc) from exc
    return _public(service, appointment, actor)
