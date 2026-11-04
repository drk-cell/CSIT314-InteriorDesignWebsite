"""Project boundary: publish, read, edit and delete portfolio entries."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status as http_status

from app.api.deps import get_current_account, get_project_service
from app.domain.account import Account
from app.domain.enums import ProjectStatus
from app.domain.errors import CompanyNotFound, NotPermitted, ProjectNotFound
from app.schemas.project import ProjectCreate, ProjectPublic, ProjectUpdate
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["projects"])

ServiceDep = Annotated[ProjectService, Depends(get_project_service)]
CurrentAccountDep = Annotated[Account, Depends(get_current_account)]


def _to_http(exc: Exception) -> HTTPException:
    """Map a domain refusal to the matching response."""
    if isinstance(exc, ProjectNotFound):
        return HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=exc.message)
    if isinstance(exc, (CompanyNotFound, NotPermitted)):
        return HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=exc.message)
    if isinstance(exc, ValueError):
        return HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.post(
    "",
    response_model=ProjectPublic,
    status_code=http_status.HTTP_201_CREATED,
    summary="Publish a project under the designer company",
)
def create_project(
    payload: ProjectCreate, actor: CurrentAccountDep, service: ServiceDep
) -> ProjectPublic:
    """Publish one portfolio project for the signed in designer."""
    try:
        project = service.create(actor, **payload.model_dump())
    except (NotPermitted, CompanyNotFound, ValueError) as exc:
        raise _to_http(exc) from exc
    return ProjectPublic.model_validate(project)


@router.get(
    "/mine",
    response_model=list[ProjectPublic],
    summary="List the signed in designer's portfolio",
)
def list_my_projects(
    actor: CurrentAccountDep,
    service: ServiceDep,
    status: ProjectStatus | None = None,
) -> list[ProjectPublic]:
    """Return the caller's projects, newest first, optionally filtered."""
    try:
        projects = service.list_for_owner(actor, status)
    except NotPermitted as exc:
        raise _to_http(exc) from exc
    return [ProjectPublic.model_validate(project) for project in projects]


@router.get(
    "/company/{company_id}",
    response_model=list[ProjectPublic],
    summary="List the published projects of one company",
)
def list_company_projects(
    company_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> list[ProjectPublic]:
    """Return the portfolio a customer browsing a designer would see."""
    projects = service.list_for_company(company_id)
    return [ProjectPublic.model_validate(project) for project in projects]


@router.get(
    "/{project_id}",
    response_model=ProjectPublic,
    summary="Read one project",
)
def read_project(
    project_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> ProjectPublic:
    """Return a project. Any signed in account may read it."""
    try:
        project = service.get(project_id)
    except ProjectNotFound as exc:
        raise _to_http(exc) from exc
    return ProjectPublic.model_validate(project)


@router.patch(
    "/{project_id}",
    response_model=ProjectPublic,
    summary="Change fields of your own project",
)
def update_project(
    project_id: str,
    payload: ProjectUpdate,
    actor: CurrentAccountDep,
    service: ServiceDep,
) -> ProjectPublic:
    """Write only the supplied fields."""
    changes = payload.model_dump(exclude_unset=True)
    try:
        project = service.update(actor, project_id, **changes)
    except (ProjectNotFound, NotPermitted, ValueError) as exc:
        raise _to_http(exc) from exc
    return ProjectPublic.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Delete your own project",
)
def delete_project(
    project_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> Response:
    """Remove a project from the portfolio."""
    try:
        service.delete(actor, project_id)
    except (ProjectNotFound, NotPermitted) as exc:
        raise _to_http(exc) from exc
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)