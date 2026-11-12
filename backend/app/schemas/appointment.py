"""Request and response schemas for the appointment endpoints."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import AppointmentState


class AppointmentPublic(BaseModel):
    """One booking, as both parties read it."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    company_id: str
    appointment_date: date
    appointment_time: str
    requirements: str
    state: AppointmentState
    notified_at: datetime | None
    created_at: datetime
    updated_at: datetime
    customer_name: str = ""


class SlotsPublic(BaseModel):
    """The free hours on one company's day."""

    date: date
    slots: list[str]


class BookRequest(BaseModel):
    """Payload a customer sends to keep one slot."""

    company_id: str = Field(min_length=1)
    date: date
    time: str = Field(pattern=r"^([01][0-9]|2[0-3]):[0-5][0-9]$")
    requirements: str = Field(default="", max_length=1000)
