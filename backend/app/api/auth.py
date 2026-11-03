"""Authentication boundary: registration, login and caller identity.

Each handler parses input, calls exactly one service method, translates
domain errors into HTTP responses and returns a schema. No business rule
lives here.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_account_service, get_current_account
from app.config import get_token_minutes
from app.domain.account import Account
from app.domain.errors import (
    AccountNotActive,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRoleForSelfRegistration,
    WeakPassword,
)
from app.schemas.account import AccountPublic, LoginRequest, RegisterRequest, TokenResponse
from app.security import create_access_token
from app.services.account_service import AccountService

router = APIRouter(prefix="/auth", tags=["auth"])

ServiceDep = Annotated[AccountService, Depends(get_account_service)]
CurrentAccountDep = Annotated[Account, Depends(get_current_account)]


@router.post(
    "/register",
    response_model=AccountPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Register a customer or designer account",
)
def register(payload: RegisterRequest, service: ServiceDep) -> AccountPublic:
    """Create a self service account."""
    try:
        account = service.register(
            email=payload.email,
            password=payload.password,
            display_name=payload.display_name,
            role=payload.role,
        )
    except EmailAlreadyRegistered as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=exc.message) from exc
    except (InvalidRoleForSelfRegistration, WeakPassword) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=exc.message
        ) from exc
    return AccountPublic.model_validate(account)


@router.post("/login", response_model=TokenResponse, summary="Exchange credentials for a token")
def login(payload: LoginRequest, service: ServiceDep) -> TokenResponse:
    """Authenticate an account and issue an access token."""
    try:
        account = service.authenticate(payload.email, payload.password)
    except InvalidCredentials as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=exc.message
        ) from exc
    except AccountNotActive as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=exc.message) from exc
    minutes = get_token_minutes()
    token = create_access_token(account.id, account.role.value, minutes)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        expires_in=minutes * 60,
        account=AccountPublic.model_validate(account),
    )


@router.get("/me", response_model=AccountPublic, summary="Return the authenticated account")
def read_current_account(account: CurrentAccountDep) -> AccountPublic:
    """Return the account the bearer token belongs to."""
    return AccountPublic.model_validate(account)