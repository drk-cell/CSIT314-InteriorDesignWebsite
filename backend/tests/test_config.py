"""Deployment settings fail closed."""

from __future__ import annotations

import pytest

from app.config import is_production
from app.main import create_app


def test_development_is_not_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ENV", raising=False)
    assert is_production() is False


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