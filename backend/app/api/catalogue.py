"""The catalogue endpoint: the dropdown lists and the budget bounds."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.domain import catalogue

router = APIRouter(prefix="/catalogue", tags=["catalogue"])


class BudgetRange(BaseModel):
    """The slider bounds for the budget filter."""

    min: int = Field(description="Lowest selectable amount")
    max: int = Field(description="Highest selectable amount")
    step: int = Field(description="Slider step in the same currency unit")


class CatalogueResponse(BaseModel):
    """Everything a filter screen needs to build its controls."""

    categories: list[str]
    styles: list[str]
    budget: BudgetRange


@router.get(
    "",
    response_model=CatalogueResponse,
    summary="Read the fixed category and style lists",
)
def read_catalogue() -> CatalogueResponse:
    """Return the platform vocabulary. No sign in needed."""
    return CatalogueResponse(
        categories=list(catalogue.CATEGORIES),
        styles=list(catalogue.STYLES),
        budget=BudgetRange(
            min=catalogue.BUDGET_MIN,
            max=catalogue.BUDGET_MAX,
            step=catalogue.BUDGET_STEP,
        ),
    )