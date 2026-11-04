"""The search service filters the catalogue for a customer."""

from __future__ import annotations

import pytest

from app.domain.project import Project
from app.repositories.project_repository import ProjectRepository
from app.services.project_search_service import ProjectSearchService


def add(
    repository: ProjectRepository,
    title: str,
    *,
    description: str = "",
    style: str = "Minimal",
    category: str = "Living Room",
    budget_min: int = 20000,
    budget_max: int = 40000,
) -> Project:
    project = Project(
        owner_id="account-1",
        company_id="company-1",
        title=title,
        description=description,
        style=style,
        category=category,
        budget_min=budget_min,
        budget_max=budget_max,
    )
    repository.add(project)
    return project


@pytest.fixture()
def service(project_repository: ProjectRepository) -> ProjectSearchService:
    return ProjectSearchService(project_repository)


def test_no_criteria_returns_everything(
    service: ProjectSearchService, project_repository: ProjectRepository
) -> None:
    add(project_repository, "One")
    add(project_repository, "Two")

    result = service.search()

    assert result.total == 2
    assert len(result.items) == 2


def test_keyword_matches_the_title_in_any_case(
    service: ProjectSearchService, project_repository: ProjectRepository
) -> None:
    add(project_repository, "Warm Minimal Living Room")
    add(project_repository, "Cool Grey Study", category="Home Office")

    result = service.search(keyword="warm")

    assert [project.title for project in result.items] == ["Warm Minimal Living Room"]


def test_keyword_matches_the_description(
    service: ProjectSearchService, project_repository: ProjectRepository
) -> None:
    add(project_repository, "Room A", description="A home that breathes.")
    add(project_repository, "Room B", description="Compact city flat.")

    result = service.search(keyword="BREATHES")

    assert [project.title for project in result.items] == ["Room A"]


def test_category_filter_is_exact(
    service: ProjectSearchService, project_repository: ProjectRepository
) -> None:
    add(project_repository, "Room A", category="Living Room")
    add(project_repository, "Room B", category="Bedroom")

    result = service.search(category="bedroom")

    assert [project.title for project in result.items] == ["Room B"]


def test_style_filter_is_exact(
    service: ProjectSearchService, project_repository: ProjectRepository
) -> None:
    add(project_repository, "Room A", style="Japandi")
    add(project_repository, "Room B", style="Industrial")

    result = service.search(style="Japandi")

    assert [project.title for project in result.items] == ["Room A"]


def test_budget_filters_match_on_overlap(
    service: ProjectSearchService, project_repository: ProjectRepository
) -> None:
    add(project_repository, "Inside", budget_min=20000, budget_max=40000)
    add(project_repository, "Above", budget_min=60000, budget_max=90000)

    result = service.search(budget_min=30000, budget_max=50000)

    assert [project.title for project in result.items] == ["Inside"]


def test_a_budget_floor_above_the_ceiling_is_rejected(
    service: ProjectSearchService,
) -> None:
    with pytest.raises(ValueError):
        service.search(budget_min=90000, budget_max=10000)


def test_filters_combine_with_and(
    service: ProjectSearchService, project_repository: ProjectRepository
) -> None:
    add(project_repository, "Warm Living Room", style="Minimal", category="Living Room")
    add(project_repository, "Warm Bedroom", style="Minimal", category="Bedroom")

    result = service.search(keyword="warm", category="Bedroom")

    assert [project.title for project in result.items] == ["Warm Bedroom"]


def test_paging_splits_the_result(
    service: ProjectSearchService, project_repository: ProjectRepository
) -> None:
    for index in range(5):
        add(project_repository, f"Room {index}")

    first = service.search(page=1, page_size=2)
    second = service.search(page=2, page_size=2)

    assert first.total == 5
    assert len(first.items) == 2
    assert len(second.items) == 2
    assert first.items[0].id != second.items[0].id


def test_a_page_past_the_end_is_empty_but_keeps_the_total(
    service: ProjectSearchService, project_repository: ProjectRepository
) -> None:
    add(project_repository, "Only One")

    result = service.search(page=5, page_size=10)

    assert result.items == []
    assert result.total == 1


def test_the_page_size_is_capped(
    service: ProjectSearchService, project_repository: ProjectRepository
) -> None:
    for index in range(3):
        add(project_repository, f"Room {index}")

    result = service.search(page=1, page_size=9999)

    assert result.page_size == 50
    assert len(result.items) == 3