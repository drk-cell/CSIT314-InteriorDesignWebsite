"""Category boundary: staff curate the room list, everyone reads it."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status as http_status
from pydantic import BaseModel, Field

from app.api.deps import get_category_service, get_current_account
from app.domain.account import Account
from app.domain.errors import NotPermitted
from app.services.category_service import (
    CategoryExists,
    CategoryNotFound,
    CategoryService,
)

router = APIRouter(prefix="/categories", tags=["categories"])

ServiceDep = Annotated[CategoryService, Depends(get_category_service)]
CurrentAccountDep = Annotated[Account, Depends(get_current_account)]


class CategoryPublic(BaseModel):
    """One category as the screens read it."""

    id: str
    name: str
    active: bool
    created_at: str
    updated_at: str


class CategoryInput(BaseModel):
    """Payload to create or rename a category."""

    name: str = Field(min_length=1, max_length=60)


class CategoryPatch(BaseModel):
    """Payload to rename, archive or restore."""

    name: str | None = Field(default=None, min_length=1, max_length=60)
    active: bool | None = None


def _to_public(category) -> CategoryPublic:
    return CategoryPublic(
        id=category.id,
        name=category.name,
        active=category.active,
        created_at=category.created_at.isoformat(),
        updated_at=category.updated_at.isoformat() if category.updated_at else "",
    )


def _fail(exc: Exception) -> HTTPException:
    if isinstance(exc, CategoryNotFound):
        return HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail=str(exc))
    if isinstance(exc, CategoryExists):
        return HTTPException(status_code=http_status.HTTP_409_CONFLICT, detail=str(exc))
    if isinstance(exc, NotPermitted):
        return HTTPException(status_code=http_status.HTTP_403_FORBIDDEN, detail=exc.message)
    return HTTPException(status_code=http_status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get(
    "",
    response_model=list[CategoryPublic],
    summary="List the categories a dropdown should show",
)
def list_categories(service: ServiceDep) -> list[CategoryPublic]:
    """Public list of active categories."""
    return [_to_public(category) for category in service.list_active()]


@router.get(
    "/all",
    response_model=list[CategoryPublic],
    summary="List every category, archived ones included",
)
def list_all_categories(
    actor: CurrentAccountDep, service: ServiceDep
) -> list[CategoryPublic]:
    """Staff only."""
    try:
        categories = service.list_all(actor)
    except NotPermitted as exc:
        raise _fail(exc) from exc
    return [_to_public(category) for category in categories]


@router.post(
    "",
    response_model=CategoryPublic,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create a category",
)
def create_category(
    payload: CategoryInput, actor: CurrentAccountDep, service: ServiceDep
) -> CategoryPublic:
    """Staff only."""
    try:
        category = service.add(actor, payload.name)
    except (NotPermitted, CategoryExists, ValueError) as exc:
        raise _fail(exc) from exc
    return _to_public(category)


@router.patch(
    "/{category_id}",
    response_model=CategoryPublic,
    summary="Rename, archive or restore a category",
)
def update_category(
    category_id: str,
    payload: CategoryPatch,
    actor: CurrentAccountDep,
    service: ServiceDep,
) -> CategoryPublic:
    """Staff only."""
    try:
        if payload.name is not None:
            service.rename(actor, category_id, payload.name)
        if payload.active is not None:
            category = service.set_active(actor, category_id, payload.active)
        else:
            category = service.get(actor, category_id)
    except (NotPermitted, CategoryNotFound, CategoryExists, ValueError) as exc:
        raise _fail(exc) from exc
    return _to_public(category)