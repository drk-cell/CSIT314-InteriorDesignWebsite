"""Health check endpoint."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel

from app.config import APP_VERSION

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Liveness payload returned by the platform."""

    status: Literal["ok"]
    version: str
    time: datetime


@router.get("/health", response_model=HealthResponse, summary="Service liveness")
def read_health() -> HealthResponse:
    """Report that the API is running."""
    return HealthResponse(
        status="ok",
        version=APP_VERSION,
        time=datetime.now(timezone.utc),
    )