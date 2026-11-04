"""Deployment settings fail closed."""

from __future__ import annotations

import pytest

from app.config import get_bootstrap_admins, is_production
from app.main import create_app


def test_development_is_not_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    assert is_production() is False


def test_no_staff_environment_yields_no_bootstrap_accounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("APP_ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("APP_ADMIN_PASSWORD", raising=False)
    monkeypatch.delenv("APP_ADMIN_ACCOUNTS", raising=False)
    assert get_bootstrap_admins() == []


def test_the_single_admin_pair_is_kept(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ADMIN_EMAIL", "Admin@Example.com")
    monkeypatch.setenv("APP_ADMIN_PASSWORD", "passw0rd123")
    monkeypatch.delenv("APP_ADMIN_ACCOUNTS", raising=False)
    assert get_bootstrap_admins() == [
        ("admin@example.com", "passw0rd123", "Administrator", "ADMIN")
    ]


def test_the_list_format_supplies_several_staff_accounts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ADMIN_ACCOUNTS",
        "admin@example.com:pw1:First Admin:ADMIN,"
        "mgmt@example.com:pw2:Catalogue Keeper:PLATFORM_MANAGER",
    )
    assert get_bootstrap_admins() == [
        ("admin@example.com", "pw1", "First Admin", "ADMIN"),
        ("mgmt@example.com", "pw2", "Catalogue Keeper", "PLATFORM_MANAGER"),
    ]


def test_malformed_and_unprivileged_entries_are_skipped(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "APP_ADMIN_ACCOUNTS",
        "bad-entry,admin@example.com:pw:Name:ADMIN,"
        "customer@example.com:pw:Name:CUSTOMER,nopassword@example.com::Name:ADMIN",
    )
    assert get_bootstrap_admins() == [
        ("admin@example.com", "pw", "Name", "ADMIN")
    ]


def test_production_refuses_the_development_secret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("APP_SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="APP_SECRET_KEY"):
        create_app()


def test_production_accepts_a_configured_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("APP_SECRET_KEY", "a-real-deployment-secret-value-1234")

    application = create_app()

    assert application is not None