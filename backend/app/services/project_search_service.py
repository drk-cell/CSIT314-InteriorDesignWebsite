"""Search the project catalogue for a customer.

The filter is one query object: keyword, category, style and a budget range.
Budget matches on overlap, so a project priced 20k to 40k answers a 30k to 50k
search. The result carries the page and the total, so the screen can page.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.domain.project import Project, SearchCriteria
from app.repositories.project_repository import ProjectRepository

DEFAULT_PAGE_SIZE: int = 12
MAX_PAGE_SIZE: int = 50


@dataclass(frozen=True)
class SearchResult:
    """One page of matches plus the numbers the screen needs."""

    items: list[Project]
    total: int
    page: int
    page_size: int

    @property
    def pages(self) -> int:
        """Return how many pages the total fills, at least one."""
        if self.page_size <= 0:
            return 1
        return max(1, -(-self.total // self.page_size))


class ProjectSearchService:
    """Filters the catalogue. Holds no state of its own."""

    def __init__(self, projects: ProjectRepository) -> None:
        self._projects = projects

    def search(
        self,
        *,
        keyword: str = "",
        category: str = "",
        style: str = "",
        budget_min: int | None = None,
        budget_max: int | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> SearchResult:
        """Return the matches for one page of results."""
        if page < 1:
            raise ValueError("Page must be 1 or higher")
        if page_size < 1:
            raise ValueError("Page size must be 1 or higher")
        if budget_min is not None and budget_max is not None and budget_min > budget_max:
            raise ValueError("Minimum budget must not exceed the maximum")

        criteria = SearchCriteria(
            keyword=keyword,
            category=category,
            style=style,
            budget_min=budget_min,
            budget_max=budget_max,
        )
        size = min(page_size, MAX_PAGE_SIZE)
        matches = [project for project in self._projects.list_all() if project.matches(criteria)]
        matches.sort(key=lambda project: project.created_at, reverse=True)
        start = (page - 1) * size
        return SearchResult(
            items=matches[start : start + size],
            total=len(matches),
            page=page,
            page_size=size,
        )