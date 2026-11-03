"""Administration boundary: account listing and status changes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status

from app.api.deps import get_account_service, get_current_account
from app.domain.account import Account
from app.domain.enums import AccountStatus
from app.domain.errors import AccountNotFound, NotPermitted
from app.schemas.account import AccountPublic
from app.services.account_service import AccountService

router = APIRouter(prefix="/admin", tags=["admin"])

ServiceDep = Annotated[AccountService, Depends(get_account_service)]
CurrentAccountDep = Annotated[Account, Depends(get_current_account)]


def _to_http(exc: Exception) -> HTTPException:
    """Map a domain refusal to the matching response."""
    if isinstance(exc, AccountNotFound):
        return HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=exc.message)
    return HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=exc.message)


@router.get(
    "/accounts",
    response_model=list[AccountPublic],
    summary="List accounts for an administrator",
)
def list_accounts(
    actor: CurrentAccountDep,
    service: ServiceDep,
    account_status: Annotated[AccountStatus | None, Query(alias="status")] = None,
) -> list[AccountPublic]:
    """Return every account, optionally filtered by status."""
    try:
        accounts = service.list_accounts(actor, account_status)
    except NotPermitted as exc:
        raise _to_http(exc) from exc
    return [AccountPublic.model_validate(account) for account in accounts]


@router.post(
    "/accounts/{account_id}/approve",
    response_model=AccountPublic,
    summary="Approve an account",
)
def approve_account(
    account_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> AccountPublic:
    """Activate the account so it may sign in."""
    try:
        account = service.approve(actor, account_id)
    except (AccountNotFound, NotPermitted) as exc:
        raise _to_http(exc) from exc
    return AccountPublic.model_validate(account)


@router.post(
    "/accounts/{account_id}/suspend",
    response_model=AccountPublic,
    summary="Suspend an account",
)
def suspend_account(
    account_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> AccountPublic:
    """Suspend the account so it cannot sign in again."""
    try:
        account = service.suspend(actor, account_id)
    except (AccountNotFound, NotPermitted) as exc:
        raise _to_http(exc) from exc
    return AccountPublic.model_validate(account)