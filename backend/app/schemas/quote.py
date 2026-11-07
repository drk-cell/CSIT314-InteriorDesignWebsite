"""Request and response schemas for the quote endpoints."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import QuoteRequestState, QuoteState


class CounterPublic(BaseModel):
    """One target price the customer named."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    target_cents: int
    note: str
    created_at: datetime


class QuotePublic(BaseModel):
    """One priced answer."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    request_id: str
    version: int
    total_cents: int
    gst_included: bool
    gst_rate_bp: int
    gst_cents: int
    grand_total_cents: int
    valid_until: date
    note: str
    state: QuoteState
    created_at: datetime


class QuoteRequestPublic(BaseModel):
    """The request fields both parties read."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    customer_id: str
    company_id: str
    project_id: str | None
    title: str
    scope: str
    budget_min_cents: int
    budget_max_cents: int
    target_cents: int | None
    state: QuoteRequestState
    counters: list[CounterPublic]
    closed_reason: str
    created_at: datetime
    updated_at: datetime


class QuoteRequestDetail(QuoteRequestPublic):
    """A request with every quote version attached."""

    quotes: list[QuotePublic]


class SubmitRequest(BaseModel):
    """Payload a customer sends to start a request."""

    company_id: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=120)
    scope: str = Field(min_length=1, max_length=2000)
    budget_min_cents: int = Field(default=0, ge=0)
    budget_max_cents: int = Field(default=0, ge=0)
    target_cents: int | None = Field(default=None, gt=0)
    project_id: str | None = None


class CounterRequest(BaseModel):
    """Payload for a target price."""

    target_cents: int = Field(gt=0)
    note: str = Field(default="", max_length=500)


class AnswerRequest(BaseModel):
    """Payload a designer sends as a quote or a revision."""

    total_cents: int = Field(gt=0)
    valid_days: int = Field(default=14, ge=1, le=90)
    gst_included: bool = False
    note: str = Field(default="", max_length=500)


class ReasonRequest(BaseModel):
    """Payload for a refusal, a cancellation or a decline."""

    reason: str = Field(default="", max_length=500)