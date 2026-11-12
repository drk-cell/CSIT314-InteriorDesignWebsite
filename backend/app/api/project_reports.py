"""Project report boundary: a customer reports, platform staff act on it."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status as http_status

from app.api.deps import get_current_account, get_project_report_service
from app.domain.account import Account
from app.domain.errors import (
    AccountNotFound,
    InvalidState,
    NotPermitted,
    ProjectNotFound,
    ReportNotFound,
)
from app.domain.report import REPORT_REASONS, ProjectReport
from app.schemas.report import ProjectReportPublic, ResolveReport, SubmitReport
from app.services.project_report_service import ProjectReportService

router = APIRouter(prefix="/project-reports", tags=["project-reports"])

ServiceDep = Annotated[ProjectReportService, Depends(get_project_report_service)]
CurrentAccountDep = Annotated[Account, Depends(get_current_account)]


def _fail(exc: Exception) -> HTTPException:
    """Map a domain refusal to the matching response."""
    if isinstance(exc, (ReportNotFound, ProjectNotFound, AccountNotFound)):
        return HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail=exc.message
        )
    if isinstance(exc, NotPermitted):
        return HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN, detail=exc.message
        )
    if isinstance(exc, InvalidState):
        return HTTPException(
            status_code=http_status.HTTP_409_CONFLICT, detail=exc.message
        )
    return HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc))


def _public(
    service: ProjectReportService, report: ProjectReport
) -> ProjectReportPublic:
    """Return one report with the names the staff screen shows."""
    public = ProjectReportPublic.model_validate(report)
    public.project_title = service.project_title(report)
    designer = service.designer_of(report)
    if designer is not None:
        public.designer_name = designer.display_name
        public.designer_email = designer.email
    customer = service.customer_of(report)
    if customer is not None:
        public.customer_name = customer.display_name
    return public


@router.get(
    "/reasons",
    response_model=list[str],
    summary="List the reasons the report form offers",
)
def list_reasons() -> list[str]:
    """Return the fixed vocabulary, so the screen and the entity agree."""
    return list(REPORT_REASONS)


@router.post(
    "",
    response_model=ProjectReportPublic,
    status_code=http_status.HTTP_201_CREATED,
    summary="Report a project",
)
def report_project(
    payload: SubmitReport, actor: CurrentAccountDep, service: ServiceDep
) -> ProjectReportPublic:
    """A customer flags a project for the administrator."""
    try:
        report = service.submit(
            actor, payload.project_id, payload.reason, payload.comments
        )
    except (NotPermitted, ProjectNotFound, InvalidState, ValueError) as exc:
        raise _fail(exc) from exc
    return _public(service, report)


@router.get(
    "",
    response_model=list[ProjectReportPublic],
    summary="List every project report",
)
def list_reports(
    actor: CurrentAccountDep, service: ServiceDep
) -> list[ProjectReportPublic]:
    """Return the report queue, newest first. Platform staff only."""
    try:
        reports = service.list_reports(actor)
    except NotPermitted as exc:
        raise _fail(exc) from exc
    return [_public(service, report) for report in reports]


@router.post(
    "/{report_id}/resolve",
    response_model=ProjectReportPublic,
    summary="Take a project down, suspend the designer, or dismiss",
)
def resolve_report(
    report_id: str,
    payload: ResolveReport,
    actor: CurrentAccountDep,
    service: ServiceDep,
) -> ProjectReportPublic:
    """Close one report, applying the chosen actions.

    Both flags may be set. Neither flag dismisses the report.
    """
    try:
        report = service.resolve(
            actor,
            report_id,
            take_down=payload.take_down,
            suspend_designer=payload.suspend_designer,
        )
    except (
        ReportNotFound,
        ProjectNotFound,
        AccountNotFound,
        NotPermitted,
        InvalidState,
    ) as exc:
        raise _fail(exc) from exc
    return _public(service, report)
