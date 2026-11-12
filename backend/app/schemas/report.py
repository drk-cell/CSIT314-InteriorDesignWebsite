"""Request and response schemas for the project report endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ReportStatus


class ProjectReportPublic(BaseModel):
    """One report, with the names the administrator needs."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    project_id: str
    reason: str
    comments: str
    status: ReportStatus
    created_at: datetime
    resolved_at: datetime | None
    customer_name: str = ""
    project_title: str = ""
    designer_name: str = ""
    designer_email: str = ""


class SubmitReport(BaseModel):
    """Payload a customer sends from the project page."""

    project_id: str = Field(min_length=1)
    reason: str = Field(min_length=1, max_length=80)
    comments: str = Field(default="", max_length=1000)


class ResolveReport(BaseModel):
    """Which actions the administrator applies when closing a report.

    Neither flag means the report is dismissed.
    """

    take_down: bool = False
    suspend_designer: bool = False
