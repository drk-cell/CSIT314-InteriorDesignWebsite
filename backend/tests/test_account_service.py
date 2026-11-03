"""The account service applies registration and sign in rules."""

from __future__ import annotations

import pytest

from app.domain.enums import AccountStatus, Role
from app.domain.errors import (
    AccountNotActive,
    EmailAlreadyRegistered,
    InvalidCredentials,
    InvalidRoleForSelfRegistration,
    WeakPassword,
)
from app.services.account_service import AccountService

PASSWORD = "secret123"


def test_register_customer_is_active(account_service: AccountService) -> None:
    account = account_service.register("Casey@Example.com", PASSWORD, "Casey", Role.CUSTOMER)
    assert account.status is AccountStatus.ACTIVE
    assert account.can_login() is True
    assert account.email == "casey@example.com"


def test_register_designer_is_pending(account_service: AccountService) -> None:
    account = account_service.register("dana@example.com", PASSWORD, "Dana", Role.DESIGNER)
    assert account.status is AccountStatus.PENDING
    assert account.can_login() is False


def test_register_stores_the_account(account_service: AccountService) -> None:
    account = account_service.register("casey@example.com", PASSWORD, "Casey", Role.CUSTOMER)
    assert account_service.get(account.id) is account


def test_get_returns_none_for_unknown_id(account_service: AccountService) -> None:
    assert account_service.get("missing-id") is None


def test_duplicate_email_is_rejected(account_service: AccountService) -> None:
    account_service.register("casey@example.com", PASSWORD, "Casey", Role.CUSTOMER)
    with pytest.raises(EmailAlreadyRegistered):
        account_service.register("casey@example.com", PASSWORD, "Other", Role.CUSTOMER)


def test_duplicate_email_check_ignores_case(account_service: AccountService) -> None:
    account_service.register("casey@example.com", PASSWORD, "Casey", Role.CUSTOMER)
    with pytest.raises(EmailAlreadyRegistered):
        account_service.register("CASEY@EXAMPLE.COM", PASSWORD, "Other", Role.DESIGNER)


def test_short_password_is_rejected(account_service: AccountService) -> None:
    with pytest.raises(WeakPassword):
        account_service.register("casey@example.com", "short", "Casey", Role.CUSTOMER)


def test_staff_roles_cannot_self_register(account_service: AccountService) -> None:
    with pytest.raises(InvalidRoleForSelfRegistration):
        account_service.register("root@example.com", PASSWORD, "Root", Role.ADMIN)
    with pytest.raises(InvalidRoleForSelfRegistration):
        account_service.register("boss@example.com", PASSWORD, "Boss", Role.PLATFORM_MANAGER)


def test_authenticate_returns_the_account(account_service: AccountService) -> None:
    created = account_service.register("casey@example.com", PASSWORD, "Casey", Role.CUSTOMER)
    assert account_service.authenticate("Casey@Example.com", PASSWORD) is created


def test_authenticate_rejects_a_wrong_password(account_service: AccountService) -> None:
    account_service.register("casey@example.com", PASSWORD, "Casey", Role.CUSTOMER)
    with pytest.raises(InvalidCredentials):
        account_service.authenticate("casey@example.com", "wrong-password")


def test_authenticate_rejects_an_unknown_email(account_service: AccountService) -> None:
    with pytest.raises(InvalidCredentials):
        account_service.authenticate("nobody@example.com", PASSWORD)


def test_authenticate_pending_account_is_blocked(account_service: AccountService) -> None:
    account_service.register("dana@example.com", PASSWORD, "Dana", Role.DESIGNER)
    with pytest.raises(AccountNotActive) as error:
        account_service.authenticate("dana@example.com", PASSWORD)
    assert error.value.status is AccountStatus.PENDING
    assert error.value.message == "Account pending approval"


def test_authenticate_suspended_account_is_blocked(account_service: AccountService) -> None:
    account = account_service.register("casey@example.com", PASSWORD, "Casey", Role.CUSTOMER)
    account.suspend()
    with pytest.raises(AccountNotActive) as error:
        account_service.authenticate("casey@example.com", PASSWORD)
    assert error.value.status is AccountStatus.SUSPENDED
    assert error.value.message == "Account suspended"