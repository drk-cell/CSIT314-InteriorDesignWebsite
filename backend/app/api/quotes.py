"""Quote boundary: request a price, answer it, negotiate on one total."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status as http_status

from app.api.deps import get_current_account, get_quote_service
from app.domain.account import Account
from app.domain.enums import QuoteRequestState
from app.domain.errors import (
    CompanyNotFound,
    InvalidState,
    NotPermitted,
    ProjectNotFound,
    QuoteNotFound,
    QuoteRequestNotFound,
)
from app.schemas.quote import (
    AnswerRequest,
    CounterRequest,
    QuotePublic,
    QuoteRequestDetail,
    QuoteRequestPublic,
    ReasonRequest,
    SubmitRequest,
)
from app.services.quote_service import QuoteService

router = APIRouter(prefix="/quotes", tags=["quotes"])

ServiceDep = Annotated[QuoteService, Depends(get_quote_service)]
CurrentAccountDep = Annotated[Account, Depends(get_current_account)]


def _fail(exc: Exception) -> HTTPException:
    """Map a domain refusal to the matching response."""
    if isinstance(exc, (QuoteRequestNotFound, QuoteNotFound, CompanyNotFound, ProjectNotFound)):
        return HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=exc.message)
    if isinstance(exc, NotPermitted):
        return HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=exc.message)
    if isinstance(exc, InvalidState):
        return HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=exc.message)
    return HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _detail(service: QuoteService, actor: Account, request_id: str) -> QuoteRequestDetail:
    request = service.get_request(actor, request_id)
    quotes = service.quotes_for(actor, request_id)
    return QuoteRequestDetail(
        **QuoteRequestPublic.model_validate(request).model_dump(),
        quotes=[QuotePublic.model_validate(quote) for quote in quotes],
    )


@router.post(
    "/requests",
    response_model=QuoteRequestPublic,
    status_code=http_status.HTTP_201_CREATED,
    summary="Send a quote request to one company",
)
def submit_request(
    payload: SubmitRequest, actor: CurrentAccountDep, service: ServiceDep
) -> QuoteRequestPublic:
    """A customer asks one company for a price."""
    try:
        request = service.submit(actor, **payload.model_dump())
    except (NotPermitted, CompanyNotFound, ProjectNotFound, InvalidState, ValueError) as exc:
        raise _fail(exc) from exc
    return QuoteRequestPublic.model_validate(request)


@router.get(
    "/requests",
    response_model=list[QuoteRequestPublic],
    summary="List the requests you may see",
)
def list_requests(
    actor: CurrentAccountDep,
    service: ServiceDep,
    state: QuoteRequestState | None = None,
) -> list[QuoteRequestPublic]:
    """Customers see what they sent; designers see what their company received."""
    try:
        if actor.role.value == "CUSTOMER":
            requests = service.list_for_customer(actor, state)
        else:
            requests = service.list_for_designer(actor, state)
    except (NotPermitted, CompanyNotFound) as exc:
        raise _fail(exc) from exc
    return [QuoteRequestPublic.model_validate(request) for request in requests]


@router.get(
    "/requests/{request_id}",
    response_model=QuoteRequestDetail,
    summary="Read one request with every quote version",
)
def read_request(
    request_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> QuoteRequestDetail:
    """Return one request to a customer, the company, or platform staff."""
    try:
        return _detail(service, actor, request_id)
    except (QuoteRequestNotFound, NotPermitted) as exc:
        raise _fail(exc) from exc


@router.post(
    "/requests/{request_id}/counter",
    response_model=QuoteRequestDetail,
    summary="Name a target price",
)
def counter_request(
    request_id: str,
    payload: CounterRequest,
    actor: CurrentAccountDep,
    service: ServiceDep,
) -> QuoteRequestDetail:
    """The customer records the price they want. It does not bind the designer."""
    try:
        service.counter(actor, request_id, payload.target_cents, payload.note)
        return _detail(service, actor, request_id)
    except (QuoteRequestNotFound, NotPermitted, InvalidState) as exc:
        raise _fail(exc) from exc


@router.post(
    "/requests/{request_id}/cancel",
    response_model=QuoteRequestPublic,
    summary="Cancel your request",
)
def cancel_request(
    request_id: str,
    payload: ReasonRequest,
    actor: CurrentAccountDep,
    service: ServiceDep,
) -> QuoteRequestPublic:
    """Stop an open request."""
    try:
        request = service.cancel(actor, request_id, payload.reason)
    except (QuoteRequestNotFound, NotPermitted, InvalidState) as exc:
        raise _fail(exc) from exc
    return QuoteRequestPublic.model_validate(request)


@router.post(
    "/requests/{request_id}/refuse",
    response_model=QuoteRequestPublic,
    summary="Decline to quote",
)
def refuse_request(
    request_id: str,
    payload: ReasonRequest,
    actor: CurrentAccountDep,
    service: ServiceDep,
) -> QuoteRequestPublic:
    """The company declines the request."""
    try:
        request = service.refuse(actor, request_id, payload.reason)
    except (QuoteRequestNotFound, NotPermitted, CompanyNotFound, InvalidState) as exc:
        raise _fail(exc) from exc
    return QuoteRequestPublic.model_validate(request)


@router.post(
    "/requests/{request_id}/quotes",
    response_model=QuotePublic,
    status_code=http_status.HTTP_201_CREATED,
    summary="Answer a request with a total",
)
def answer_request(
    request_id: str,
    payload: AnswerRequest,
    actor: CurrentAccountDep,
    service: ServiceDep,
) -> QuotePublic:
    """The company sends version one of the quote."""
    try:
        quote = service.answer(actor, request_id, **payload.model_dump())
    except (QuoteRequestNotFound, NotPermitted, CompanyNotFound, InvalidState) as exc:
        raise _fail(exc) from exc
    return QuotePublic.model_validate(quote)


@router.get(
    "/requests/{request_id}/quotes",
    response_model=list[QuotePublic],
    summary="List every version of a request's quote",
)
def list_quotes(
    request_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> list[QuotePublic]:
    """Return the versions, oldest first."""
    try:
        quotes = service.quotes_for(actor, request_id)
    except (QuoteRequestNotFound, NotPermitted) as exc:
        raise _fail(exc) from exc
    return [QuotePublic.model_validate(quote) for quote in quotes]


@router.post(
    "/{quote_id}/revise",
    response_model=QuotePublic,
    status_code=http_status.HTTP_201_CREATED,
    summary="Send the next version of a quote",
)
def revise_quote(
    quote_id: str,
    payload: AnswerRequest,
    actor: CurrentAccountDep,
    service: ServiceDep,
) -> QuotePublic:
    """Replace the offered total with a new version."""
    try:
        quote = service.revise(actor, quote_id, **payload.model_dump())
    except (QuoteNotFound, QuoteRequestNotFound, NotPermitted, InvalidState) as exc:
        raise _fail(exc) from exc
    return QuotePublic.model_validate(quote)


@router.post(
    "/{quote_id}/accept",
    response_model=QuotePublic,
    summary="Accept a quote",
)
def accept_quote(
    quote_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> QuotePublic:
    """Accept one quote. Other open requests stay open."""
    try:
        quote = service.accept(actor, quote_id)
    except (QuoteNotFound, QuoteRequestNotFound, NotPermitted, InvalidState) as exc:
        raise _fail(exc) from exc
    return QuotePublic.model_validate(quote)


@router.post(
    "/{quote_id}/decline",
    response_model=QuotePublic,
    summary="Decline a quote",
)
def decline_quote(
    quote_id: str,
    payload: ReasonRequest,
    actor: CurrentAccountDep,
    service: ServiceDep,
) -> QuotePublic:
    """Turn one quote down with an optional reason."""
    try:
        quote = service.decline(actor, quote_id, payload.reason)
    except (QuoteNotFound, QuoteRequestNotFound, NotPermitted, InvalidState) as exc:
        raise _fail(exc) from exc
    return QuotePublic.model_validate(quote)