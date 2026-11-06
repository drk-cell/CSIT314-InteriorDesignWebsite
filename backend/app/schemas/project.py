"""Request and response schemas for the project endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ProjectStatus


class ProjectPublic(BaseModel):
    """The project fields a customer may read."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_id: str
    company_id: str
    title: str
    description: str
    style: str
    category: str
    budget_min: int
    budget_max: int
    status: ProjectStatus
    images: list[str]
    tags: list[str]
    view_count: int
    shortlist_count: int
    created_at: datetime
    updated_at: datetime


class ProjectCreate(BaseModel):
    """Payload accepted when a designer publishes a project."""

    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    style: str = Field(min_length=1, max_length=60)
    category: str = Field(min_length=1, max_length=60)
    budget_min: int = Field(default=0, ge=0)
    budget_max: int = Field(default=0, ge=0)
    images: list[str] = Field(default_factory=list, max_length=8)
    tags: list[str] = Field(default_factory=list, max_length=12)


class ProjectUpdate(BaseModel):
    """Payload accepted when the owner changes a project.

    Every field is optional. ``images`` replaces the whole list when supplied.
    """

    title: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    style: str | None = Field(default=None, max_length=60)
    category: str | None = Field(default=None, max_length=60)
    budget_min: int | None = Field(default=None, ge=0)
    budget_max: int | None = Field(default=None, ge=0)
    status: ProjectStatus | None = None
    images: list[str] | None = Field(default=None, max_length=8)
    tags: list[str] | None = Field(default=None, max_length=12)


class SearchResponse(BaseModel):
    """One page of search results plus the counts the screen shows."""

    items: list[ProjectPublic]
    total: int
    page: int
    page_size: int
    pages: int


class PaletteEntryPublic(BaseModel):
    """One colour of a photo and how much of it the photo holds."""

    hex: str
    percent: float


class TagSuggestionPublic(BaseModel):
    """What the analyser offers the designer. Nothing is applied automatically."""

    palette: list[PaletteEntryPublic]
    tags: list[str]
    width: int
    height: int