"""Application factory and module level ASGI entry point."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, auth, catalogue, companies, health, projects, shortlist
from app.api.deps import get_account_service
from app.config import (
    APP_VERSION,
    get_bootstrap_admins,
    is_default_secret,
    is_production,
)
from app.domain.enums import Role

logger = logging.getLogger(__name__)

API_PREFIX: str = "/api"
ALLOWED_ORIGINS: tuple[str, ...] = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def _bootstrap_administrators() -> None:
    """Create the staff accounts the environment supplies.

    The store is empty at every start, so without these accounts nobody could
    approve a designer or suspend a user.
    """
    for email, password, name, role_name in get_bootstrap_admins():
        role = Role(role_name)
        get_account_service().ensure_staff_account(email, password, name, role)


def create_app() -> FastAPI:
    """Build the FastAPI application for the interior design platform."""
    if is_default_secret() and is_production():
        raise RuntimeError("APP_SECRET_KEY must be set when APP_ENV is not development")
    application = FastAPI(
        title="Interior Design Platform API",
        version=APP_VERSION,
        description="Accounts, roles and approval workflow for the CSIT314 project.",
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(ALLOWED_ORIGINS),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(health.router, prefix=API_PREFIX)
    application.include_router(auth.router, prefix=API_PREFIX)
    application.include_router(admin.router, prefix=API_PREFIX)
    application.include_router(companies.router, prefix=API_PREFIX)
    application.include_router(projects.router, prefix=API_PREFIX)
    application.include_router(catalogue.router, prefix=API_PREFIX)
    application.include_router(shortlist.router, prefix=API_PREFIX)
    _bootstrap_administrators()
    return application


app = create_app()

if is_default_secret():
    # Surfaced once at import time so a real deployment cannot silently ship
    # with the development signing key.
    logger.warning("APP_SECRET_KEY is unset, using the development secret")