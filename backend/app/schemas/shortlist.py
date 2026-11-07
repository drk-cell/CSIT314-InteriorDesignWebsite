"""Request and response schemas for the shortlist endpoints."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.project import ProjectPublic


class ShortlistResponse(BaseModel):
    """The saved ids, plus the projects they still resolve to."""

    project_ids: list[str]
    items: list[ProjectPublic]