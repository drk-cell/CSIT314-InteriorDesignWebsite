"""The company store holds one company per designer."""

from __future__ import annotations

from app.domain.company import Company
from app.repositories.company_repository import CompanyRepository


def make_company(owner_id: str, name: str = "Studio Verde") -> Company:
    return Company(owner_id=owner_id, name=name)


def test_add_stores_the_company() -> None:
    repository = CompanyRepository()
    company = make_company("account-1")

    assert repository.add(company) is True
    assert repository.get(company.id) is company
    assert repository.count() == 1


def test_one_company_per_designer() -> None:
    repository = CompanyRepository()
    repository.add(make_company("account-1"))

    second = make_company("account-1", "Second Studio")

    assert repository.add(second) is False
    assert repository.count() == 1
    assert repository.get_by_owner("account-1").name == "Studio Verde"


def test_get_by_owner_returns_none_for_an_unknown_designer() -> None:
    repository = CompanyRepository()

    assert repository.get_by_owner("nobody") is None


def test_clear_empties_the_store() -> None:
    repository = CompanyRepository()
    repository.add(make_company("account-1"))
    repository.add(make_company("account-2"))

    repository.clear()

    assert repository.count() == 0
    assert repository.list_all() == []