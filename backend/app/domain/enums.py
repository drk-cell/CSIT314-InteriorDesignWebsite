"""Enumerations shared by the domain and the boundary layer."""

from __future__ import annotations

from enum import Enum


class Role(str, Enum):
    """The kind of actor an account represents."""

    CUSTOMER = "CUSTOMER"
    DESIGNER = "DESIGNER"
    ADMIN = "ADMIN"
    PLATFORM_MANAGER = "PLATFORM_MANAGER"

    @property
    def is_privileged(self) -> bool:
        """Return ``True`` for the platform oversight roles."""
        return self in PRIVILEGED_ROLES

    @property
    def can_self_register(self) -> bool:
        """Return ``True`` when a visitor may pick this role at sign up."""
        return self in SELF_REGISTRATION_ROLES


class AccountStatus(str, Enum):
    """Where an account sits in its approval lifecycle."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"


PRIVILEGED_ROLES: frozenset[Role] = frozenset({Role.ADMIN, Role.PLATFORM_MANAGER})
SELF_REGISTRATION_ROLES: frozenset[Role] = frozenset({Role.CUSTOMER, Role.DESIGNER})