"""Business rule failures raised by the domain and the service layer.

Every error carries a short message that the boundary layer may pass
straight into an HTTP response, so wording lives with the rule it describes.
"""

from __future__ import annotations

from app.domain.enums import AccountStatus


class DomainError(Exception):
    """Base class for every recoverable business rule failure."""

    default_message: str = "The request breaks a business rule."

    def __init__(self, message: str | None = None) -> None:
        self.message: str = message or self.default_message
        super().__init__(self.message)


class EmailAlreadyRegistered(DomainError):
    """An account with the same email address already exists."""

    default_message = "Email is already registered"


class InvalidCredentials(DomainError):
    """The supplied email and password do not identify an account."""

    default_message = "Invalid email or password"


class AccountNotActive(DomainError):
    """The account exists but its status forbids signing in."""

    default_message = "Account cannot sign in"

    def __init__(self, status: AccountStatus) -> None:
        self.status: AccountStatus = status
        super().__init__(inactive_message(status))


def inactive_message(status: AccountStatus) -> str:
    """Return the message shown when an account may not hold a session."""
    if status is AccountStatus.PENDING:
        return "Account pending approval"
    if status is AccountStatus.SUSPENDED:
        return "Account suspended"
    return AccountNotActive.default_message


class InvalidRoleForSelfRegistration(DomainError):
    """A visitor tried to register with a staff only role."""

    default_message = "This role cannot be chosen at registration"


class WeakPassword(DomainError):
    """The chosen password does not meet the minimum length."""

    default_message = "Password must be at least 8 characters"


class NotPermitted(DomainError):
    """The caller may not perform this operation."""

    default_message = "You are not allowed to do that"


class AccountNotFound(DomainError):
    """No account matches the supplied identifier."""

    default_message = "Account not found"


class CompanyAlreadyExists(DomainError):
    """The designer already holds a company profile."""

    default_message = "This designer already has a company profile"


class CompanyNotFound(DomainError):
    """No company profile matches the request."""

    default_message = "Company profile not found"