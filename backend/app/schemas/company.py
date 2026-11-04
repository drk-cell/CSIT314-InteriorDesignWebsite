"""Request and response schemas for the company endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CompanyPublic(BaseModel):
    """The company fields a customer may read."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    name: str
    description: str
    contact_email: str
    contact_phone: str
    location: str
    logo_url: str
    created_at: datetime
    updated_at: datetime


class CompanyCreate(BaseModel):
    """Payload accepted when a designer creates the profile."""

    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    contact_email: str = Field(min_length=3, max_length=254)
    contact_phone: str = Field(default="", max_length=40)
    location: str = Field(default="", max_length=120)
    logo_url: str = Field(default="", max_length=500)


class CompanyUpdate(BaseModel):
    """Payload accepted when the owner changes the profile.

    Every field is optional. Only the supplied fields are written, so a caller
    may rename without resending the contact pair.
    """

    name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    contact_email: str | None = Field(default=None, max_length=254)
    contact_phone: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=120)
    logo_url: str | None = Field(default=None, max_length=500)