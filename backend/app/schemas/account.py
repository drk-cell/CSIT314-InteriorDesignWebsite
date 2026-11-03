"""Request and response schemas for the account endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.enums import AccountStatus, Role


class AccountPublic(BaseModel):
    """The account fields that may leave the API."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    display_name: str
    role: Role
    status: AccountStatus
    created_at: datetime


class RegisterRequest(BaseModel):
    """Payload accepted by the registration endpoint."""

    email: str = Field(min_length=3, max_length=254)
    password: str
    display_name: str = Field(min_length=1, max_length=80)
    role: Role = Role.CUSTOMER

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        candidate = value.strip()
        local_part, _, domain = candidate.partition("@")
        if not local_part or "." not in domain:
            raise ValueError("Enter a valid email address")
        return candidate

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str) -> str:
        candidate = value.strip()
        if not candidate:
            raise ValueError("Display name must not be empty")
        return candidate


class LoginRequest(BaseModel):
    """Payload accepted by the login endpoint."""

    email: str = Field(min_length=3, max_length=254)
    password: str


class TokenResponse(BaseModel):
    """The result of a successful login."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    account: AccountPublic