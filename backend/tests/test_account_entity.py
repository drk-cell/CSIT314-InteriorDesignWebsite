"""The Account entity owns its own state transitions and password check."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest

from app.domain.account import Account
from app.domain.enums import AccountStatus, Role
from app.domain.passwords import hash_password

PASSWORD = "secret123"


def make_account(**overrides: Any) -> Account:
    values: dict[str, Any] = {
        "email": "Ada@Example.COM",
        "display_name": "  Ada Lovelace  ",
        "password_hash": hash_password(PASSWORD),
        "role": Role.CUSTOMER,
        "status": AccountStatus.ACTIVE,
    }
    values.update(overrides)
    return Account(**values)


def test_email_is_stored_lowercased() -> None:
    assert make_account().email == "ada@example.com"


def test_display_name_is_trimmed() -> None:
    assert make_account().display_name == "Ada Lovelace"


def test_new_account_gets_an_id_and_utc_timestamp() -> None:
    account = make_account()
    assert len(account.id) == 36
    assert account.created_at.tzinfo is not None
    assert account.created_at.utcoffset() == timedelta(0)


def test_check_password_accepts_the_right_password() -> None:
    assert make_account().check_password(PASSWORD) is True


def test_check_password_rejects_a_wrong_password() -> None:
    assert make_account().check_password("wrong-password") is False


def test_check_password_rejects_a_malformed_hash() -> None:
    account = make_account(password_hash="not-a-valid-hash")
    assert account.check_password(PASSWORD) is False


def test_active_account_can_login() -> None:
    assert make_account(status=AccountStatus.ACTIVE).can_login() is True


def test_pending_account_cannot_login() -> None:
    assert make_account(status=AccountStatus.PENDING).can_login() is False


def test_suspend_blocks_login() -> None:
    account = make_account()
    account.suspend()
    assert account.status is AccountStatus.SUSPENDED
    assert account.can_login() is False


def test_activate_restores_login() -> None:
    account = make_account(status=AccountStatus.SUSPENDED)
    account.activate()
    assert account.status is AccountStatus.ACTIVE
    assert account.can_login() is True


def test_admin_is_privileged() -> None:
    assert make_account(role=Role.ADMIN).is_privileged() is True


def test_platform_manager_is_privileged() -> None:
    assert make_account(role=Role.PLATFORM_MANAGER).is_privileged() is True


def test_customer_and_designer_are_not_privileged() -> None:
    assert make_account(role=Role.CUSTOMER).is_privileged() is False
    assert make_account(role=Role.DESIGNER).is_privileged() is False


def test_change_display_name_replaces_and_trims() -> None:
    account = make_account()
    account.change_display_name("  Ada King  ")
    assert account.display_name == "Ada King"


def test_change_display_name_rejects_blank_input() -> None:
    account = make_account()
    with pytest.raises(ValueError):
        account.change_display_name("   ")
    assert account.display_name == "Ada Lovelace"