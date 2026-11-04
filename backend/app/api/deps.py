"""FastAPI dependencies: the shared store, the service and the caller.

The repository is a module level singleton so every request sees the same
in memory data. Tests clear it between cases through the fixture in
``tests/conftest.py``.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.domain.account import Account
from app.domain.enums import AccountStatus
from app.domain.errors import inactive_message
from app.repositories.account_repository import AccountRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.project_repository import ProjectRepository
from app.security import decode_access_token
from app.services.account_service import AccountService
from app.services.company_service import CompanyService
from app.services.project_service import ProjectService

_account_repository = AccountRepository()
_company_repository = CompanyRepository()
_project_repository = ProjectRepository()
_bearer_scheme = HTTPBearer(auto_error=False)


def get_account_repository() -> AccountRepository:
    """Return the process wide account store."""
    return _account_repository


def get_account_service() -> AccountService:
    """Return a service bound to the shared account store."""
    return AccountService(get_account_repository())


def get_company_repository() -> CompanyRepository:
    """Return the process wide company store."""
    return _company_repository


def get_company_service() -> CompanyService:
    """Return a service bound to the shared company store."""
    return CompanyService(get_company_repository())


def get_project_repository() -> ProjectRepository:
    """Return the process wide project store."""
    return _project_repository


def get_project_service() -> ProjectService:
    """Return a service bound to the shared project and company stores."""
    return ProjectService(get_project_repository(), get_company_repository())


def get_current_account(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)],
    service: Annotated[AccountService, Depends(get_account_service)],
) -> Account:
    """Return the account named by the bearer token.

    Raises 401 for a missing, malformed, expired or orphaned token.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        claims = decode_access_token(credentials.credentials)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    account = service.get(claims["sub"])
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not account.can_login():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=inactive_message(account.status),
        )
    return account