"""Project boundary: publish, read, edit and delete portfolio entries."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status as http_status

from app.api.deps import get_current_account, get_project_search_service, get_project_service
from app.domain.account import Account
from app.domain.enums import ProjectStatus
from app.domain.errors import CompanyNotFound, NotPermitted, ProjectNotFound
from app.schemas.project import (
    PaletteEntryPublic,
    ProjectCreate,
    ProjectPublic,
    ProjectUpdate,
    SearchResponse,
    TagSuggestionPublic,
)
from app.services.image_source import ImageUnavailable, load_image_bytes
from app.services.object_labels import engine_name
from app.services.project_search_service import ProjectSearchService
from app.services.project_service import ProjectService
from app.services.tag_suggestion_service import suggest_tags

router = APIRouter(prefix="/projects", tags=["projects"])

PUBLIC_DIR = Path(
    os.environ.get(
        "APP_PUBLIC_DIR",
        Path(__file__).resolve().parents[3] / "frontend" / "public",
    )
)

ServiceDep = Annotated[ProjectService, Depends(get_project_service)]
SearchDep = Annotated[ProjectSearchService, Depends(get_project_search_service)]
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
    name: str = "",
) -> list[ProjectPublic]:
    """Return the owner's projects filtered by status and title."""
    try:
        projects = service.list_for_owner(
            actor,
            status=status,
            name=name,
        )
    except NotPermitted as exc:
        raise _to_http(exc) from exc

    return [
        ProjectPublic.model_validate(project)
        for project in projects
    ]

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
    "/search",
    response_model=SearchResponse,
    summary="Search the project catalogue",
)
def search_projects(
    actor: CurrentAccountDep,
    service: SearchDep,
    keyword: str = "",
    category: str = "",
    style: str = "",
    budget_min: int | None = None,
    budget_max: int | None = None,
    tags: str = "",
    page: int = 1,
    page_size: int = 12,
) -> SearchResponse:
    """Return one page of projects that match the filters.

    ``tags`` takes a comma separated list. A project must carry at least one of
    them, and the closest match comes first.
    """
    try:
        result = service.search(
            keyword=keyword,
            category=category,
            style=style,
            budget_min=budget_min,
            budget_max=budget_max,
            tags=[tag.strip() for tag in tags.split(",") if tag.strip()],
            page=page,
            page_size=page_size,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return SearchResponse(
        items=[ProjectPublic.model_validate(project) for project in result.items],
        total=result.total,
        page=result.page,
        page_size=result.page_size,
        pages=result.pages,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectPublic,
    summary="Read one project",
)
def read_project(
    project_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> ProjectPublic:
    """Return a project. Any signed in account may read it, unless it was taken down."""
    try:
        project = service.get(project_id, actor)
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


@router.post(
    "/{project_id}/view",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Count one look at a project",
)
def record_project_view(
    project_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> Response:
    """Raise the view counter. The read endpoint stays free of side effects."""
    try:
        project = service.get(project_id)
    except ProjectNotFound as exc:
        raise _to_http(exc) from exc
    project.record_view()
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


@router.post(
    "/{project_id}/suggest-tags",
    response_model=TagSuggestionPublic,
    summary="Suggest description tags for one of your project photos",
)
def suggest_project_tags(
    project_id: str,
    actor: CurrentAccountDep,
    service: ServiceDep,
    image_index: int = 0,
) -> TagSuggestionPublic:
    """Read one photo of your project and offer palette and mood tags.

    Nothing is saved. The designer accepts what fits and edits the rest.
    """
    try:
        project = service.require_owned(actor, project_id)
    except (ProjectNotFound, NotPermitted) as exc:
        raise _to_http(exc) from exc

    if not project.images:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="The project has no photo to analyse",
        )
    if image_index < 0 or image_index >= len(project.images):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="The photo index is out of range",
        )

    try:
        data = load_image_bytes(project.images[image_index], PUBLIC_DIR)
        suggestion = suggest_tags(data)
    except ImageUnavailable as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    return TagSuggestionPublic(
        palette=[
            PaletteEntryPublic(hex=entry.hex, percent=entry.percent)
            for entry in suggestion.palette
        ],
        tags=suggestion.tags,
        width=suggestion.width,
        height=suggestion.height,
        engine=engine_name(),
        subject=suggestion.subject,
        objects=suggestion.objects,
    )