"""Account use cases: registration and sign in."""

from __future__ import annotations

from app.domain.account import Account
from app.domain.enums import AccountStatus, Role
from app.domain.errors import (
    AccountNotActive,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRoleForSelfRegistration,
    WeakPassword,
)
from app.repositories.account_repository import AccountRepository
from app.security import hash_password, verify_password

MIN_PASSWORD_LENGTH: int = 8

# Verifying against a real hash keeps the sign in path equally slow whether or
# not the email exists, so response time does not reveal registered addresses.
_TIMING_DECOY_HASH: str = hash_password("decoy-password-for-timing")

INITIAL_STATUS_BY_ROLE: dict[Role, AccountStatus] = {
    Role.CUSTOMER: AccountStatus.ACTIVE,
    Role.DESIGNER: AccountStatus.PENDING,
}


class AccountService:
    """Applies account business rules on top of the repository."""

    def __init__(self, repository: AccountRepository) -> None:
        self._repository = repository

    def register(self, email: str, password: str, display_name: str, role: Role) -> Account:
        """Create an account and store it.

        Customers may use the platform immediately; designers wait for
        approval. Staff roles cannot be chosen at sign up.
        """
        self._require_self_registration_role(role)
        self._require_strong_password(password)
        account = Account(
            email=email.strip().lower(),
            display_name=display_name,
            password_hash=hash_password(password),
            role=role,
            status=INITIAL_STATUS_BY_ROLE[role],
        )
        if not self._repository.add(account):
            raise EmailAlreadyRegistered()
        return account

    def authenticate(self, email: str, password: str) -> Account:
        """Return the account matching ``email`` and ``password``.

        Raises ``InvalidCredentials`` for an unknown address or a bad
        password, and ``AccountNotActive`` when the status blocks sign in.
        """
        account = self._repository.get_by_email(email)
        if account is None:
            verify_password(password, _TIMING_DECOY_HASH)
            raise InvalidCredentials()
        if not account.check_password(password):
            raise InvalidCredentials()
        if not account.can_login():
            raise AccountNotActive(account.status)
        return account

    def get(self, account_id: str) -> Account | None:
        """Return the account with ``account_id``, or ``None``."""
        return self._repository.get(account_id)

    @staticmethod
    def _require_self_registration_role(role: Role) -> None:
        if not role.can_self_register:
            raise InvalidRoleForSelfRegistration()

    @staticmethod
    def _require_strong_password(password: str) -> None:
        if len(password) < MIN_PASSWORD_LENGTH:
            raise WeakPassword()