"""Report boundary: daily, weekly and monthly activity for platform staff."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from pydantic import BaseModel

from app.api.deps import get_current_account, get_report_service
from app.domain.account import Account
from app.domain.enums import PRIVILEGED_ROLES
from app.domain.errors import NotPermitted
from app.services.report_service import DEFAULT_BUCKETS, MAX_BUCKETS, ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

ServiceDep = Annotated[ReportService, Depends(get_report_service)]
CurrentAccountDep = Annotated[Account, Depends(get_current_account)]


class BucketPublic(BaseModel):
    """One period of activity."""

    label: str
    start: str
    end: str
    accounts: int
    projects: int
    quote_requests: int
    quotes: int


class ReportPublic(BaseModel):
    """A report with its period and buckets."""

    period: str
    buckets: list[BucketPublic]


@router.get(
    "",
    response_model=ReportPublic,
    summary="Read the activity report",
)
def read_report(
    actor: CurrentAccountDep,
    service: ServiceDep,
    period: str = "daily",
    buckets: int = DEFAULT_BUCKETS,
) -> ReportPublic:
    """Staff only. Buckets run oldest first and end at now."""
    if actor.role not in PRIVILEGED_ROLES:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="Only platform staff may read reports",
        )
    if buckets < 1 or buckets > MAX_BUCKETS:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=f"Buckets must sit between 1 and {MAX_BUCKETS}",
        )
    try:
        report = service.build(period=period, buckets=buckets)
    except ValueError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return ReportPublic(
        period=report.period,
        buckets=[
            BucketPublic(
                label=bucket.label,
                start=bucket.start.isoformat(),
                end=bucket.end.isoformat(),
                accounts=bucket.accounts,
                projects=bucket.projects,
                quote_requests=bucket.quote_requests,
                quotes=bucket.quotes,
            )
            for bucket in report.buckets
        ],
    )