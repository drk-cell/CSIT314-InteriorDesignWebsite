"""Shortlist boundary: a customer saves projects to compare later."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status as http_status

from app.api.deps import get_current_account, get_shortlist_service
from app.domain.account import Account
from app.domain.errors import NotPermitted, ProjectNotFound
from app.schemas.project import ProjectPublic
from app.schemas.shortlist import ShortlistResponse
from app.services.shortlist_service import ShortlistService

router = APIRouter(prefix="/shortlist", tags=["shortlist"])

ServiceDep = Annotated[ShortlistService, Depends(get_shortlist_service)]
CurrentAccountDep = Annotated[Account, Depends(get_current_account)]


def _forbidden(exc: NotPermitted) -> HTTPException:
    return HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=exc.message)


@router.get(
    "",
    response_model=ShortlistResponse,
    summary="Read the saved projects of the signed in customer",
)
def read_shortlist(actor: CurrentAccountDep, service: ServiceDep) -> ShortlistResponse:
    """Return the caller's saved projects, oldest save first."""
    try:
        projects = service.list_for(actor)
        project_ids = service.ids_for(actor)
    except NotPermitted as exc:
        raise _forbidden(exc) from exc
    return ShortlistResponse(
        project_ids=project_ids,
        items=[ProjectPublic.model_validate(project) for project in projects],
    )


@router.post(
    "/{project_id}",
    response_model=ShortlistResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Save a project for the signed in customer",
)
def save_project(
    project_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> ShortlistResponse:
    """Save one project. Saving a saved project changes nothing."""
    try:
        service.add(actor, project_id)
        projects = service.list_for(actor)
        project_ids = service.ids_for(actor)
    except NotPermitted as exc:
        raise _forbidden(exc) from exc
    except ProjectNotFound as exc:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND, detail=exc.message
        ) from exc
    return ShortlistResponse(
        project_ids=project_ids,
        items=[ProjectPublic.model_validate(project) for project in projects],
    )


@router.delete(
    "/{project_id}",
    status_code=http_status.HTTP_204_NO_CONTENT,
    summary="Drop a project from the signed in customer's shortlist",
)
def unsave_project(
    project_id: str, actor: CurrentAccountDep, service: ServiceDep
) -> Response:
    """Drop one project. Dropping an absent project changes nothing."""
    try:
        service.remove(actor, project_id)
    except NotPermitted as exc:
        raise _forbidden(exc) from exc
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)