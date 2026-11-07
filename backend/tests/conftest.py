"""Shared fixtures: clean in memory stores and a test client."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import (
    get_account_repository,
    get_company_repository,
    get_project_repository,
    get_shortlist_repository,
)
from app.main import create_app
from app.repositories.account_repository import AccountRepository
from app.repositories.company_repository import CompanyRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.shortlist_repository import ShortlistRepository
from app.services.account_service import AccountService
from app.services.company_service import CompanyService
from app.services.project_service import ProjectService


@pytest.fixture()
def account_repository() -> Iterator[AccountRepository]:
    """The singleton account store, emptied before and after each test."""
    repository = get_account_repository()
    repository.clear()
    yield repository
    repository.clear()


@pytest.fixture()
def company_repository() -> Iterator[CompanyRepository]:
    """The singleton company store, emptied before and after each test."""
    repository = get_company_repository()
    repository.clear()
    yield repository
    repository.clear()


@pytest.fixture()
def project_repository() -> Iterator[ProjectRepository]:
    """The singleton project store, emptied before and after each test."""
    repository = get_project_repository()
    repository.clear()
    yield repository
    repository.clear()


@pytest.fixture()
def shortlist_repository() -> Iterator[ShortlistRepository]:
    """The singleton shortlist store, emptied before and after each test."""
    repository = get_shortlist_repository()
    repository.clear()
    yield repository
    repository.clear()


@pytest.fixture()
def account_service(account_repository: AccountRepository) -> AccountService:
    """A service bound to the freshly cleared account store."""
    return AccountService(account_repository)


@pytest.fixture()
def company_service(company_repository: CompanyRepository) -> CompanyService:
    """A service bound to the freshly cleared company store."""
    return CompanyService(company_repository)


@pytest.fixture()
def project_service(
    project_repository: ProjectRepository,
    company_repository: CompanyRepository,
) -> ProjectService:
    """A service bound to the freshly cleared project and company stores."""
    return ProjectService(project_repository, company_repository)


@pytest.fixture()
def client(
    account_repository: AccountRepository,
    company_repository: CompanyRepository,
    project_repository: ProjectRepository,
    shortlist_repository: ShortlistRepository,
) -> Iterator[TestClient]:
    """A client for the application, sharing the cleared stores."""
    with TestClient(create_app()) as test_client:
        yield test_client