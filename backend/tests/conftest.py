"""Shared fixtures: a clean in memory store and a test client."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_account_repository
from app.main import create_app
from app.repositories.account_repository import AccountRepository
from app.services.account_service import AccountService


@pytest.fixture()
def account_repository() -> Iterator[AccountRepository]:
    """The singleton store, emptied before and after each test."""
    repository = get_account_repository()
    repository.clear()
    yield repository
    repository.clear()


@pytest.fixture()
def account_service(account_repository: AccountRepository) -> AccountService:
    """A service bound to the freshly cleared store."""
    return AccountService(account_repository)


@pytest.fixture()
def client(account_repository: AccountRepository) -> Iterator[TestClient]:
    """A client for the application, sharing the cleared store."""
    with TestClient(create_app()) as test_client:
        yield test_client