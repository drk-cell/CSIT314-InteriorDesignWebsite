"""Company profile boundary: create, read and update."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status as http_status

from app.api.deps import (
    get_appointment_service,
    get_company_service,
    get_current_account,
)
from app.domain.account import Account
from app.domain.errors import CompanyAlreadyExists, CompanyNotFound, NotPermitted
from app.schemas.company import CompanyCreate, CompanyPublic, CompanyUpdate
from app.services.appointment_service import AppointmentService
from app.services.company_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])

ServiceDep = Annotated[CompanyService, Depends(get_company_service)]
AppointmentsDep = Annotated[AppointmentService, Depends(get_appointment_service)]
CurrentAccountDep = Annotated[Account, Depends(get_current_account)]


def _public(
    company, actor: Account, appointments: AppointmentService
) -> CompanyPublic:
    """Return the public view, holding back the call link until it is earned."""
    public = CompanyPublic.model_validate(company)
    if not appointments.may_read_call_link(actor, company.id):
        public.call_link = ""
    return public


def _to_http(exc: Exception) -> HTTPException:
    """Map a domain refusal to the matching response."""
    if isinstance(exc, CompanyNotFound):
        return HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=exc.message)
    if isinstance(exc, CompanyAlreadyExists):
        return HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=exc.message)
    if isinstance(exc, ValueError):
        return HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)
        )
    return HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=exc.message)


@router.post(
    "",
    response_model=CompanyPublic,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create the company profile of the signed in designer",
)
def create_company(
    payload: CompanyCreate,
    actor: CurrentAccountDep,
    service: ServiceDep,
    appointments: AppointmentsDep,
) -> CompanyPublic:
    """Create the one profile this designer may hold."""
    try:
        company = service.create(actor, **payload.model_dump())
    except (NotPermitted, CompanyAlreadyExists, ValueError) as exc:
        raise _to_http(exc) from exc
    return _public(company, actor, appointments)


@router.get(
    "/me",
    response_model=CompanyPublic,
    summary="Read the company profile of the signed in designer",
)
def read_my_company(
    actor: CurrentAccountDep, service: ServiceDep, appointments: AppointmentsDep
) -> CompanyPublic:
    """Return the caller's own profile."""
    try:
        company = service.get_for_owner(actor)
    except (NotPermitted, CompanyNotFound) as exc:
        raise _to_http(exc) from exc
    return _public(company, actor, appointments)


@router.patch(
    "/me",
    response_model=CompanyPublic,
    summary="Change fields of the signed in designer's profile",
)
def update_my_company(
    payload: CompanyUpdate,
    actor: CurrentAccountDep,
    service: ServiceDep,
    appointments: AppointmentsDep,
) -> CompanyPublic:
    """Write only the fields that were supplied."""
    changes = payload.model_dump(exclude_unset=True)
    try:
        company = service.update(actor, **changes)
    except (NotPermitted, CompanyNotFound, ValueError) as exc:
        raise _to_http(exc) from exc
    return _public(company, actor, appointments)


@router.get(
    "",
    response_model=list[CompanyPublic],
    summary="List every company profile",
)
def list_companies(
    actor: CurrentAccountDep, service: ServiceDep, appointments: AppointmentsDep
) -> list[CompanyPublic]:
    """Return the published profiles so a customer can browse them."""
    return [
        _public(company, actor, appointments)
        for company in service.list_companies()
    ]


@router.get(
    "/{company_id}",
    response_model=CompanyPublic,
    summary="Read any company profile by id",
)
def read_company(
    company_id: str,
    actor: CurrentAccountDep,
    service: ServiceDep,
    appointments: AppointmentsDep,
) -> CompanyPublic:
    """Return a profile. Any signed in account may read it."""
    try:
        company = service.get(company_id)
    except CompanyNotFound as exc:
        raise _to_http(exc) from exc
    return _public(company, actor, appointments)