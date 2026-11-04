"""The company service applies the profile rules."""

from __future__ import annotations

import pytest

from app.domain.errors import (
    CompanyAlreadyExists,
    CompanyNotFound,
    NotPermitted,
)
from app.domain.enums import Role
from app.services.account_service import AccountService
from app.services.company_service import CompanyService

PASSWORD = "secret123"


def designer(accounts: AccountService, email: str = "dana@example.com"):
    return accounts.register(email, PASSWORD, "Dana Studio", Role.DESIGNER)


def customer(accounts: AccountService, email: str = "casey@example.com"):
    return accounts.register(email, PASSWORD, "Casey", Role.CUSTOMER)


def test_a_designer_creates_one_company(
    account_service: AccountService, company_service: CompanyService
) -> None:
    owner = designer(account_service)

    company = company_service.create(
        owner,
        name="Studio Verde",
        description="Warm minimal interiors.",
        contact_email="hello@verde.sg",
        contact_phone="+65 6123 4567",
        location="Singapore",
    )

    assert company.name == "Studio Verde"
    assert company.is_owned_by(owner.id) is True
    assert company_service.get_for_owner(owner).id == company.id


def test_a_customer_cannot_create_a_company(
    account_service: AccountService, company_service: CompanyService
) -> None:
    shopper = customer(account_service)

    with pytest.raises(NotPermitted):
        company_service.create(
            shopper,
            name="Not A Studio",
            description="",
            contact_email="shopper@example.com",
            contact_phone="",
            location="",
        )


def test_a_designer_cannot_hold_two_companies(
    account_service: AccountService, company_service: CompanyService
) -> None:
    owner = designer(account_service)
    company_service.create(
        owner,
        name="Studio Verde",
        description="",
        contact_email="hello@verde.sg",
        contact_phone="",
        location="Singapore",
    )

    with pytest.raises(CompanyAlreadyExists):
        company_service.create(
            owner,
            name="Second Studio",
            description="",
            contact_email="hi@second.sg",
            contact_phone="",
            location="Singapore",
        )


def test_reading_a_profile_before_creating_one_is_a_not_found(
    account_service: AccountService, company_service: CompanyService
) -> None:
    owner = designer(account_service)

    with pytest.raises(CompanyNotFound):
        company_service.get_for_owner(owner)


def test_the_owner_updates_the_profile(
    account_service: AccountService, company_service: CompanyService
) -> None:
    owner = designer(account_service)
    company_service.create(
        owner,
        name="Studio Verde",
        description="Warm minimal interiors.",
        contact_email="hello@verde.sg",
        contact_phone="",
        location="Singapore",
    )

    updated = company_service.update(
        owner, name="Verde Studio", location="Kuala Lumpur"
    )

    assert updated.name == "Verde Studio"
    assert updated.location == "Kuala Lumpur"
    assert updated.contact_email == "hello@verde.sg"


def test_an_unknown_field_value_is_rejected_by_the_entity(
    account_service: AccountService, company_service: CompanyService
) -> None:
    owner = designer(account_service)
    company_service.create(
        owner,
        name="Studio Verde",
        description="",
        contact_email="hello@verde.sg",
        contact_phone="",
        location="",
    )

    with pytest.raises(ValueError):
        company_service.update(owner, name="   ")


def test_a_designer_without_a_profile_cannot_update_one(
    account_service: AccountService, company_service: CompanyService
) -> None:
    stranger = designer(account_service, "other@example.com")

    with pytest.raises(CompanyNotFound):
        company_service.update(stranger, name="Ghost Studio")


def test_any_caller_can_read_a_company_by_id(
    account_service: AccountService, company_service: CompanyService
) -> None:
    owner = designer(account_service)
    company = company_service.create(
        owner,
        name="Studio Verde",
        description="",
        contact_email="hello@verde.sg",
        contact_phone="",
        location="",
    )

    assert company_service.get(company.id).name == "Studio Verde"


def test_reading_an_unknown_company_is_a_not_found(
    company_service: CompanyService,
) -> None:
    with pytest.raises(CompanyNotFound):
        company_service.get("does-not-exist")