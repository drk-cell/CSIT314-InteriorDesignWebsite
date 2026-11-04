"""The company entity owns its own invariants."""

from __future__ import annotations

import pytest

from app.domain.company import Company

OWNER = "account-1"


def make_company(**overrides: object) -> Company:
    fields: dict[str, object] = {
        "owner_id": OWNER,
        "name": "Studio Verde",
        "description": "Warm minimal interiors.",
        "contact_email": "Hello@StudioVerde.SG",
        "contact_phone": "+65 6123 4567",
        "location": "Singapore",
    }
    fields.update(overrides)
    return Company(**fields)  # type: ignore[arg-type]


def test_fields_are_normalised() -> None:
    company = make_company(name="  Studio Verde  ", contact_email=" Hello@StudioVerde.SG ")

    assert company.name == "Studio Verde"
    assert company.contact_email == "hello@studioverde.sg"
    assert company.location == "Singapore"


def test_a_new_company_has_an_id_and_one_timestamp() -> None:
    company = make_company()

    assert company.id
    assert company.created_at == company.updated_at


def test_rename_rejects_a_blank_name() -> None:
    company = make_company()

    with pytest.raises(ValueError):
        company.rename("   ")


def test_rename_keeps_the_trimmed_name_and_touches_the_record() -> None:
    company = make_company()
    before = company.updated_at

    company.rename("  Verde Studio ")

    assert company.name == "Verde Studio"
    assert company.updated_at >= before


def test_update_contact_rejects_an_address_without_a_domain() -> None:
    company = make_company()

    with pytest.raises(ValueError):
        company.update_contact("studio@localhost", "")


def test_update_contact_stores_a_clean_pair() -> None:
    company = make_company()

    company.update_contact(" Studio@Verde.sg ", " +65 6000 0000 ")

    assert company.contact_email == "studio@verde.sg"
    assert company.contact_phone == "+65 6000 0000"


def test_attach_logo_rejects_blank() -> None:
    company = make_company()

    with pytest.raises(ValueError):
        company.attach_logo("  ")


def test_attach_logo_stores_the_address() -> None:
    company = make_company()

    company.attach_logo(" https://cdn.example.com/verde.png ")

    assert company.logo_url == "https://cdn.example.com/verde.png"


def test_is_owned_by_compares_the_owner() -> None:
    company = make_company()

    assert company.is_owned_by(OWNER) is True
    assert company.is_owned_by("account-2") is False


def test_update_description_trims_and_touches() -> None:
    company = make_company()
    before = company.updated_at

    company.update_description("  Calm, warm, lived in. ")

    assert company.description == "Calm, warm, lived in."
    assert company.updated_at >= before